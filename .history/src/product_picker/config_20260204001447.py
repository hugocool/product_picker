"""Configuration and state persistence."""

from pathlib import Path
from typing import Optional
import json


def get_config_path() -> Path:
    """Get the path to the config file in user's home directory."""
    return Path.home() / ".pendant_chooser" / "config.json"


def save_last_folder(folder: str) -> None:
    """Save the last used folder to config."""
    config_path = get_config_path()
    config_path.parent.mkdir(parents=True, exist_ok=True)
    
    config = {}
    if config_path.exists():
        try:
            config = json.loads(config_path.read_text())
        except Exception:
            pass
    
    config["last_folder"] = folder
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
