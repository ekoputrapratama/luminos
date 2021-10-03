import os
import io
import sys
import _imp
import marshal
import types
import importlib
import importlib._bootstrap as _bootstrap
from importlib.abc import Loader

from luminos.utils import log

_PYCACHE = '__pycache__'
_OPT = 'opt-'
SOURCE_SUFFIXES = ['.py']  # _setup() adds .pyw as needed.

BYTECODE_SUFFIXES = ['.pyc']

MAGIC_NUMBER = (3394).to_bytes(2, 'little') + b'\r\n'
_RAW_MAGIC_NUMBER = int.from_bytes(MAGIC_NUMBER, 'little')  # For import.c


def _r_long(int_bytes):
    """Convert 4 bytes in little-endian to an integer."""
    return int.from_bytes(int_bytes, 'little')


def _w_long(x):
    """Convert a 32-bit integer to little-endian."""
    return (int(x) & 0xFFFFFFFF).to_bytes(4, 'little')


def _calc_mode(path):
    """Calculate the mode permissions for a bytecode file."""
    try:
        mode = os.stat(path).st_mode
    except OSError:
        mode = 0o666
    # We always ensure write access so we can update cached files
    # later even when the source files are read-only on Windows (#6074)
    mode |= 0o200
    return mode


def _write_atomic(path, data, mode=0o666):
    """Best-effort function to write data to a path atomically.
    Be prepared to handle a FileExistsError if concurrent writing of the
    temporary file is attempted."""
    # id() is used to generate a pseudo-random filename.
    path_tmp = '{}.{}'.format(path, id(path))
    fd = os.open(path_tmp,
                 os.O_EXCL | os.O_CREAT | os.O_WRONLY, mode & 0o666)
    try:
        # We first write data to a temporary file, and then use os.replace() to
        # perform an atomic rename.
        with io.FileIO(fd, 'wb') as file:
            file.write(data)
        os.replace(path_tmp, path)
    except OSError:
        try:
            os.unlink(path_tmp)
        except OSError:
            pass
        raise


_code_type = type(_write_atomic.__code__)


def cache_from_source(path, debug_override=None, *, optimization=None):
    """Given the path to a .py file, return the path to its .pyc file.

    The .py file does not need to exist; this simply returns the path to the
    .pyc file calculated as if the .py file were imported.

    The 'optimization' parameter controls the presumed optimization level of
    the bytecode file. If 'optimization' is not None, the string representation
    of the argument is taken and verified to be alphanumeric (else ValueError
    is raised).

    The debug_override parameter is deprecated. If debug_override is not None,
    a True value is the same as setting 'optimization' to the empty string
    while a False value is equivalent to setting 'optimization' to '1'.

    If sys.implementation.cache_tag is None then NotImplementedError is raised.

    """
    if debug_override is not None:
        log.warnings.warn('the debug_override parameter is deprecated; use '
                          "'optimization' instead", DeprecationWarning)
        if optimization is not None:
            message = 'debug_override or optimization must be set to None'
            raise TypeError(message)
        optimization = '' if debug_override else 1

    path = os.fspath(path)
    head, tail = os.path.split(path)
    base, sep, rest = tail.rpartition('.')
    tag = sys.implementation.cache_tag
    if tag is None:
        raise NotImplementedError('sys.implementation.cache_tag is None')

    almost_filename = ''.join([(base if base else rest), sep, tag])
    if optimization is None:
        if sys.flags.optimize == 0:
            optimization = ''
        else:
            optimization = sys.flags.optimize

    optimization = str(optimization)
    if optimization != '':
        if not optimization.isalnum():
            raise ValueError('{!r} is not alphanumeric'.format(optimization))
        almost_filename = '{}.{}{}'.format(almost_filename, _OPT, optimization)

    return os.path.join(head, _PYCACHE, almost_filename + BYTECODE_SUFFIXES[0])


