from datetime import datetime, timezone

def remove_tz(dt):
    """Convierte datetime con timezone a naive datetime"""
    if dt is None:
        return None
    return dt.replace(tzinfo=None) if dt.tzinfo else dt

def now_naive():
    """Devuelve la fecha/hora actual sin timezone"""
    return datetime.now().replace(tzinfo=None)

def utcnow():
    return datetime.now(timezone.utc)