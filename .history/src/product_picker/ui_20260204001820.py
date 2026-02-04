"""Gradio UI for pendant comparison."""

from pathlib import Path
from typing import Optional, Tuple

import gradio as gr
import pandas as pd
from PIL import Image

from product_picker.config import (
    load_last_folder,
    save_last_folder,
    get_recent_folders,
    get_common_folders,
)
from product_picker.database import get_session, reset_database
from product_picker.display import get_leaderboard, get_match_history, get_pendant_by_id
from product_picker.images import load_image_for_display
from product_picker.matching import choose_next_pair, record_match
from product_picker.rating import conservative_score, update_ratings
from product_picker.scanner import scan_folder


def render_pair(
    folder: str, left_id: int, right_id: int
) -> Tuple[Image.Image, Image.Image, str, str]:
    """Render a pair of pendant images with their info."""
    left = get_pendant_by_id(folder, left_id)
    right = get_pendant_by_id(folder, right_id)

    if left is None or right is None:
        raise ValueError("Pendant not found")

    left_img = load_image_for_display(left)
    right_img = load_image_for_display(right)

    left_md = (
        f"**LEFT**\n\n"
        f"- id: `{left.id}`\n"
        f"- file: `{left.rel_path}`\n"
        f"- mu: `{left.mu:.3f}` | sigma: `{left.sigma:.3f}`\n"
        f"- score(mu-3σ): `{conservative_score(left.mu, left.sigma):.3f}`\n"
        f"- W/L/D: `{left.wins}/{left.losses}/{left.draws}` (games={left.games})"
    )
    right_md = (
        f"**RIGHT**\n\n"
        f"- id: `{right.id}`\n"
        f"- file: `{right.rel_path}`\n"
        f"- mu: `{right.mu:.3f}` | sigma: `{right.sigma:.3f}`\n"
        f"- score(mu-3σ): `{conservative_score(right.mu, right.sigma):.3f}`\n"
        f"- W/L/D: `{right.wins}/{right.losses}/{right.draws}` (games={right.games})"
    )

    return left_img, right_img, left_md, right_md


def load_folder_and_first_pair(folder: str):
    """Scan folder and load first pair to compare."""
    folder_abs = str(Path(folder).expanduser().resolve())
    
    # Save this folder as the last used
    save_last_folder(folder_abs)
    
    hist = get_match_history(folder_abs, limit=25)

    nxt = choose_next_pair(folder_abs)
    if nxt is None:
        status = (
            f"Scanned `{folder_abs}` — found {stats['found']}, "
            f"added {stats['added']}, skipped {stats['skipped']}. "
            f"Need at least 2 images."
        )
        return folder_abs, None, None, status, None, None, "", "", lb, hist, ""

    left_id, right_id = nxt
    left_img, right_img, left_md, right_md = render_pair(folder_abs, left_id, right_id)

    status = (
        f"Scanned `{folder_abs}` — found **{stats['found']}**, "
        f"added **{stats['added']}**, skipped **{stats['skipped']}**.\n\n"
        f"Showing next comparison."
    )
    return (
        folder_abs,
        left_id,
        right_id,
        status,
        left_img,
        right_img,
        left_md,
        right_md,
        lb,
        hist,
        "",
    )


def decide_and_advance(folder: str, left_id: Optional[int], right_id: Optional[int], outcome: str):
    """Process outcome and advance to next pair."""
    folder_abs = str(Path(folder).expanduser().resolve())

    if left_id is None or right_id is None:
        return (
            None,
            None,
            "No active pair. Load a folder first.",
            None,
            None,
            "",
            "",
            get_leaderboard(folder_abs),
            get_match_history(folder_abs),
            "",
        )

    # Update ratings and record match
    with get_session(folder_abs) as session:
        left = get_pendant_by_id(folder_abs, left_id)
        right = get_pendant_by_id(folder_abs, right_id)

        if left is None or right is None:
            return (
                None,
                None,
                "Error: Pendant not found",
                None,
                None,
                "",
                "",
                get_leaderboard(folder_abs),
                get_match_history(folder_abs),
                "",
            )

        # Record match
        record_match(session, folder_abs, left_id, right_id, outcome)

        # Update ratings if not skip
        if outcome in {"L", "R", "D"}:
            update_ratings(left, right, outcome)
            session.add(left)
            session.add(right)

        session.commit()

    # Get updated data
    lb = get_leaderboard(folder_abs, limit=50)
    hist = get_match_history(folder_abs, limit=25)

    # Result message
    if outcome == "L":
        last = "Last result: **LEFT won**"
    elif outcome == "R":
        last = "Last result: **RIGHT won**"
    elif outcome == "D":
        last = "Last result: **DRAW**"
    else:
        last = "Last result: **SKIP**"

    # Get next pair
    nxt = choose_next_pair(folder_abs)
    if nxt is None:
        return None, None, "Done (or not enough images).", None, None, "", "", lb, hist, last

    nL, nR = nxt
    left_img, right_img, left_md, right_md = render_pair(folder_abs, nL, nR)
    return (
        nL,
        nR,
        "Showing next comparison.",
        left_img,
        right_img,
        left_md,
        right_md,
        lb,
        hist,
        last,
    )


