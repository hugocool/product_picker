"""Gradio UI for pendant comparison."""

from pathlib import Path
from typing import Optional, Tuple

import gradio as gr
import pandas as pd
from PIL import Image

from product_picker.config import load_last_folder, save_last_folder
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


def get_top_3_display(folder: str) -> Tuple[Optional[Image.Image], str, Optional[Image.Image], str, Optional[Image.Image], str]:
    """Get images and info for top 3 pendants."""
    lb = get_leaderboard(folder, limit=3)
    
    if lb.empty:
        return None, "_No data yet_", None, "_No data yet_", None, "_No data yet_"
    
    results = []
    for idx in range(3):
        if idx < len(lb):
            pendant_id = lb.iloc[idx]['id']
            pendant = get_pendant_by_id(folder, pendant_id)
            if pendant:
                img = load_image_for_display(pendant, max_side=300)
                score = lb.iloc[idx]['score(mu-3σ)']
                info = (
                    f"**{lb.iloc[idx]['file']}**\n\n"
                    f"Score: **{score:.2f}**\n"
                    f"Games: {lb.iloc[idx]['games']} "
                    f"({lb.iloc[idx]['W']}-{lb.iloc[idx]['L']}-{lb.iloc[idx]['D']})"
                )
                results.extend([img, info])
            else:
                results.extend([None, "_Error loading_"])
        else:
            results.extend([None, "_Not enough data_"])
    
    return tuple(results)



def load_folder_and_first_pair(folder):
    """Scan folder and load first pair to compare."""
    # Handle various input types
    if isinstance(folder, list):
        if not folder:
            return "", None, None, "❌ No folder selected. Click a folder in the explorer above.", None, None, "", "", pd.DataFrame(), pd.DataFrame(), "", None, "", None, "", None, ""
        folder = folder[0]
    
    if not folder or not isinstance(folder, str) or folder.strip() == "":
        return "", None, None, "❌ No folder selected. Click a folder in the explorer above.", None, None, "", "", pd.DataFrame(), pd.DataFrame(), "", None, "", None, "", None, ""
    
    folder_abs = str(Path(folder).expanduser().resolve())
    
    if not Path(folder_abs).exists():
        return "", None, None, f"❌ Folder does not exist: {folder_abs}", None, None, "", "", pd.DataFrame(), pd.DataFrame(), "", None, "", None, "", None, ""
    
    if not Path(folder_abs).is_dir():
        return "", None, None, f"❌ Not a directory: {folder_abs}", None, None, "", "", pd.DataFrame(), pd.DataFrame(), "", None, "", None, "", None, ""
    
    # Save this folder as the last used
    save_last_folder(folder_abs)
    
    stats = scan_folder(folder_abs, recursive=True)
    
    lb = get_leaderboard(folder_abs, limit=50)
    hist = get_match_history(folder_abs, limit=25)
    
    # Get top 3
    top1_img, top1_info, top2_img, top2_info, top3_img, top3_info = get_top_3_display(folder_abs)

    nxt = choose_next_pair(folder_abs)
    if nxt is None:
        status = (
            f"Scanned `{folder_abs}` — found {stats['found']}, "
            f"added {stats['added']}, skipped {stats['skipped']}. "
            f"Need at least 2 images."
        )
        return folder_abs, None, None, status, None, None, "", "", lb, hist, "", top1_img, top1_info, top2_img, top2_info, top3_img, top3_info

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
        top1_img,
        top1_info,
        top2_img,
        top2_info,
        top3_img,
        top3_info,
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
    
    # Get top 3
    top1_img, top1_info, top2_img, top2_info, top3_img, top3_info = get_top_3_display(folder_abs)

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
    # Exclude current pair if it was skipped or drawn to avoid immediate repeat
    exclude = None
    if outcome in {"S", "D"}:
        exclude = (left_id, right_id)
    
    nxt = choose_next_pair(folder_abs, exclude_pair=exclude)
    if nxt is None:
        return None, None, "Done (or not enough images).", None, None, "", "", lb, hist, last, top1_img, top1_info, top2_img, top2_info, top3_img, top3_info

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
        top1_img,
        top1_info,
        top2_img,
        top2_info,
        top3_img,
        top3_info,
    )


