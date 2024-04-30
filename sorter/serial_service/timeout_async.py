import logging
import threading
import time
import types


class TimeoutAsync:
    def __init__(self, callback_fct: types.FunctionType, timeout_sec: float) -> None:
        self.callback_fct = callback_fct
        self.timeout_sec = timeout_sec

        self.running = False
        self.stop_thread_requested = False
        self.running_mutex = threading.Lock()
        self.running_condition = threading.Condition(self.running_mutex)

        # thread async wait
        self.thread = threading.Thread(target=self.thread_fct)
        self.thread.daemon = True
        self.thread.name = "TimeoutAsyncThread"
        self.thread.start()

    def stop_thread(self):
        self.running_mutex.acquire()
        logging.info("Thread stop requested ...")
        self.stop_thread_requested = True
        self.running_condition.notify_all()
        self.running_mutex.release()
        self.thread.join()

    def trigger(self):
        self.running_mutex.acquire()
        self.running = True
        self.running_condition.notify_all()
        self.running_mutex.release()

    def thread_fct(self):
        while True:
            # wait for timeout started
            self.running_mutex.acquire()
            while True:
                if self.running:
                    self.running = False
                    break
                if self.stop_thread_requested:
                    break
                self.running_condition.wait()
            self.running_mutex.release()

            if self.stop_thread_requested:
                break

            # wait timeout time
            time.sleep(self.timeout_sec)

            # callback
            self.callback_fct()
        logging.info("Thread stopping.")
