import threading
import traceback

exception_log = []
base_exceptionhook = None


def overlay_exception_hook(args):
    # forward to standard handler
    if base_exceptionhook:
        base_exceptionhook(args)

    # traceback
    exception_msg = "\n".join(
        traceback.format_exception(args.exc_type, args.exc_value, args.exc_traceback)
    )
    exception_log.append(exception_msg)
    return exception_msg


def install():
    global exception_log
    global base_exceptionhook

    exception_log = []

    # backup base exception hook
    base_exceptionhook = threading.excepthook

    # overlay own exceptionhook
    threading.excepthook = overlay_exception_hook


def collect_thread_exceptions():
    global base_exceptionhook

    # recover base exceptionhook
    threading.excepthook = base_exceptionhook
    base_exceptionhook = None  # Clear the stored hook

    # forward exceptions in main thread
    if len(exception_log) > 0:
        raise Exception("Exceptions in all threads: " + "\n".join(exception_log))
