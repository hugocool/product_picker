"""Database models for pendants and matches."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


class Pendant(SQLModel, table=True):
    """Represents a pendant image with TrueSkill ratings."""

    id: Optional[int] = Field(default=None, primary_key=True)
    folder: str = Field(index=True)  # absolute folder path
    rel_path: str = Field(index=True)  # relative to folder
    sha256: str = Field(index=True)  # content hash for de-dup
    created_at_utc: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    # TrueSkill parameters
    mu: float = 25.0
    sigma: float = 25.0 / 3.0

    # Simple counters
    games: int = 0
    wins: int = 0
    losses: int = 0
    draws: int = 0


class Match(SQLModel, table=True):
    """Represents a single comparison between two pendants."""

    id: Optional[int] = Field(default=None, primary_key=True)
    folder: str = Field(index=True)

    shown_left_id: int = Field(index=True)
    shown_right_id: int = Field(index=True)

    # canonical pair for counting repeats
    pair_a_id: int = Field(index=True)
    pair_b_id: int = Field(index=True)

    # "L" | "R" | "D" | "S" (left/right/draw/skip)
    outcome: str = Field(index=True)

    created_at_utc: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