def _classify_pyc(data, name, exc_details):
    """Perform basic validity checking of a pyc header and return the flags field,
    which determines how the pyc should be further validated against the source.

    *data* is the contents of the pyc file. (Only the first 16 bytes are
    required, though.)

    *name* is the name of the module being imported. It is used for logging.

    *exc_details* is a dictionary passed to ImportError if it raised for
    improved debugging.

    ImportError is raised when the magic number is incorrect or when the flags
    field is invalid. EOFError is raised when the data is found to be truncated.

    """
    magic = data[:4]
    if magic != MAGIC_NUMBER:
        message = f'bad magic number in {name!r}: {magic!r}'
        _bootstrap._verbose_message('{}', message)
        raise ImportError(message, **exc_details)

    if len(data) < 16:
        message = f'reached EOF while reading pyc header of {name!r}'
        _bootstrap._verbose_message('{}', message)
        raise EOFError(message)

    flags = _r_long(data[4:8])
    # Only the first two flags are defined.
    if flags & ~0b11:
        message = f'invalid flags {flags!r} in {name!r}'
        raise ImportError(message, **exc_details)
    return flags


def _validate_timestamp_pyc(data, source_mtime, source_size, name,
                            exc_details):
    """Validate a pyc against the source last-modified time.

    *data* is the contents of the pyc file. (Only the first 16 bytes are
    required.)

    *source_mtime* is the last modified timestamp of the source file.

    *source_size* is None or the size of the source file in bytes.

    *name* is the name of the module being imported. It is used for logging.

    *exc_details* is a dictionary passed to ImportError if it raised for
    improved debugging.

    An ImportError is raised if the bytecode is stale.

    """
    if _r_long(data[8:12]) != (source_mtime & 0xFFFFFFFF):
        message = f'bytecode is stale for {name!r}'
        _bootstrap._verbose_message('{}', message)
        raise ImportError(message, **exc_details)
    if (source_size is not None and
            _r_long(data[12:16]) != (source_size & 0xFFFFFFFF)):
        raise ImportError(f'bytecode is stale for {name!r}', **exc_details)


def _validate_hash_pyc(data, source_hash, name, exc_details):
    """Validate a hash-based pyc by checking the real source hash against the one in
    the pyc header.

    *data* is the contents of the pyc file. (Only the first 16 bytes are
    required.)

    *source_hash* is the importlib.util.source_hash() of the source file.

    *name* is the name of the module being imported. It is used for logging.

    *exc_details* is a dictionary passed to ImportError if it raised for
    improved debugging.

    An ImportError is raised if the bytecode is stale.

    """
    if data[8:16] != source_hash:
        raise ImportError(
            f'hash in bytecode doesn\'t match hash of source {name!r}',
            **exc_details,
        )


def _compile_bytecode(data, name=None, bytecode_path=None, source_path=None):
    """Compile bytecode as found in a pyc."""
    code = marshal.loads(data)
    if isinstance(code, _code_type):
        _bootstrap._verbose_message('code object from {!r}', bytecode_path)
        if source_path is not None:
            _imp._fix_co_filename(code, source_path)
        return code
    else:
        raise ImportError('Non-code object in {!r}'.format(bytecode_path),
                          name=name, path=bytecode_path)


def _code_to_timestamp_pyc(code, mtime=0, source_size=0):
    "Produce the data for a timestamp-based pyc."
    data = bytearray(MAGIC_NUMBER)
    data.extend(_w_long(0))
    data.extend(_w_long(mtime))
    data.extend(_w_long(source_size))
    data.extend(marshal.dumps(code))
    return data


def _code_to_hash_pyc(code, source_hash, checked=True):
    "Produce the data for a hash-based pyc."
    data = bytearray(MAGIC_NUMBER)
    flags = 0b1 | checked << 1
    data.extend(_w_long(flags))
    assert len(source_hash) == 8
    data.extend(source_hash)
    data.extend(marshal.dumps(code))
    return data


