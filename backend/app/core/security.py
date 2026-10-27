import html
import re

def sanitize_text(text: str) -> str:
    """Sanitize user-provided text inputs against basic injection & XSS."""
    if not text:
        return ""
    # Strip dangerous HTML tags
    cleaned = html.escape(text.strip())
    # Remove control characters
    cleaned = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", cleaned)
    return cleaned

def validate_node_id(node_id: str) -> bool:
    """Ensure node identifier conforms to safe alphanumeric identifier format."""
    return bool(re.match(r"^[A-Za-z0-9_\-\.]{2,64}$", node_id))
