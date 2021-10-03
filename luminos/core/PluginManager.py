import os
import re
import ast
import sys
import typing
import types
import importlib
import importlib._bootstrap
import configparser

from PyQt5.QtCore import QObject, QUrl
from PyQt5.QtWidgets import QApplication
from PyQt5.QtWebEngineWidgets import QWebEngineScript
from luminos.utils import log, utils, standarddir, config
from luminos.core.Signal import Signal
from .DependencyInjector import DependencyInjectorFinder, DependencyInjectorLoader

Url = typing.TypeVar('Url', str, QUrl)


class PluginInjector:
    """
    Convenience wrapper for DependencyInjectorLoader and DependencyInjectorFinder.
    """

    def __init__(self):
        self._loader = DependencyInjectorLoader()
        self._finder = DependencyInjectorFinder(self._loader)
        self.installed = False
        self.install()

    def install(self):
        if not self.installed:
            self.installed = True
            sys.meta_path.append(self._finder)

    def provide(self, service_name, module):
        self._loader.provide(service_name, module)


class PluginInfo(configparser.ConfigParser):
    def __init__(self, filepath):
        super().__init__()
        self._filepath = filepath
        self.read(self._filepath, encoding='utf-8')

    def isValid(self) -> bool:
        """"""
        return self.has_section("plugin") and self.has_option("plugin", "Module")