def reset_db(folder):
    """Reset database for folder."""
    # Handle FileExplorer output
    if isinstance(folder, list):
        if not folder:
            return "No folder selected", pd.DataFrame(), pd.DataFrame()
        folder = folder[0]
    
    if not folder or not isinstance(folder, str):
        return "No folder selected", pd.DataFrame(), pd.DataFrame()
    
    folder_abs = str(Path(folder).expanduser().resolve())
    db_path = reset_database(folder_abs)
    return f"Reset DB at `{db_path}`. Now rescan the folder.", pd.DataFrame(), pd.DataFrame()


def create_ui() -> gr.Blocks:
    """Create the Gradio Blocks UI."""
    # Load last folder if available
    initial_folder = load_last_folder() or str(Path.home())
    
    with gr.Blocks(title="Pendant Chooser") as demo:
        gr.Markdown("# Pendant Chooser — pairwise comparisons (TrueSkill)")
        
        folder_state = gr.State(value="")
        left_id_state = gr.State(value=None)
        right_id_state = gr.State(value=None)
        
        with gr.Row():
            with gr.Column(scale=3):
                folder_picker = gr.FileExplorer(
                    label="📁 Navigate and select a folder",
                    root_dir=initial_folder,
                    glob="**",
                    ignore_glob="**/.*",  # Ignore hidden files/folders
                    file_count="single",
                    height=400,
                )
            with gr.Column(scale=1):
                selected_folder = gr.Textbox(
                    label="Selected folder",
                    value=initial_folder if initial_folder != str(Path.home()) else "",
                    placeholder="Click a folder in the explorer...",
                    interactive=False,
                )
                load_btn = gr.Button("Load / Rescan", variant="primary", size="lg")
                reset_btn = gr.Button("Reset DB")
                gr.Markdown(
                    "**How to use:**\n"
                    "1. Click on a **folder** (📁) in the explorer\n"
                    "2. The path will appear above\n"
                    "3. Click 'Load / Rescan'"
                )
        
        status_md = gr.Markdown()

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
        
        gr.Markdown("## 🏆 Top 3 Rankings")
        with gr.Row():
            top1_col = gr.Column(scale=1)
            with top1_col:
                top1_rank = gr.Markdown("### 🥇 #1")
                top1_img = gr.Image(type="pil", label="", show_label=False, height=200)
                top1_info = gr.Markdown("")
            
            top2_col = gr.Column(scale=1)
            with top2_col:
                top2_rank = gr.Markdown("### 🥈 #2")
                top2_img = gr.Image(type="pil", label="", show_label=False, height=200)
                top2_info = gr.Markdown("")
            
            top3_col = gr.Column(scale=1)
            with top3_col:
                top3_rank = gr.Markdown("### 🥉 #3")
                top3_img = gr.Image(type="pil", label="", show_label=False, height=200)
                top3_info = gr.Markdown("")

        # Helper to extract folder path
        def update_selected_folder(file_path):
            """Update the selected folder textbox."""
            if not file_path:
                return ""
            if isinstance(file_path, list):
                if not file_path:
                    return ""
                file_path = file_path[0]
            
            path = Path(file_path)
            # If it's a file, get its parent directory
            if path.is_file():
                return str(path.parent)
            # If it's a directory, use it
            elif path.is_dir():
                return str(path)
            return str(file_path)
        
        # Update selected folder when clicking in FileExplorer
        folder_picker.change(
            update_selected_folder,
            inputs=[folder_picker],
            outputs=[selected_folder],
        )

        # Event handlers
        load_btn.click(
            load_folder_and_first_pair,
            inputs=[selected_folder],
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
                top1_img,
                top1_info,
                top2_img,
                top2_info,
                top3_img,
                top3_info,
            ],
        )

        reset_btn.click(
            reset_db,
            inputs=[selected_folder],
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
                top1_img,
                top1_info,
                top2_img,
                top2_info,
                top3_img,
                top3_info,
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
                top1_img,
                top1_info,
                top2_img,
                top2_info,
                top3_img,
                top3_info,
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
                top1_img,
                top1_info,
                top2_img,
                top2_info,
                top3_img,
                top3_info,
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
                top1_img,
                top1_info,
                top2_img,
                top2_info,
                top3_img,
                top3_info,
            ],
        )

    return demo
