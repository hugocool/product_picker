"""Scanning folders and managing pendant database."""

from pathlib import Path
from typing import Dict

from sqlmodel import select

from product_picker.database import get_session
from product_picker.images import find_image_files, sha256_file
from product_picker.models import Pendant


def scan_folder(folder: str, recursive: bool = True) -> Dict[str, int]:
    """
    Scan a folder for pendant images and add new ones to the database.

    Args:
        folder: Path to folder containing images
        recursive: Whether to search recursively

    Returns:
        Dictionary with 'found', 'added', and 'skipped' counts
    """
    folder_p = Path(folder).expanduser().resolve()
    if not folder_p.exists() or not folder_p.is_dir():
        raise ValueError(f"Folder does not exist or is not a directory: {folder_p}")

    files = find_image_files(folder_p, recursive=recursive)

    added = 0
    skipped = 0

    with get_session(str(folder_p)) as session:
        # Get existing hashes for this folder
        existing = session.exec(select(Pendant.sha256).where(Pendant.folder == str(folder_p))).all()
        existing_set = set(existing)

        for fp in files:
            try:
                sha = sha256_file(fp)
            except Exception:
                skipped += 1
                continue

            if sha in existing_set:
                skipped += 1
                continue

            rel = str(fp.relative_to(folder_p))
            p = Pendant(
                folder=str(folder_p),
                rel_path=rel,
                sha256=sha,
                mu=25.0,
                sigma=25.0 / 3.0,
            )
            session.add(p)
            existing_set.add(sha)
            added += 1

        session.commit()

    return {"found": len(files), "added": added, "skipped": skipped}
