"""Database operations and engine management."""

from pathlib import Path
from typing import Any, Dict

from sqlmodel import Session, SQLModel, create_engine


ENGINE_CACHE: Dict[str, Any] = {}


def _db_path_for_folder(folder: str) -> Path:
    """Get the database path for a given folder."""
    p = Path(folder).expanduser().resolve()
    return p / ".pendant_ranker" / "pendants.sqlite"


def get_engine(folder: str):
    """Get or create a SQLAlchemy engine for the given folder."""
    folder_abs = str(Path(folder).expanduser().resolve())
    if folder_abs in ENGINE_CACHE:
        return ENGINE_CACHE[folder_abs]

    db_path = _db_path_for_folder(folder_abs)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    engine = create_engine(f"sqlite:///{db_path}", echo=False)
    SQLModel.metadata.create_all(engine)
    ENGINE_CACHE[folder_abs] = engine
    return engine


def reset_database(folder: str):
    """Reset the database for a given folder."""
    folder_abs = str(Path(folder).expanduser().resolve())
    db_path = _db_path_for_folder(folder_abs)
    if db_path.exists():
        db_path.unlink()
    # clear engine cache
    ENGINE_CACHE.pop(folder_abs, None)
    # recreate empty DB
    _ = get_engine(folder_abs)
    return db_path


def get_session(folder: str) -> Session:
    """Create a new database session for the given folder."""
    engine = get_engine(folder)
    return Session(engine)