class DependencyInjectorFinder(importlib.abc.MetaPathFinder):
    def __init__(self, loader):
        # we'll write the loader in a minute, hang tight
        self._loader = loader

    def find_spec(self, fullname, path, target=None):
        """Attempt to locate the requested module
        fullname is the fully-qualified name of the module,
        path is set to __path__ for sub-modules/packages, or None otherwise.
        target can be a module object, but is unused in this example.
        """
        if self._loader.provides(fullname):
            return self._gen_spec(fullname)

    def _gen_spec(self, fullname):
        spec = importlib.machinery.ModuleSpec(fullname, self._loader)
        return spec


class DependencyInjectorLoader(Loader):
    _COMMON_PREFIX = "luminos.plugins."
    path = None

    def __init__(self):
        self._services = {}
        # create a dummy module to return when Python attempts to import
        # myapp and myapp.virtual, the :-1 removes the last "." for
        # aesthetic reasons :)
        self._dummy_module = types.ModuleType(self._COMMON_PREFIX[:-1])
        # set __path__ so Python believes our dummy module is a package
        # this is important, since otherwise Python will believe our
        # dummy module can have no submodules
        self._dummy_module.__path__ = []

    def path_stats(self, path):
        """Return the metadata for the path."""
        st = os.stat(path)
        return {'mtime': st.st_mtime, 'size': st.st_size}

    def _cache_bytecode(self, source_path, bytecode_path, data):
        # Adapt between the two APIs
        mode = _calc_mode(source_path)
        return self.set_data(bytecode_path, data, _mode=mode)

    def set_data(self, path, data, *, _mode=0o666):
        """Write bytes data to a file."""
        parent, filename = os.path.split(path)
        path_parts = []
        # Figure out what directories are missing.
        while parent and not os.path.isdir(parent):
            parent, part = os.path.split(parent)
            path_parts.append(part)
        # Create needed directories.
        for part in reversed(path_parts):
            parent = os.path.join(parent, part)
            try:
                os.mkdir(parent)
            except FileExistsError:
                # Probably another Python process already created the dir.
                continue
            except OSError as exc:
                # Could be a permission error, read-only filesystem: just forget
                # about writing the data.
                _bootstrap._verbose_message('could not create {!r}: {!r}',
                                            parent, exc)
                return
        try:
            _write_atomic(path, data, _mode)
            _bootstrap._verbose_message('created {!r}', path)
        except OSError as exc:
            # Same as above: just don't write the bytecode.
            _bootstrap._verbose_message('could not create {!r}: {!r}', path,
                                        exc)

    def get_filename(self, fullname):
        """Return the path to the source file as found by the finder."""
        if fullname in self._services:
            module = self._services[fullname]
            return module.__path__
        return None

    def get_code(self, fullname):
        """Concrete implementation of InspectLoader.get_code.

        Reading of bytecode requires path_stats to be implemented. To write
        bytecode, set_data must also be implemented.

        """
        source_path = self.get_filename(fullname)
        source_mtime = None
        source_bytes = None
        source_hash = None
        hash_based = False
        check_source = True
        try:
            bytecode_path = cache_from_source(source_path)
        except NotImplementedError:
            bytecode_path = None
        else:
            try:
                st = self.path_stats(source_path)
            except OSError:
                pass
            else:
                source_mtime = int(st['mtime'])
                try:
                    data = self.get_data(bytecode_path)
                except OSError:
                    pass
                else:
                    exc_details = {
                        'name': fullname,
                        'path': bytecode_path,
                    }
                    try:
                        flags = _classify_pyc(data, fullname, exc_details)
                        bytes_data = memoryview(data)[16:]
                        hash_based = flags & 0b1 != 0
                        if hash_based:
                            check_source = flags & 0b10 != 0
                            if (_imp.check_hash_based_pycs != 'never' and
                                (check_source or
                                 _imp.check_hash_based_pycs == 'always')):
                                source_bytes = self.get_data(source_path)
                                source_hash = _imp.source_hash(
                                    _RAW_MAGIC_NUMBER,
                                    source_bytes,
                                )
                                _validate_hash_pyc(data, source_hash, fullname,
                                                   exc_details)
                        else:
                            _validate_timestamp_pyc(
                                data,
                                source_mtime,
                                st['size'],
                                fullname,
                                exc_details,
                            )
                    except (ImportError, EOFError):
                        pass
                    else:
                        _bootstrap._verbose_message('{} matches {}', bytecode_path,
                                                    source_path)
                        return _compile_bytecode(bytes_data, name=fullname,
                                                 bytecode_path=bytecode_path,
                                                 source_path=source_path)
        if source_bytes is None:
            source_bytes = self.get_data(source_path)
        code_object = self.source_to_code(source_bytes, source_path)
        _bootstrap._verbose_message('code object from {}', source_path)
        if (not sys.dont_write_bytecode and bytecode_path is not None and
                source_mtime is not None):
            if hash_based:
                if source_hash is None:
                    source_hash = _imp.source_hash(source_bytes)
                data = _code_to_hash_pyc(code_object, source_hash, check_source)
            else:
                data = _code_to_timestamp_pyc(code_object, source_mtime,
                                              len(source_bytes))
            try:
                self._cache_bytecode(source_path, bytecode_path, data)
                _bootstrap._verbose_message('wrote {!r}', bytecode_path)
            except NotImplementedError:
                pass
        return code_object

    def source_to_code(self, data, path, *, _optimize=-1):
        """Return the code object compiled from source.

        The 'data' argument can be any object type that compile() supports.
        """
        return _bootstrap._call_with_frames_removed(compile, data, path, 'exec',
                                                    dont_inherit=True, optimize=_optimize)

    def get_data(self, path):
        """Return the data from path as raw bytes."""
        # TODO: raise error if the file is not found
        # if it's a directory try to get the __init__.py file inside this folder
        if os.path.isdir(path):
            init_path = os.path.join(path, '__init__.py')
            if os.path.exists(init_path):
                with io.FileIO(init_path, 'r') as file:
                    return file.read()

        with io.FileIO(path, 'r') as file:
            return file.read()

    def provide(self, service_name, module):
        """Register a service as provided via the given module
        A service is any Python object in this context - an imported module,
        a class, etc."""
        self._services[service_name] = module

    def provides(self, fullname):
        if self._truncate_name(fullname) in self._services:
            return True
        else:
            # this checks if we should return the dummy module,
            # since this evaluates to True when importing myapp and
            # myapp.virtual
            return self._COMMON_PREFIX.startswith(fullname)

    def create_module(self, spec):
        """Create the given module from the supplied module spec
        Under the hood, this module returns a service or a dummy module,
        depending on whether Python is still importing one of the names listed
        in _COMMON_PREFIX.
        """
        service_name = self._truncate_name(spec.name)
        if service_name not in self._services:
            # return our dummy module since at this point we're loading
            # *something* along the lines of "myapp.virtual" that's not
            # a service
            return self._dummy_module
        module = self._services[service_name]
        return module

    def exec_module(self, module):
        """Execute the given module in its own namespace
        This method is required to be present by importlib.abc.Loader,
        but since we know our module object is already fully-formed,
        this method merely no-ops.
        """
        if hasattr(module, "__path__"):
            self.path = module.__path__
            code = self.get_code(module.__name__)
            importlib._bootstrap._call_with_frames_removed(exec, code, module.__dict__)

    def _truncate_name(self, fullname):
        """Strip off _COMMON_PREFIX from the given module name
        Convenience method when checking if a service is provided.
        """
        truncated_name = fullname
        if truncated_name.startswith(self._COMMON_PREFIX):
            truncated_name = fullname[len(self._COMMON_PREFIX):]

        return truncated_name

    def is_package(self, fullname):
        return self.provides(fullname)
