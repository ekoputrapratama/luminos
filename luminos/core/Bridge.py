from PyQt5.QtCore import (pyqtSignal, pyqtSlot, pyqtProperty, # noqa
                          QObject, QVariant as Variant)


class Bridge:
    @staticmethod
    def method(*args, **kwargs):
        return pyqtSlot(*args, **kwargs)

    @staticmethod
    def property(*args, **kwargs):
        return pyqtProperty(*args, **kwargs)

    @staticmethod
    def signal(*args, **kwargs):
        if args and kwargs:
            return pyqtSignal(*args, **kwargs)
        elif args:
            return pyqtSignal(*args)
        elif kwargs:
            return pyqtSignal(**kwargs)
        else:
            return pyqtSignal()


class BridgeObject(QObject):
    def __init__(self, name: str = "bridge_object", *args, **kwargs):
        super().__init__(parent=None)

        self._name = name
