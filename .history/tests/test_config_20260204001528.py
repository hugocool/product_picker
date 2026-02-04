"""Tests for config persistence."""

from pathlib import Path
import tempfile

from product_picker.config import save_last_folder, load_last_folder, get_config_path


def test_save_and_load_folder():
    """Test saving and loading last folder."""
    # Use a temp directory for testing
    with tempfile.TemporaryDirectory() as tmpdir:
        test_folder = str(Path(tmpdir) / "test_pendants")
        Path(test_folder).mkdir()
        
        # Save folder
        save_last_folder(test_folder)
        
        # Load it back
        loaded = load_last_folder()
        assert loaded == test_folder


def test_load_nonexistent_folder():
    """Test loading when config doesn't exist yet."""
    # This should not crash
    folder = load_last_folder()
    assert folder is None or isinstance(folder, str)


def test_config_path():
    """Test config path is in home directory."""
    config_path = get_config_path()
    assert config_path.parent.name == ".pendant_chooser"
    assert config_path.name == "config.json"
