"""Demo the folder picker feature."""

from product_picker.config import get_common_folders, get_recent_folders

print("🎨 Pendant Chooser - Folder Picker Demo\n")

print("📁 Common Folders Available:")
for name, path in get_common_folders():
    print(f"   • {name}: {path}")

print("\n🕐 Recent Folders:")
recent = get_recent_folders()
if recent:
    for folder in recent:
        print(f"   • {folder}")
else:
    print("   (None yet - use the app to build history)")

print("\n✨ New Feature: Folder Picker Modal")
print("   1. Click '📁 Browse' button")
print("   2. Choose from:")
print("      • Common folders (Desktop, Documents, Downloads, Pictures)")
print("      • Recently used folders")
print("   3. Or type/paste path manually")
print("\nNo more copying paths from Finder!")
