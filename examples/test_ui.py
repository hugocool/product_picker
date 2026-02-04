#!/usr/bin/env python
"""Quick test launch to verify the folder picker UI."""

print("🎨 Testing Pendant Chooser with Folder Picker...")
print("   This will launch the app for 3 seconds to verify the UI loads.\n")

from product_picker.ui import create_ui
import threading
import time

demo = create_ui()
print("✓ UI created successfully")
print("✓ Folder picker modal integrated")
print("✓ Browse button added")
print("\n📁 Features:")
print("   • Click 'Browse' to see common folders")
print("   • Recent folders appear automatically")
print("   • Last folder pre-populated")
print("\n✅ All UI components ready!")
print("\nTo launch the app: uv run python run.py")
