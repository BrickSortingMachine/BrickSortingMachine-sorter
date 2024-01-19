def first_index(a, f):
    for index, item in enumerate(a):
        if f(item):
            return index
    return -1


def last_index(a, f):
    for index, item in reversed(list(enumerate(a))):
        if f(item):
            return index
    return -1


def count_if(a, f):
    c = 0
    for item in a:
        if f(item):
            c += 1
    return c
