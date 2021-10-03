import sys
import re
import os
import ast
import atexit
import os.path as path
from setuptools import setup, find_packages
from scripts import setupcommon as common
from scripts.setupcommon import hasWriteAccess, copyTree, copyFile
from subprocess import call

try:
    BASEDIR = os.path.dirname(os.path.realpath(__file__))
except NameError:
    BASEDIR = None


def _post_install():
    if hasWriteAccess('/usr/share'):
        datadir = '/usr/share'
        libdir = '/usr/lib'
        os.makedirs(path.join(datadir, 'luminos'), 0o755, exist_ok=True)
        os.makedirs(path.join(libdir, 'luminos'), 0o755, exist_ok=True)
    else:
        datadir = path.expanduser('~/.local/share')
        libdir = path.expanduser('~/.local/lib')
        os.makedirs(path.join(datadir, 'luminos'), 0o755, exist_ok=True)
        os.makedirs(path.join(libdir, 'luminos'), 0o755, exist_ok=True)

    print('Installing vendor files...')
    copyTree('data/vendor', path.join(datadir, 'luminos', 'vendor'))
    print('Installing static templates...')
    copyTree('data/static', path.join(datadir, 'luminos', 'static'))
    print('Installing built-in plugins...')
    copyTree('plugins', path.join(libdir, 'luminos', 'plugins'))
    print('Installing GSettings schemas...')
    copyFile('data/io.gitlab.fisma.luminos.gschema.xml', path.join(datadir, 'glib-2.0', 'schemas', 'io.gitlab.fisma.luminos.gschema.xml'))

    print("Updating icon cache...")
    call(["gtk-update-icon-cache", "-qtf", path.join(datadir, "icons", "hicolor")])

    print("Updating desktop database...")
    call(["update-desktop-database", "-q", path.join(datadir, "applications")])

    print("Compiling GSettings schemas...")
    call(["glib-compile-schemas", path.join(datadir, "glib-2.0", "schemas")])


args = sys.argv[1:]
if len(args) > 0 and args[0] != 'sdist':
    atexit.register(_post_install)


def read_file(name):
    """Get the string contained in the file named name."""
    with common.open_file(name, 'r', encoding='utf-8') as f:
        return f.read()


def read_requirements(name: str) -> list:
    filepath = os.path.join(BASEDIR, name)
    requirements = []
    with open(filepath) as fp:
        line = fp.readline()
        cnt = 1
        while line:
            requirements.append(line.strip())
            line = fp.readline()
            cnt += 1

    return requirements


def _get_constant(name):
    """Read a __magic__ constant from luminos/__init__.py.

    We don't import luminos here because it can go wrong for multiple
    reasons. Instead we use re/ast to get the value directly from the source
    file.

    Args:
        name: The name of the argument to get.

    Return:
        The value of the argument.
    """
    field_re = re.compile(r'__{}__\s+=\s+(.*)'.format(re.escape(name)))
    path = os.path.join(BASEDIR, 'luminos', '__init__.py')
    line = field_re.search(read_file(path)).group(1)
    value = ast.literal_eval(line)
    return value


# Get the long description from the README file
with open(os.path.join(BASEDIR, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name="luminos",
    version="0.3.8",
    python_requires='>=3.5',
    packages=find_packages(exclude=['scripts', 'scripts.*', 'tests', 'tests.*']),
    url="https://gitlab.com/fisma/luminos",
    license="MIT",
    author="Fisma Linux Project",
    author_email="muhammad.sayuti94@gmail.com",
    description="Desktop application SDK for creating Universal Linux Applications.",
    long_description=long_description,
    long_description_content_type='text/markdown',  # Optional (see note above)
    install_requires=read_requirements('requirements.txt'),
    # extras_require={  # Optional
    #     'dev': ['check-manifest'],
    #     'test': ['coverage'],
    # },
    entry_points={'gui_scripts':
                  ['luminos = luminos.luminos:main']},
    package_data={"": ["luminos.yml"]},
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Environment :: X11 Applications",
        "Intended Audience :: Developers",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: JavaScript",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Topic :: Software Development",
        "Topic :: Software Development :: Libraries :: Application Frameworks",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Software Development :: User Interfaces",
    ],
    keywords="desktop-application-sdk framework sdk javascript universal html5",
)
