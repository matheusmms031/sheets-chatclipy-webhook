import re

_DIGITS_RE = re.compile(r"\D")


def normalize_br_phone(raw: str) -> str | None:
    """Normaliza números brasileiros digitados livremente num formulário.

    Aceita variações como "(45) 99858-3615", "48988888888" ou já com o
    código do país ("5511915384263"). Retorna None quando não dá pra
    extrair um número plausível (ex: "#ERROR!").
    """
    digits = _DIGITS_RE.sub("", raw or "")

    if len(digits) in (10, 11):
        digits = "55" + digits

    if len(digits) not in (12, 13):
        return None

    return digits
