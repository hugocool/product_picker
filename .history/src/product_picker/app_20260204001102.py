"""Main application entry point."""

from product_picker.ui import create_ui


def launch_app(share: bool = False, inline: bool = False, **kwargs):
    """
    Launch the Gradio app.
    
    Args:
        share: Whether to create a public share link
        inline: Whether to display inline (for notebooks)
        **kwargs: Additional arguments passed to demo.launch()
    """
    demo = create_ui()
    demo.launch(share=share, inline=inline, **kwargs)


if __name__ == "__main__":
    launch_app()
