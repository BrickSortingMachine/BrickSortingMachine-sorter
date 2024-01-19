import os


def human_file_size(fn):
    size = os.path.getsize(fn)
    for unit in ["B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB"]:
        if abs(size) < 1024.0:
            return "%3.1f%s" % (size, unit)
        size /= 1024.0
    return "%.1f%s" % (size, "YB")
