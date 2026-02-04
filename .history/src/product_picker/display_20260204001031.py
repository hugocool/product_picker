"""Data display utilities - leaderboards and match history."""

from typing import Optional

import pandas as pd
from sqlmodel import select

from product_picker.database import get_session
from product_picker.models import Match, Pendant
from product_picker.rating import conservative_score


def get_leaderboard(folder: str, limit: int = 50) -> pd.DataFrame:
    """
    Generate leaderboard DataFrame sorted by conservative score.
    
    Args:
        folder: Folder path
        limit: Maximum number of rows to return
        
    Returns:
        DataFrame with columns: rank, id, file, score(mu-3σ), mu, sigma, games, W, L, D
    """
    with get_session(folder) as session:
        rows = session.exec(select(Pendant).where(Pendant.folder == folder)).all()
    
    data = []
    for p in rows:
        data.append(
            {
                "id": p.id,
                "file": p.rel_path,
                "score(mu-3σ)": round(conservative_score(p.mu, p.sigma), 3),
                "mu": round(p.mu, 3),
                "sigma": round(p.sigma, 3),
                "games": p.games,
                "W": p.wins,
                "L": p.losses,
                "D": p.draws,
            }
        )
    
    df = pd.DataFrame(data)
    if df.empty:
        return df
    
    df = df.sort_values(by="score(mu-3σ)", ascending=False).reset_index(drop=True)
    df.insert(0, "rank", range(1, len(df) + 1))
    return df.head(limit)


def get_match_history(folder: str, limit: int = 25) -> pd.DataFrame:
    """
    Generate match history DataFrame.
    
    Args:
        folder: Folder path
        limit: Maximum number of matches to return
        
    Returns:
        DataFrame with columns: t_utc, left, right, winner
    """
    with get_session(folder) as session:
        matches = session.exec(
            select(Match)
            .where(Match.folder == folder)
            .order_by(Match.id.desc())
            .limit(limit)
        ).all()
        
        # Map IDs to names for display
        ids = set()
        for m in matches:
            ids.add(m.shown_left_id)
            ids.add(m.shown_right_id)
        
        pendants = session.exec(select(Pendant).where(Pendant.folder == folder)).all()
        name_map = {p.id: p.rel_path for p in pendants if p.id in ids}
    
    data = []
    for m in matches:
        if m.outcome == "L":
            winner = "LEFT"
        elif m.outcome == "R":
            winner = "RIGHT"
        elif m.outcome == "D":
            winner = "DRAW"
        else:
            winner = "SKIP"
        
        data.append(
            {
                "t_utc": m.created_at_utc,
                "left": name_map.get(m.shown_left_id, f"id={m.shown_left_id}"),
                "right": name_map.get(m.shown_right_id, f"id={m.shown_right_id}"),
                "winner": winner,
            }
        )
    
    return pd.DataFrame(data)


def get_pendant_by_id(folder: str, pendant_id: Optional[int]) -> Optional[Pendant]:
    """Get a pendant by ID."""
    if pendant_id is None:
        return None
    
    with get_session(folder) as session:
        pendant = session.exec(
            select(Pendant).where(Pendant.folder == folder, Pendant.id == pendant_id)
        ).first()
    
    return pendant
