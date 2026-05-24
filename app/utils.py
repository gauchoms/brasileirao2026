from datetime import datetime
import pytz


def converter_utc_brasilia(data_utc):
    """
    Converte datetime (ou string ISO) UTC para horário de Brasília.
    Aceita tanto objetos datetime quanto strings no formato da API Football.
    """
    if not data_utc:
        return None

    # Se for string, tenta parsear os formatos comuns da API Football
    if isinstance(data_utc, str):
        formatos = [
            '%Y-%m-%dT%H:%M:%S%z',    # "2026-06-11T19:00:00+00:00"
            '%Y-%m-%dT%H:%M:%S',       # "2026-06-11T19:00:00"
            '%Y-%m-%dT%H:%M',          # "2026-06-11T19:00"
            '%Y-%m-%d %H:%M:%S',       # "2026-06-11 19:00:00"
            '%Y-%m-%d %H:%M',          # "2026-06-11 19:00"
        ]
        parsed = None
        for fmt in formatos:
            try:
                parsed = datetime.strptime(data_utc, fmt)
                break
            except ValueError:
                continue
        if not parsed:
            return None
        data_utc = parsed

    brasilia = pytz.timezone('America/Sao_Paulo')

    # Se já tem timezone, converte diretamente
    if data_utc.tzinfo:
        return data_utc.astimezone(brasilia)

    # Se não tem timezone, assume UTC e converte
    return pytz.UTC.localize(data_utc).astimezone(brasilia)
