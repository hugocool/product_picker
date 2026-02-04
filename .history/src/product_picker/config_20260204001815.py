"""Configuration and state persistence."""

from pathlib import Path
from typing import Optional, List
import json


def get_config_path() -> Path:
    """Get the path to the config file in user's home directory."""
    return Path.home() / ".pendant_chooser" / "config.json"


def save_last_folder(folder: str) -> None:
    """Save the last used folder to config and add to recent folders."""
    config_path = get_config_path()
    config_path.parent.mkdir(parents=True, exist_ok=True)
    
    config = {}
    if config_path.exists():
        try:
            config = json.loads(config_path.read_text())
        except Exception:
            pass
    
    config["last_folder"] = folder
    
    # Add to recent folders (keep last 10)
    recent = config.get("recent_folders", [])
    if folder in recent:
        recent.remove(folder)
    recent.insert(0, folder)
    config["recent_folders"] = recent[:10]
    
    config_path.write_text(json.dumps(config, indent=2))


def load_last_folder() -> Optional[str]:
    """Load the last used folder from config."""
    config_path = get_config_path()
    if not config_path.exists():
        return None
    
    try:
        config = json.loads(config_path.read_text())
        folder = config.get("last_folder")
        if folder and Path(folder).exists():
            return folder
    except Exception:
        pass
    
    return None


def get_recent_folders() -> List[str]:
    """Get list of recently used folders that still exist."""
    config_path = get_config_path()
    if not config_path.exists():
        return []
    
    try:
        config = json.loads(config_path.read_text())
        recent = config.get("recent_folders", [])
        # Filter to only existing folders
        return [f for f in recent if Path(f).exists()]
    except Exception:
        return []


def get_common_folders() -> List[tuple[str, str]]:
    """Get common folder locations (name, path)."""
    home = Path.home()
    folders = [
        ("Home", str(home)),
        ("Desktop", str(home / "Desktop")),
        ("Documents", str(home / "Documents")),
        ("Downloads", str(home / "Downloads")),
        ("Pictures", str(home / "Pictures")),
    ]
    # Only return folders that exist
    return [(name, path) for name, path in folders if Path(path).exists()]
