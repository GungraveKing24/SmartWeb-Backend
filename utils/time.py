from datetime import datetime, timezone

def utcnow():
    return datetime.now(timezone.utc)

def remove_tz(dt):
    if dt is None:
        return None
    return dt.replace(tzinfo=None)

def now_naive():
    return datetime.now().replace(tzinfo=None)