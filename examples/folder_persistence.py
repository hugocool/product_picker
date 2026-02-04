"""Demo showing folder persistence."""

from product_picker.config import save_last_folder, load_last_folder
from pathlib import Path
import tempfile

print("🎨 Pendant Chooser - Folder Persistence Demo\n")

# Simulate using the app with a folder
with tempfile.TemporaryDirectory() as tmpdir:
    test_folder = str(Path(tmpdir) / "my_pendants")
    Path(test_folder).mkdir()
    
    print(f"1️⃣  First time: Using folder: {test_folder}")
    save_last_folder(test_folder)
    print("   ✓ Folder saved to config\n")
    
    print("2️⃣  Next time you launch the app:")
    loaded = load_last_folder()
    print(f"   ✓ Auto-loaded: {loaded}")
    print(f"   ✓ Matches: {loaded == test_folder}\n")

print("📁 Config location: ~/.pendant_chooser/config.json")
print("📁 Database location: YOUR_FOLDER/.pendant_ranker/pendants.sqlite")
print("\n✨ Everything is stored in hidden folders!")
print("   - Progress persists across sessions")
print("   - Last folder auto-loads on startup")
print("   - Database unique to each pendant folder")
