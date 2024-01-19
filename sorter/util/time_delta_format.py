unit_list = [
    {"n": "h", "v": 60 * 60},
    {"n": "m", "v": 60},
    {"n": "s", "v": 1},
]


def time_delta_format(total_sec):
    if total_sec is None:
        return ""

    remainder_sec = total_sec
    res = ""
    for unit in unit_list:
        amount = remainder_sec // unit["v"]
        remainder_sec -= amount * unit["v"]
        if amount > 0:
            res += f"{amount:.0f}" + unit["n"] + " "
    return res.rstrip()
