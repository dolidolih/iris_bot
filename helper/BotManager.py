from irispy2 import Bot
from helper.PyKV import PyKV
import threading

class BotManager:
    _instance = None
    _thread_local = threading.local() 

    def __new__(cls, iris_url=None, *args, **kwargs):
        if not cls._instance:
            if iris_url is None:
                raise ValueError("iris_url must be provided during the first initialization of BotManager")
            cls._instance = super().__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self, iris_url=None):
        if not hasattr(self, '_initialized'):
            self.kv = PyKV()
            self.kv.open('res/ipy.db')
            self.bot = Bot(iris_url)
            self._initialized = True

    def get_current_bot(self):
        return self.bot

    def _get_thread_local_kv(self):
        if not hasattr(BotManager._thread_local, 'kv'):
            BotManager._thread_local.kv = PyKV()
            BotManager._thread_local.kv.open('res/ipy.db')
        return BotManager._thread_local.kv

    def get_kv(self):
        return self._get_thread_local_kv()

    def close_kv_connection(self):
        if hasattr(BotManager._thread_local, 'kv'):
            kv_instance = BotManager._thread_local.kv
            kv_instance.close()
            del BotManager._thread_local.kv