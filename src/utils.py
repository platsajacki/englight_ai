import re


def has_russian(text: str) -> bool:
    return bool(re.search(r'[А-Яа-яЁё]', text))
