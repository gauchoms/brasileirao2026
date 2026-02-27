from datetime import datetime
import pytz

def converter_utc_brasilia(data_utc):
    """Converte datetime UTC para horário de Brasília"""
    if not data_utc:
        return None
    
    # Se já tem timezone, converte
    if data_utc.tzinfo:
        brasilia = pytz.timezone('America/Sao_Paulo')
        return data_utc.astimezone(brasilia)
    
    # Se não tem timezone, assume UTC e converte
    utc = pytz.UTC
    data_com_tz = utc.localize(data_utc)
    brasilia = pytz.timezone('America/Sao_Paulo')
    return data_com_tz.astimezone(brasilia)