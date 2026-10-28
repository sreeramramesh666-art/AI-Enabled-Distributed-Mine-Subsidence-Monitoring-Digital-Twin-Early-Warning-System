import html
import re
from datetime import datetime
from typing import Optional, Union

def sanitize_text(text: str) -> str:
    """Sanitize user-provided text inputs against basic injection & XSS."""
    if not text:
        return ""
    cleaned = html.escape(text.strip())
    cleaned = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", cleaned)
    return cleaned

def validate_node_id(node_id: str) -> bool:
    """Ensure node identifier conforms to safe alphanumeric identifier format."""
    return bool(re.match(r"^[A-Za-z0-9_\-\.]{2,64}$", node_id))

def parse_query_datetime(val: Optional[Union[str, datetime]]) -> Optional[datetime]:
    """
    Robust ISO 8601 query parameter datetime parser.
    Handles 'Z' suffixes and '+' unencoded spaces in query strings.
    """
    if val is None:
        return None
    if isinstance(val, datetime):
        return val
    s = str(val).strip()
    if not s:
        return None
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(s)
    except Exception:
        pass

    if " " in s:
        parts = s.rsplit(" ", 1)
        if len(parts) == 2 and re.match(r"^\d{2}(:?\d{2})?$", parts[1]):
            candidate = f"{parts[0]}+{parts[1]}"
            try:
                return datetime.fromisoformat(candidate)
            except Exception:
                pass
    raise ValueError(f"Invalid ISO 8601 datetime format '{val}'")