def reset_db(folder: str):
    """Reset database for folder."""
    folder_abs = str(Path(folder).expanduser().resolve())
    db_path = reset_database(folder_abs)
    return f"Reset DB at `{db_path}`. Now rescan the folder.", pd.DataFrame(), pd.DataFrame()


def create_ui() -> gr.Blocks:
    """Create the Gradio Blocks UI."""
    # Load last folder if available
    initial_folder = load_last_folder() or ""
    initial_info = ""
    if initial_folder:
        initial_info = f"💡 **Tip:** Last folder pre-loaded. Click 'Load / Rescan' to continue: `{initial_folder}`"
    
    with gr.Blocks(title="Pendant Chooser") as demo:
        gr.Markdown("# Pendant Chooser — pairwise comparisons (TrueSkill)")
        
        folder_state = gr.State(value="")
        left_id_state = gr.State(value=None)
        right_id_state = gr.State(value=None)
        
        with gr.Row():
            folder_tb = gr.Textbox(
                label="Folder path containing pendant images",
                placeholder="/absolute/path/to/pendants",
                value=initial_folder,
                scale=4,
            )
            load_btn = gr.Button("Load / Rescan", scale=1, variant="primary")
            reset_btn = gr.Button("Reset DB", scale=1)
        
        status_md = gr.Markdown(initial_info)

        with gr.Row(equal_height=True):
            left_img = gr.Image(type="pil", label="Left", scale=1)
            right_img = gr.Image(type="pil", label="Right", scale=1)

        with gr.Row():
            left_choice = gr.Button("⬅️ Left wins", scale=1)
            draw_choice = gr.Button("🤝 Draw", scale=1)
            right_choice = gr.Button("Right wins ➡️", scale=1)
            skip_choice = gr.Button("Skip", scale=1)

        last_result_md = gr.Markdown()

        with gr.Row():
            left_info = gr.Markdown()
            right_info = gr.Markdown()

        gr.Markdown("## Leaderboard (sorted by conservative score = mu − 3σ)")
        leaderboard = gr.Dataframe(interactive=False, wrap=True)

        gr.Markdown("## Recent match history (which one won)")
        history = gr.Dataframe(interactive=False, wrap=True)

        # Event handlers
        load_btn.click(
            load_folder_and_first_pair,
            inputs=[folder_tb],
            outputs=[
                folder_state,
                left_id_state,
                right_id_state,
                status_md,
                left_img,
                right_img,
                left_info,
                right_info,
                leaderboard,
                history,
                last_result_md,
            ],
        )

        reset_btn.click(
            reset_db,
            inputs=[folder_tb],
            outputs=[status_md, leaderboard, history],
        )

        def _decide(outcome, folder, left_id, right_id):
            return decide_and_advance(folder, left_id, right_id, outcome)

        left_choice.click(
            lambda folder, left_id, right_id: _decide("L", folder, left_id, right_id),
            inputs=[folder_state, left_id_state, right_id_state],
            outputs=[
                left_id_state,
                right_id_state,
                status_md,
                left_img,
                right_img,
                left_info,
                right_info,
                leaderboard,
                history,
                last_result_md,
            ],
        )

        right_choice.click(
            lambda folder, left_id, right_id: _decide("R", folder, left_id, right_id),
            inputs=[folder_state, left_id_state, right_id_state],
            outputs=[
                left_id_state,
                right_id_state,
                status_md,
                left_img,
                right_img,
                left_info,
                right_info,
                leaderboard,
                history,
                last_result_md,
            ],
        )

        draw_choice.click(
            lambda folder, left_id, right_id: _decide("D", folder, left_id, right_id),
            inputs=[folder_state, left_id_state, right_id_state],
            outputs=[
                left_id_state,
                right_id_state,
                status_md,
                left_img,
                right_img,
                left_info,
                right_info,
                leaderboard,
                history,
                last_result_md,
            ],
        )

        skip_choice.click(
            lambda folder, left_id, right_id: _decide("S", folder, left_id, right_id),
            inputs=[folder_state, left_id_state, right_id_state],
            outputs=[
                left_id_state,
                right_id_state,
                status_md,
                left_img,
                right_img,
                left_info,
                right_info,
                leaderboard,
                history,
                last_result_md,
            ],
        )

    return demo
