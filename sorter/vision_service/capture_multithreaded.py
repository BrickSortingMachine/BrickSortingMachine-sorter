import datetime
import logging
import threading
import time


class CaptureMultithreaded:
    def __init__(self, capture_device) -> None:
        # opencv capture
        self.capture_device = capture_device

        # pause capture
        self.enable_capture = True

        # queue of newly acquired frames
        self.queue_mutex = threading.Lock()
        self.queue_condition = threading.Condition(self.queue_mutex)
        self.queue = []

        # capture thread
        self.thread = threading.Thread(target=self.capture_thread_fct)
        self.thread.daemon = True  # have no explicit stopping mechanism
        self.thread.start()
        self.thread.name = "Capture Multithreaded"

    def capture_thread_fct(self):
        """
        - read
        - lock queue
        - add to queue
        - wake_all
        - unlock queue
        """
        logging.info("Camera thread started ...")
        dt_last_frame = datetime.datetime.now()
        frame_index = 0
        while True:
            # read into temp buffer
            if self.enable_capture:
                logging.info("capturing ...")
                ret, frame = self.capture_device.read()
                if not ret:
                    raise Exception("Error during image capture")
            else:
                time.sleep(0.60)

            # fps
            dt = datetime.datetime.now()
            fps = 1.0 / ((dt - dt_last_frame).total_seconds())
            dt_last_frame = dt

            if frame_index % 100 == 0:
                logging.info(f"Capture Thread: {fps:.2f} fps")

            self.queue_mutex.acquire()
            keep_last = 10
            del self.queue[:-keep_last]
            self.queue.append(frame)
            self.queue_condition.notify_all()
            self.queue_mutex.release()

            frame_index += 1

    def get_next_frame(self):
        queue_item = None
        self.queue_mutex.acquire()

        while True:
            # logging.info(f'Capture thread: Capture queue len = {len(self.queue)}')
            if len(self.queue) > 0:
                # # get last element from queue
                # queue_item = self.queue[-1]

                # # clear queue
                # self.queue.clear()

                # higher values increases latency
                buffer_len = 1
                if len(self.queue) > buffer_len:
                    # logging.warn('Images queueing up')
                    # logging.warn(f'len={len(self.queue)}')
                    del self.queue[:-buffer_len]
                    # logging.warn(f'len={len(self.queue)}')

                queue_item = self.queue[0]
                del self.queue[0]

                break
            else:
                logging.info("get_next_frame: Queue empty - going to wait ...")
                self.queue_condition.wait()
                logging.info("get_next_frame: Woke up.")

        self.queue_mutex.release()

        assert queue_item is not None
        return queue_item

    def set_enable_capture(self, enable_capture):
        if enable_capture:
            logging.info("Capturing enabled ...")
        else:
            logging.info("Capturing disabled ...")
        self.enable_capture = enable_capture
