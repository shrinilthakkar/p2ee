import threading
from weakref import WeakKeyDictionary


class ThreadContext(object):
    def __init__(self, **kwargs):
        """
        Maintains thread level contexts
        :param kwargs: contains the default global context
        """
        self._thread_contexts = WeakKeyDictionary()
        self._global_context = dict(**kwargs)

    def __get_thread_key(self):
        try:
            from greenlet import getcurrent
            return getcurrent()
        except ImportError:
            return threading.current_thread()

    def __get_thread_context(self):
        """
        :return: context of the current thread, if no context exists, create one with global context values
        """
        thread_id = self.__get_thread_key()
        return self._thread_contexts.setdefault(thread_id, dict(self._global_context))

    def get(self, key):
        return self.__get_thread_context().get(key)

    def set(self, key, value):
        self.__get_thread_context()[key] = value

    def unset(self, key):
        self.__get_thread_context().pop(key, None)

    def updateContext(self, **kwargs):
        self.__get_thread_context().update(**kwargs)

    def removeContext(self, *keys):
        for key in keys:
            self.unset(key)

    def clearContext(self):
        thread_id = self.__get_thread_key()
        self._thread_contexts[thread_id] = dict(self._global_context)

    def to_dict(self):
        return self.__get_thread_context()
