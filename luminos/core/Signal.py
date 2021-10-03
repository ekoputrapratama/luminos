from typing import TypeVar, Callable, Generic

T = TypeVar('T')


class Signal:
    def __init__(self, *args):
        self.__subscribers = []

    def emit(self, *args, **kwargs):
        for subs in self.__subscribers:
            subs(*args, **kwargs)

    def connect(self, func):
        self.__subscribers.append(func)

    def disconnect(self, func: Callable[[T], None]):
        try:
            self.__subscribers.remove(func)
        except ValueError:
            print('Warning: function %s not removed '
                  'from signal %s' % (func, self))
