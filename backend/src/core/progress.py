from __future__ import annotations

from collections.abc import Callable
from typing import TypedDict


class ProgressEvent(TypedDict, total=False):
    phase: str
    status: str
    message: str
    current: int
    total: int
    current_item: str


ProgressCallback = Callable[[ProgressEvent], None]
