from datetime import date

MESES = [
    "ene", "feb", "mar", "abr", "may", "jun",
    "jul", "ago", "sep", "oct", "nov", "dic",
]

DIAS = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]


def format_day(day: date) -> str:
    return f"{DIAS[day.weekday()]} {day.day}"


def format_week_range(start: date, end: date) -> str:
    if start.month == end.month:
        return f"{start.day}–{end.day} {MESES[end.month - 1]} {end.year}"
    return (
        f"{start.day} {MESES[start.month - 1]} – "
        f"{end.day} {MESES[end.month - 1]} {end.year}"
    )


def format_number(value: float) -> str:
    if value == int(value):
        return f"{int(value):,}"
    return f"{value:,.1f}"


def parse_number(text: str) -> float:
    text = text.strip().replace(" ", "")
    if "," in text and "." in text:
        text = text.replace(",", "")
    else:
        text = text.replace(",", ".")
    return float(text)
