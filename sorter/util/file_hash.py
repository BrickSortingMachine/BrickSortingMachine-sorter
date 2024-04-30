import hashlib


def file_hash(file_name: str):
    BUF_SIZE = 65536
    sha1 = hashlib.sha1()
    with open(file_name, "rb") as f:
        while True:
            data = f.read(BUF_SIZE)
            if not data:
                break
            sha1.update(data)
    return "{0}".format(sha1.hexdigest())
