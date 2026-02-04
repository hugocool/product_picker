"""Pair selection and matching logic."""

import random
from typing import Dict, List, Optional, Tuple

from sqlmodel import Session, select

from product_picker.database import get_session
from product_picker.models import Match, Pendant


def _pair_ids(a: int, b: int) -> Tuple[int, int]:
    """Return canonical pair ordering (smaller id first)."""
    return (a, b) if a < b else (b, a)


def _pair_repeat_counts(
    session: Session, folder: str, candidate_ids: List[int]
) -> Dict[Tuple[int, int], int]:
    """Count how many times each pair has been compared."""
    cand = set(candidate_ids)
    counts: Dict[Tuple[int, int], int] = {}

    matches = session.exec(select(Match).where(Match.folder == folder)).all()
    for m in matches:
        if m.pair_a_id in cand or m.pair_b_id in cand:
            key = (m.pair_a_id, m.pair_b_id)
            counts[key] = counts.get(key, 0) + 1

    return counts


def choose_next_pair(folder: str, exclude_pair: Optional[Tuple[int, int]] = None) -> Optional[Tuple[int, int]]:
    """
    Select the next pair of pendants to compare using an information-maximizing heuristic.

    Strategy:
    1. Prioritize items with high uncertainty (sigma)
    2. Prefer matchups with closer mu (harder decisions)
    3. Penalize repeated comparisons

    Args:
        folder: Folder path
        exclude_pair: Optional pair (a, b) to exclude from selection (e.g., just skipped)

    Returns:
        Tuple of (left_id, right_id) or None if not enough pendants
    """
    # Normalize exclude_pair to canonical form
    if exclude_pair:
        exclude_pair = _pair_ids(exclude_pair[0], exclude_pair[1])
    
    with get_session(folder) as session:
        pendants = session.exec(select(Pendant).where(Pendant.folder == folder)).all()

    if len(pendants) < 2:
        return None

    # Sort by uncertainty (high sigma = needs more comparisons)
    pendants_sorted = sorted(pendants, key=lambda p: p.sigma, reverse=True)

    # Create candidate pools
    left_pool = pendants_sorted[: min(25, len(pendants_sorted))]
    right_pool = pendants_sorted[: min(80, len(pendants_sorted))]

    left_ids = [p.id for p in left_pool if p.id is not None]

    with get_session(folder) as session:
        counts = _pair_repeat_counts(session, folder, left_ids)

    # Find best pair using information heuristic
    best = None
    best_score = -1e18

    for left in left_pool:
        for right in right_pool:
            if left.id is None or right.id is None or left.id == right.id:
                continue

            a, b = _pair_ids(left.id, right.id)
            
            # Skip the excluded pair
            if exclude_pair and (a, b) == exclude_pair:
                continue
            
            repeat = counts.get((a, b), 0)

            # Information score: high when both have high sigma and close mu
            mu_gap = abs(left.mu - right.mu) + 1e-6
            info = (left.sigma + right.sigma) / mu_gap
            score = info - 0.75 * repeat  # Penalize repeats

            if score > best_score:
                best_score = score
                best = (left.id, right.id)

    if best is None:
        # Fallback: random pair
        ids = [p.id for p in pendants if p.id is not None]
        if len(ids) >= 2:
            a, b = random.sample(ids, 2)
            return (a, b)

    return best


def record_match(session: Session, folder: str, left_id: int, right_id: int, outcome: str) -> Match:
    """Record a match in the database."""
    pa, pb = _pair_ids(left_id, right_id)
    m = Match(
        folder=folder,
        shown_left_id=left_id,
        shown_right_id=right_id,
        pair_a_id=pa,
        pair_b_id=pb,
        outcome=outcome,
    )
    session.add(m)
    return m
