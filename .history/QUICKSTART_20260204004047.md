# Quick Start Guide

## Installation

```bash
# Install dependencies with uv (fast!)
uv sync

# For development (includes Jupyter, pytest, etc.)
uv sync --extra dev
```

## Running the App

### Option 1: Quick Launch Script

```bash
uv run python run.py
```

### Option 2: As a Module

```bash
uv run python -m product_picker
```

### Option 3: From Python

```python
from product_picker import launch_app
launch_app()
```

### Option 4: Jupyter Notebook

Open `notebooks/pendant_chooser.ipynb` in Jupyter Lab or VS Code.

## How to Use

1. **Open the Gradio UI** - A browser window will open automatically
2. **Select your folder**:
   - Click **📁 Browse** to see common folders (Desktop, Documents, Pictures, etc.)
   - Or choose from recently used folders
   - Or type/paste the path manually
3. **Click "Load / Rescan"** - The app will scan and index all images
4. **Start comparing** - Click "Left wins", "Right wins", "Draw", or "Skip" for each pair
5. **Watch the leaderboard** - Rankings update in real-time using TrueSkill algorithm
6. **Come back later** - Your progress is saved! Just load the same folder to continue

## Project Structure

```
product_picker/
├── src/product_picker/      # Main package
│   ├── models.py            # Database models (Pendant, Match)
│   ├── database.py          # SQLite engine management
│   ├── rating.py            # TrueSkill rating logic
│   ├── images.py            # Image loading/processing
│   ├── scanner.py           # Folder scanning
│   ├── matching.py          # Smart pair selection
│   ├── display.py           # Leaderboard/history display
│   ├── ui.py                # Gradio interface
│   └── app.py               # Main entry point
├── notebooks/               # Jupyter notebooks
├── tests/                   # Unit tests
├── examples/                # Example scripts
└── run.py                   # Quick launch script
```

## Data Storage

- **Database**: `YOUR_FOLDER/.pendant_ranker/pendants.sqlite` (hidden folder)
- **Config**: `~/.pendant_chooser/config.json` (remembers last folder)
- Automatically created when you first scan a folder
- Persists across sessions - pick up where you left off!
- SHA-256 hashing prevents duplicates

## Tips

- **Start with 10-20 comparisons** to see initial rankings emerge
- **High uncertainty (σ)** items are prioritized for comparison
- **Conservative score (μ - 3σ)** prevents barely-tested items from ranking high
- Use **"Skip"** if both images are equally good/bad or you're unsure
- Use **"Draw"** if they're genuinely tied in quality

## Running Tests

```bash
uv run pytest tests/ -v
```

## Troubleshooting

**App won't launch?**

- Check that port 7860 is available
- Try: `launch_app(server_port=7861)` to use a different port

**Images not loading?**

- Verify folder path is absolute
- Check file extensions are supported (JPG, PNG, WEBP, BMP, TIFF)
- Look for scanning errors in the status message

**Want to start over?**

- Click "Reset DB" button in the UI
- Or manually delete `.pendant_ranker/` folder in your images directory
