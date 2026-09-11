"""Time formatting helpers shared by the dashboard."""


def fmt_hm(total_seconds: int) -> str:
    """12345 -> '3h 25m'  |  720 -> '12m'  |  45 -> '45s'"""
    total_seconds = max(0, int(total_seconds))
    h, rem = divmod(total_seconds, 3600)
    m, s = divmod(rem, 60)
    if h > 0:
        return f"{h}h {m}m"
    if m > 0:
        return f"{m}m"
    return f"{s}s"


def fmt_clock(seconds_of_day: int) -> str:
    """Seconds since midnight -> '09:24 AM'."""
    seconds_of_day = max(0, int(seconds_of_day)) % 86400
    h24, rem = divmod(seconds_of_day, 3600)
    m, _ = divmod(rem, 60)
    ampm = "AM" if h24 < 12 else "PM"
    h12 = h24 % 12 or 12
    return f"{h12:02d}:{m:02d} {ampm}"


def hour_label(hour: int) -> str:
    """0 -> '12a', 9 -> '9a', 13 -> '1p', 23 -> '11p'"""
    hour = hour % 24
    if hour == 0:
        return "12a"
    if hour < 12:
        return f"{hour}a"
    if hour == 12:
        return "12p"
    return f"{hour - 12}p"
