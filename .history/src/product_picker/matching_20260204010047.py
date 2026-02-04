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


def _get_recent_skips_and_draws(
    session: Session, folder: str, last_n: int = 1
) -> set[Tuple[int, int]]:
    """Get pairs that were skipped or drawn in the most recent match(es).
    
    We only look at the very last match to prevent immediate repeats,
    but allow the pair to come back later if it's highly informative.
    """
    recent_skip_draw = set()
    
    # Get the most recent match only
    matches = session.exec(
        select(Match)
        .where(Match.folder == folder)
        .order_by(Match.created_at_utc.desc())
        .limit(last_n)
    ).all()
    
    for m in matches:
        if m.outcome in {"S", "D"}:  # Skip or Draw
            recent_skip_draw.add((m.pair_a_id, m.pair_b_id))
    
    return recent_skip_draw


def choose_next_pair(
    folder: str, exclude_pair: Optional[Tuple[int, int]] = None
) -> Optional[Tuple[int, int]]:
    """
    Select the next pair of pendants to compare using an information-maximizing heuristic.
    
    **Algorithm Goal**: Find the true ranking (not just the winner) with minimum comparisons
    by maximizing information gain per comparison.
    
    **TrueSkill Information Theory**:
    - Each pendant has a skill distribution N(μ, σ²)
    - Comparisons update both μ (ranking) and σ (certainty)
    - High information pairs: high σ (uncertain items) + close μ (uncertain outcome)
    - This naturally handles transitivity: if A>B and B>C, TrueSkill updates all ratings
    
    **Exploration vs Exploitation**:
    1. **Exploration**: Prioritize high-σ items (uncertain rankings need more data)
    2. **Exploitation**: Prefer close-μ matchups (uncertain outcomes = max info gain)
    3. **Diversity**: Penalize repeated pairs to gather broad information
    4. **Cooldown**: Exclude just-skipped/drawn pairs to avoid immediate repeats
    
    **Randomness**: Minimal - the algorithm is deterministic given current ratings,
    only using randomness as a fallback if scoring fails.
    
    **Transitivity**: Fully considered - TrueSkill updates all ratings based on outcomes,
    so comparing A vs B affects how we view A vs C and B vs C (Bayesian inference).

    Args:
        folder: Folder path
        exclude_pair: Optional pair to exclude (deprecated, use recent skip tracking instead)

    Returns:
        Tuple of (left_id, right_id) or None if not enough pendants
    """
    with get_session(folder) as session:
        pendants = session.exec(select(Pendant).where(Pendant.folder == folder)).all()

    if len(pendants) < 2:
        return None

    # Sort by uncertainty (high sigma = needs more comparisons)
    pendants_sorted = sorted(pendants, key=lambda p: p.sigma, reverse=True)

    # Create candidate pools - include more items to explore transitivity
    left_pool = pendants_sorted[: min(40, len(pendants_sorted))]
    right_pool = pendants_sorted[: min(len(pendants_sorted), 120)]

    left_ids = [p.id for p in left_pool if p.id is not None]

    with get_session(folder) as session:
        counts = _pair_repeat_counts(session, folder, left_ids)
        recent_skip_draw = _get_recent_skips_and_draws(session, folder, last_n=1)
    
    # Calculate average games to determine exploration phase
    avg_games = sum(p.games for p in pendants) / len(pendants) if pendants else 0
    exploration_phase = avg_games < 5  # Early phase: prioritize coverage

    # Find best pair using information heuristic
    best = None
    best_score = -1e18

    for left in left_pool:
        for right in right_pool:
            if left.id is None or right.id is None or left.id == right.id:
                continue

            a, b = _pair_ids(left.id, right.id)

            # HARD EXCLUDE: Pairs from the most recent skip/draw
            # This prevents immediate repeats while still allowing them later
            if (a, b) in recent_skip_draw:
                continue

            # Also skip explicitly excluded pair if provided
            if exclude_pair and (a, b) == exclude_pair:
                continue

            repeat = counts.get((a, b), 0)
            
            # Exploration bonus: heavily favor items with few comparisons
            min_games = min(left.games, right.games)
            exploration_bonus = 0.0
            if min_games == 0:
                exploration_bonus = 100.0  # Uncompared items get huge boost
            elif min_games < 3:
                exploration_bonus = 50.0   # Rarely compared items get big boost
            elif min_games < 5:
                exploration_bonus = 20.0   # Less-compared items get moderate boost

            # Information score: balance exploration and exploitation
            # - High sigma = high uncertainty = more to learn (exploration)
            # - Close mu = uncertain outcome = maximum info gain (exploitation)
            mu_gap = abs(left.mu - right.mu) + 1e-6
            
            if exploration_phase:
                # Early phase: prioritize broad coverage and transitivity
                # Sigma matters more than close matchups
                info = (left.sigma + right.sigma) * 10.0 + exploration_bonus
            else:
                # Late phase: focus on resolving close races
                # Close matchups matter more
                info = (left.sigma + right.sigma) / mu_gap + exploration_bonus * 0.3
            
            # Soft penalty for historical repeats (allows re-matching if informative)
            score = info - 0.75 * repeat

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
