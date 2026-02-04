# Folder Persistence Feature

## What's New

✅ **Auto-remembers last folder** - The app now saves your last used folder and pre-loads it on next launch

✅ **Hidden folder structure** - Everything stored neatly:

- Database: `YOUR_FOLDER/.pendant_ranker/pendants.sqlite`
- Config: `~/.pendant_chooser/config.json`

✅ **Pick up where you left off** - Just load the same folder to continue ranking

## Implementation

### Files Added

- `src/product_picker/config.py` - Configuration persistence
- `tests/test_config.py` - Unit tests for config
- `examples/folder_persistence.py` - Demo script

### Files Modified

- `src/product_picker/ui.py` - Auto-populate last folder, show helpful tip
- `src/product_picker/app.py` - Print tip on startup
- `README.md` - Document persistence feature
- `QUICKSTART.md` - Update data storage section

## How It Works

1. **First Time Use**
   - User enters folder path
   - Clicks "Load / Rescan"
   - Folder path saved to `~/.pendant_chooser/config.json`
   - Database created at `FOLDER/.pendant_ranker/pendants.sqlite`

2. **Next Launch**
   - App automatically loads last folder path into textbox
   - Shows tip: "💡 Last folder pre-loaded. Click 'Load / Rescan' to continue"
   - User just clicks "Load / Rescan" to continue

3. **Multiple Folders**
   - Each folder has its own database (in `.pendant_ranker/`)
   - Config remembers the most recently used one
   - Switch between folders anytime

## Testing

All 5 tests passing:

```bash
uv run pytest tests/ -v
```

Tests verify:

- Config save/load functionality
- Path generation
- Graceful handling of missing config

## Example Usage

```python
from product_picker.config import save_last_folder, load_last_folder

# Save a folder
save_last_folder("/Users/me/pendants")

# Later...
folder = load_last_folder()
print(folder)  # "/Users/me/pendants"
```
