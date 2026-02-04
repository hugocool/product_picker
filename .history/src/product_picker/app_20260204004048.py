"""Main application entry point."""

from product_picker.config import load_last_folder
from product_picker.ui import create_ui


def launch_app(share: bool = False, inline: bool = False, auto_load: bool = True, **kwargs):
    """
    Launch the Gradio app.

    Args:
        share: Whether to create a public share link
        inline: Whether to display inline (for notebooks)
        auto_load: Whether to auto-load the last used folder on startup
        **kwargs: Additional arguments passed to demo.launch()
    """
    demo = create_ui()

    # Auto-load last folder if available
    if auto_load:
        last_folder = load_last_folder()
        if last_folder:
            print(f"💡 Tip: Click 'Load / Rescan' to continue with: {last_folder}")

    demo.launch(share=share, inline=inline, **kwargs)


if __name__ == "__main__":
    launch_app()
