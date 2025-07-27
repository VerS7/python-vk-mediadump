"""
Исполнитель отложенных задач
"""

from time import sleep
from queue import Queue, Empty
from typing import Callable, Any
from concurrent.futures import ThreadPoolExecutor


class QueueExecutor:
    """Исполяет задачи по очереди в ThreadPool"""

    def __init__(
        self, max_workers: int = 10, empty_queue_sleep_time: float = 0.1
    ) -> None:
        self.max_workers = max_workers
        self.empty_queue_sleep_time = empty_queue_sleep_time
        self.stop = False
        self.queue = Queue()

    def push(self, executable: Callable[..., Any]) -> None:
        """Добавляет задачу в очередь"""
        self.queue.put(executable)

    def poll(self) -> None:
        """Слушает очередь с задачами и исполняет первую попавшуюся в ThreadPool"""
        with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
            while not self.stop:
                try:
                    executable = self.queue.get()
                except Empty:
                    sleep(self.empty_queue_sleep_time)

                pool.submit(lambda: executable())
