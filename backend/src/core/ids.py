from __future__ import annotations

import re
from hashlib import sha256


def slugify(value: str, fallback: str = "source") -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.lower()).strip("-")
    return slug or fallback


def stable_id(*parts: str) -> str:
    digest = sha256("\n".join(parts).encode("utf-8")).hexdigest()
    return digest[:24]
