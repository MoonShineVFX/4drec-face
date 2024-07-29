from time import perf_counter
import logging


class Profiler:
    def __init__(self, text: str):
        self.__last_time = None
        self.mark(text)

    def mark(self, text: str):
        if self.__last_time is None:
            self.__last_time = perf_counter()
            logging.info(f"[Timer] {text}")
            return
        now = perf_counter()
        duration = now - self.__last_time
        self.__last_time = now
        logging.info(f"[Timer] {text}: {duration:.2f}s")
