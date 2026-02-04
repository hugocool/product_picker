"""Image loading and processing utilities."""

import hashlib
from pathlib import Path

from PIL import Image, ImageOps

from product_picker.models import Pendant


SUPPORTED_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}


def sha256_file(path: Path) -> str:
    """Calculate SHA-256 hash of a file."""
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def pendant_abs_path(p: Pendant) -> Path:
    """Get absolute path for a pendant."""
    return Path(p.folder) / p.rel_path


def load_image_for_display(p: Pendant, max_side: int = 900) -> Image.Image:
    """
    Load and prepare a pendant image for display.

    Args:
        p: Pendant to load image for
        max_side: Maximum dimension (width or height) in pixels

    Returns:
        PIL Image ready for display
    """
    img = Image.open(pendant_abs_path(p))
    img = ImageOps.exif_transpose(img)  # Handle EXIF orientation
    img = img.convert("RGB")

    w, h = img.size
    scale = min(max_side / max(w, h), 1.0)
    if scale < 1.0:
        img = img.resize((int(w * scale), int(h * scale)), Image.Resampling.LANCZOS)

    return img


def find_image_files(folder: Path, recursive: bool = True) -> list[Path]:
    """
    Find all supported image files in a folder.

    Args:
        folder: Folder to search
        recursive: Whether to search recursively

    Returns:
        List of image file paths
    """
    pattern_iter = folder.rglob("*") if recursive else folder.glob("*")

    files = []
    for fp in pattern_iter:
        if fp.is_file() and fp.suffix.lower() in SUPPORTED_EXTS:
            files.append(fp)

    return files
