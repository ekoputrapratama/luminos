import os
import traceback  # noqa
import typing
import functools

from gi.repository import Gio
from typing import Callable

import yaml
from luminos.core.Signal import Signal
from luminos.utils import log

instance = None
change_filters = {}


class change_filter:
    def __init__(self, option, function: bool = False) -> None:
        self._option = option
        self._function = function

        if not option in change_filters.keys():
            change_filters[option] = []

        change_filters[option].append(self)

    def checkMatch(self, option: str = None) -> bool:
        """Check if the given option matches the filter."""
        if option is None:
            # Called directly, not from a config change event.
            return True
        elif option == self._option:
            return True
        elif option.startswith(self._option + '.'):
            # prefix match
            return True
        else:
            return False

    def __call__(self, func: Callable) -> Callable:
        """Filter calls to the decorated function.

       Gets called when a function should be decorated.

       Adds a filter which returns if we're not interested in the change-event
       and calls the wrapped function if we are.

       We assume the function passed doesn't take any parameters.

       Args:
           func: The function to be decorated.

       Return:
           The decorated function.
       """
        if self._function:
            @functools.wraps(func)
            def func_wrapper(option: str, value) -> typing.Any:
                """Call the underlying function."""
                if self.checkMatch(option):
                    return func(option, value)
                return None
            self.callback = func_wrapper
            return func_wrapper
        else:
            @functools.wraps(func)
            def meth_wrapper(self_wrapper, option: str, value) -> typing.Any:
                """Call the underlying function."""
                if self.checkMatch(option):
                    return func(self_wrapper, option, value)
                return None
            self.callback = meth_wrapper
            return meth_wrapper


class Configuration:
    _filters = []
    changed = Signal()

    def __init__(self, path: str = None) -> None:
        self.loadFrom = path
        self.config = self.loadConfig()

        global instance
        instance = self

    def _filterData(self, key: str, data: str) -> str:
        if not self._filters:
            return data

        for callback in self._filters:
            data = callback(key, data)

        return data

    @classmethod
    def addFilter(cls, callback: Callable[[str, str], None]) -> None:
        cls._filters.append(callback)

    def loadConfig(self, key: str = None) -> dict:
        config = dict()
        try:
            with open(self.loadFrom, 'r') as f:
                data = f.read()
                if key is not None:
                    data = self._filterData(key, data)
                    config = yaml.safe_load(data)
                    config = config[key]
                else:
                    config = yaml.safe_load(data)
        except Exception:
            log.config.error("couldn't load config file from {}".format(self.loadFrom))

        return {key: value for key, value in config.items()}

    def keys(self):
        return self.config.keys()

    def get(self, key: str, defaultValue=None):
        temp = None
        try:
            for k in key.split("."):
                if temp is None:
                    temp = self.config[k]
                else:
                    temp = temp[k]
        except Exception:
            log.config.warning("cannot get config value for {}".format(key))
            temp = None

        if temp is None and defaultValue is not None:
            return defaultValue

        return temp

    def set(self, key, value) -> None:
        temp = None
        try:
            splitted = key.split(".")
            if len(splitted) > 1:
                max_slice = len(splitted) - 1
                for k in splitted[0:max_slice]:
                    if temp is None:
                        if not k in self.config.keys():
                            self.config[k] = {}

                        temp = self.config[k]
                    else:
                        if not k in temp.keys():
                            temp[k] = {}

                        temp = temp[k]

                temp[splitted[max_slice]] = value
            else:
                self.config[key] = value

            self.changed.emit(key, value)

        except Exception:
            log.config.warning("cannot set config value for {}".format(key))
            temp = None

    def save(self, path=None):

        if path is None:

            writable = os.access(os.path.dirname(self.loadFrom), os.W_OK)
            data = yaml.dump(self.config)
            if writable:
                with open(self.loadFrom, "w+") as f:
                    f.write(data)
            else:
                log.config.critical("Cannot save config file, file is not writable.")

    def loadDefaultConfig(self) -> dict:
        load_from_orig = self.loadFrom  # noqa
        self.loadFrom = __file__
        defaultConfig = self.loadConfig("Example")

        return defaultConfig

    @classmethod
    def removeFilter(cls, callback: Callable[[str, str], None]) -> None:
        cls._filters.remove(callback)


class Settings(Gio.Settings):
    def __init__(self, schema_id, path=None):
        # Add backwards compat with pygobject < 3.11.2
        if Gio.Settings.__init__.__name__ == "new_init":
            super().__init__(schema_id=schema_id, path=path)
        else:
            super().__init__(schema=schema_id, path=path)

    def bind_to_widget(self, key, widget, prop, flags=Gio.SettingsBindFlags.DEFAULT):
        self.bind(key, widget, prop, flags)