class PluginManager(QObject):
    pluginAdded = Signal()
    pluginRemoved = Signal()
    pluginActivated = Signal()
    pluginDeactivated = Signal()
    loadStarted = Signal()
    loadFinished = Signal()
    beforeLoad = Signal()
    bridgeInitialize = Signal()

    def __init__(self, plugins_dirs: list = [], parent=None):
        super().__init__(parent)
        log.plugins.debug("Initializing PluginManager")
        lapp = QApplication.instance()

        from luminos.Application import Application
        assert isinstance(lapp, Application)

        self._plugins = {}
        self._injector = PluginInjector()
        self._loadedPlugins = {}
        self._pluginsResources = {}
        self._pluginsDirs = plugins_dirs + standarddir.defaultPluginsDir()
        self.loadStarted.connect(self._loadStarted)
        self.beforeLoad.connect(self._beforeLoad)
        self.loadFinished.connect(self._loadFinished)
        self.bridgeInitialize.connect(self._bridgeInitialize)
        config.instance.changed.connect(self._pluginsStateChanged)
        self._loadPlugins()

    def _bridgeInitialize(self, page):
        for name, resources in self._pluginsResources.items():
            for resource in resources:
                script_name = name + "_" + os.path.basename(resource)

                if resource.endswith(".js"):
                    injectionPoint = QWebEngineScript.DocumentReady
                    page.injectScript(resource, script_name, injectionPoint)
                elif resource.endswith(".css"):
                    injectionPoint = QWebEngineScript.DocumentReady
                    page.injectStylesheet(resource, script_name, injectionPoint)

    def _beforeLoad(self, channel, page):
        for name, plugin in self._plugins.items():
            if 'beforeLoad' in dir(plugin):
                plugin.beforeLoad(channel, page)
            elif 'before_load' in dir(plugin):
                plugin.before_load(channel, page)

    def _loadStarted(self, page):
        """"""

        for name, plugin in self._plugins.items():
            if 'loadStarted' in dir(plugin):
                plugin.loadStarted(page)
            elif 'load_started' in dir(plugin):
                plugin.load_started(page)

    def _loadFinished(self, page):
        for name, plugin in self._plugins.items():
            if 'loadFinished' in dir(plugin):
                plugin.loadStarted(page)
            elif 'load_finished' in dir(plugin):
                plugin.load_started(page)

    def addPluginPath(self, path: str):
        assert os.path.isabs(path)
        if not path in self._pluginsDirs:
            self._pluginsDirs.append(path)
            self._loadPlugins()

    def _loadPlugin(self, plugin_name):
        if plugin_name in self._loadedPlugins.keys():
            return self._loadedPlugins[plugin_name]

        identities_paths = []
        for directory in self._pluginsDirs:
            identities_paths += utils.findFiles("*.plugin", directory)

        module = None
        for f in identities_paths:
            info = PluginInfo(f)
            name = f
            if info.has_section("plugin") and info.has_option("plugin", "Name"):
                name = info.get("plugin", "Name")
            else:
                continue

            if name == plugin_name:
                if not info.isValid():
                    log.plugins.debug(f"Plugin identity {name} is not valid, please read documentation "
                                      "about how to write plugin.")
                else:
                    parentdir = os.path.dirname(f)
                    module_path = os.path.join(parentdir, info.get("plugin", "Module"))
                    if(not module_path.endswith(".py")):
                        module_path += ".py"

                    if os.path.exists(module_path):
                        try:
                            module_path = module_path
                            package = "luminos.plugins.{}.{}".format(name, name)
                            spec = importlib.util.spec_from_file_location(package, module_path)
                            module = importlib.util.module_from_spec(spec)
                            spec.loader.exec_module(module)
                            self._loadedPlugins[name] = module
                        except ImportError:
                            log.plugins.error(f"Unable to load plugin module {name}")

                        break
                    else:
                        log.plugins.warning(f"module specified in {name} doesn't exists, it will be ignored.")

        return module

    def _loadPlugins(self):
        """"""
        identities_paths = []
        for directory in self._pluginsDirs:
            identities_paths += utils.findFiles("*.plugin", directory)

        plugins: typing.List[PluginInfo] = []

        for f in identities_paths:
            info = PluginInfo(f)
            name = f
            if info.has_section("plugin") and info.has_option("plugin", "Name"):
                name = info.get("plugin", "Name")
            else:
                continue

            # if it's already exists it means that user just add a new plugins directory
            if name in self._loadedPlugins.keys():
                continue

            if not info.isValid():
                log.plugins.debug(f"Plugin identity {name} is not valid, please read documentation "
                                  "about how to write plugin.")
            else:
                parentdir = os.path.dirname(f)
                module_path = os.path.join(parentdir, info.get("plugin", "Module"))

                if(not module_path.endswith(".py")):
                    module_path += ".py"

                if os.path.exists(module_path):
                    info.set("plugin", "Path", module_path)
                    plugins.append(info)
                else:
                    log.plugins.warning(f"module specified in {f} doesn't exists, it will be ignored.")

        log.plugins.info(f"{len(plugins)} plugins found.")
        for plugin in plugins:
            try:
                name = plugin.get("plugin", "Name")
                module_name = plugin.get("plugin", "Module").replace(".py", "")
                module_path = plugin.get("plugin", "Path")

                parentdir = os.path.dirname(module_path)
                log.plugins.info(f"creating namespace for plugin {name}")
                # create a fake module for this plugin namespace
                package = f"{name}"
                module = types.ModuleType(package)
                module.__path__ = parentdir
                self._injector.provide(package, module)

                # TODO: add support to import module in subfolder
                # try to load all python file except for the main file and __init__.py
                for f in utils.findFiles("*.py", parentdir):
                    basename = os.path.splitext(os.path.basename(f))[0]
                    if basename == module_name or basename == '__init__':
                        continue

                    tail = f[len(parentdir + '/'):].replace(os.path.sep, '.').replace('.py', '')
                    package = f"{name}.{tail}"
                    m_path = f
                    log.plugins.info(f"load external module for plugin {name} with name {module.__name__}")
                    spec = importlib.util.spec_from_file_location(package, m_path)
                    module = importlib.util.module_from_spec(spec)
                    module.__path__ = m_path
                    self._injector.provide(package, module)

                log.plugins.info(f"importing main plugin module for plugin {name}")
                package = f"{name}.{module_name}"
                spec = importlib.util.spec_from_file_location(package, module_path)
                module = importlib.util.module_from_spec(spec)
                module.__path__ = module_path
                self._injector.provide(package, module)
                spec.loader.exec_module(module)
                self._loadedPlugins[name] = module

                """
                By default plugin will be enabled if there was no plugin configuration.
                """
                cfg = config.instance.get(f"plugins.{name}")
                shouldActivate = True
                if cfg is None:
                    shouldActivate = False
                    cfg = dict()
                    cfg['enabled'] = True
                    config.instance.set(f"plugins.{name}.enabled", True)

                # if this is the first time the plugin is registered code above will trigger _pluginStateChange
                # and activate it, so we don't need to activate it again here
                if cfg['enabled'] and shouldActivate:
                    if 'activate' in dir(module):
                        module.activate()
                        self._plugins[name] = module

                if plugin.has_option("plugin", "Resources"):
                    resources = ast.literal_eval(plugin.get("plugin", "Resources"))
                    base_path = os.path.dirname(module_path)

                    def to_abspath(path: str):
                        if not os.path.isabs(path):
                            return os.path.join(base_path, path)

                        return path

                    resources = list(map(to_abspath, resources))
                    self._pluginsResources[name] = resources

            except ImportError as e:
                name = plugin.get("plugin", "Name")
                log.plugins.error(f"Unable to load plugin module {name} : ${e.msg}")

    @config.change_filter("plugins")
    def _pluginsStateChanged(self, key: str, value):
        """We only interested with the name and the value"""
        res = re.findall("plugins\\.(.*)\\.enabled", key)
        if key.endswith("enabled") and len(res) > 0:
            name = res[0]
            if not value:
                self.disablePlugin(name)
            elif value:
                self.enablePlugin(name)

    def enablePlugin(self, name: str):
        """"""
        log.plugins.debug(f"enabling plugin {name}")
        if not name in self._plugins.keys():
            module = self._loadPlugin(name)
            if module is not None:
                if "activate" in dir(module):
                    module.activate()
                    self.pluginActivated.emit(name)
                    self._plugins[name] = module
                    self.pluginAdded.emit(name)
            else:
                log.plugins.warning(f"Unable activate plugin {name}")

    def disablePlugin(self, name: str):
        """"""
        log.plugins.debug(f"disabling plugin {name}")
        if name in self._plugins.keys():
            module = self._plugins[name]
            if "deactivate" in dir(module):
                module.deactivate()
                self.pluginDeactivated.emit(name)

            self._plugins.pop(name, None)
            self.pluginRemoved.emit(name)
