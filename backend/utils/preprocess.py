import re


def preprocess(text: str) -> str:
    """Clean and normalize input text before analysis."""
    # Strip leading/trailing whitespace
    text = text.strip()

    # Normalize multiple spaces to single space
    text = re.sub(r" {2,}", " ", text)

    # Normalize multiple newlines to max 2
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Remove null bytes or weird control chars
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)

    return text



def truncate(text: str, max_chars: int = 4000) -> str:
    """Truncate text to avoid hitting token limits."""
    if len(text) > max_chars:
        return text[:max_chars] + "..."
    return text


def prepare(text: str) -> str:
    return truncate(preprocess(text))
