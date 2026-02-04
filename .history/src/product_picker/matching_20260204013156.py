"""Pair selection and matching logic.

Implements a hybrid EΔσ (Expected Uncertainty Reduction) + Thompson Sampling
approach for principled, efficient pair selection in pairwise ranking.

Key concepts:
- EΔσ: Compute expected reduction in uncertainty (σ) for each candidate pair
- Thompson Sampling: Sample from posteriors to naturally balance explore/exploit
- Match Quality: Use TrueSkill's quality_1vs1() for draw probability
- Cooldown: Prevent immediate repeats of skipped/drawn pairs
"""

import random
from math import sqrt, erf
from typing import Dict, List, Optional, Tuple

from sqlmodel import Session, select
from trueskill import Rating

from product_picker.database import get_session
from product_picker.models import Match, Pendant
from product_picker.rating import TS_ENV


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


def _cdf(x: float) -> float:
    """Standard normal CDF."""
    return 0.5 * (1.0 + erf(x / sqrt(2.0)))


def _expected_sigma_reduction(left: Pendant, right: Pendant) -> float:
    """
    Compute expected reduction in σ (uncertainty) for a single comparison.
    
    This is the principled Bayesian active learning objective: select pairs
    that maximize expected information gain (equivalently, minimize expected
    posterior uncertainty).
    
    The calculation:
    1. Estimate outcome probabilities: p(L wins), p(R wins), p(draw)
    2. For each outcome, do a hypothetical TrueSkill update
    3. Measure σ reduction under each outcome
    4. Take expectation: Σ p(y) × Δσ(y)
    
    Returns:
        Expected reduction in (σ_left + σ_right) from this comparison
    """
    rL = Rating(mu=left.mu, sigma=left.sigma)
    rR = Rating(mu=right.mu, sigma=right.sigma)
    
    # Approximate outcome probabilities using TrueSkill's generative model
    # Skills → Performances (with noise β) → Outcome
    delta_mu = rL.mu - rR.mu
    denom = sqrt(2 * (TS_ENV.beta ** 2) + rL.sigma ** 2 + rR.sigma ** 2)
    
    # Probability left wins (ignoring draws)
    p_left_nd = _cdf(delta_mu / denom)
    
    # Draw probability from TrueSkill's match quality
    # quality_1vs1 returns the probability of a draw given the skill difference
    p_draw = TS_ENV.quality_1vs1(rL, rR)
    
    # Split non-draw probability between left and right wins
    p_left = p_left_nd * (1.0 - p_draw)
    p_right = (1.0 - p_left_nd) * (1.0 - p_draw)
    
    # Hypothetical rating updates for each outcome
    # Left wins
    newL_w, newR_w = TS_ENV.rate_1vs1(rL, rR, drawn=False)
    # Right wins
    newR_l, newL_l = TS_ENV.rate_1vs1(rR, rL, drawn=False)
    # Draw
    newL_d, newR_d = TS_ENV.rate_1vs1(rL, rR, drawn=True)
    
    # Current total uncertainty
    sigma_sum = left.sigma + right.sigma
    
    # Uncertainty reduction under each outcome
    delta_w = sigma_sum - (newL_w.sigma + newR_w.sigma)  # Left wins
    delta_l = sigma_sum - (newL_l.sigma + newR_l.sigma)  # Right wins
    delta_d = sigma_sum - (newL_d.sigma + newR_d.sigma)  # Draw
    
    # Expected uncertainty reduction
    return p_left * delta_w + p_right * delta_l + p_draw * delta_d


def choose_next_pair(
    folder: str,
    policy: str = "hybrid",
    ts_prob: float = 0.25,
) -> Optional[Tuple[int, int]]:
    """
    Select the next pendant pair using hybrid EΔσ + Thompson Sampling.
    
    **Algorithm Overview**:
    
    1. **EΔσ (Expected Uncertainty Reduction)**: For each candidate pair, compute
       the expected reduction in total uncertainty (σ) after the comparison.
       This is the gold-standard Bayesian active learning objective.
       
    2. **Thompson Sampling**: With probability `ts_prob`, sample skills from
       each pendant's posterior and consider adjacent pairs in the sampled order.
       This naturally surfaces uncertain items and prevents greedy loops.
    
    **Why Hybrid?**
    - Pure EΔσ can get stuck refining the same near-ties
    - Pure Thompson is optimized for "find the best" not "full ranking"
    - Hybrid ensures variety while prioritizing informative comparisons
    
    **TrueSkill Integration**:
    - Uses quality_1vs1() for draw probability estimation
    - Uses rate_1vs1() for hypothetical updates
    - Respects the Bayesian generative model (skills → performances → outcomes)
    
    Args:
        folder: Folder path containing pendants
        policy: "hybrid" (default), "edelta", or "thompson"
        ts_prob: Probability of taking a Thompson sampling step (default 0.25)
    
    Returns:
        Tuple of (left_id, right_id) or None if < 2 pendants
    """
    with get_session(folder) as session:
        pendants = session.exec(select(Pendant).where(Pendant.folder == folder)).all()
    
    if len(pendants) < 2:
        return None
    
    # Build lookup dict for fast access
    pendant_by_id: Dict[int, Pendant] = {p.id: p for p in pendants if p.id is not None}
    
    # Sort pendants by uncertainty (high σ first)
    pendants_sorted = sorted(pendants, key=lambda p: p.sigma, reverse=True)
    
    # Get repeat counts and recent skip/draw pairs
    all_ids = [p.id for p in pendants if p.id is not None]
    with get_session(folder) as session:
        counts = _pair_repeat_counts(session, folder, all_ids)
        recent_skip_draw = _get_recent_skips_and_draws(session, folder, last_n=2)
    
    # Generate candidate pairs based on policy
    if policy == "thompson" or (policy == "hybrid" and random.random() < ts_prob):
        # Thompson Sampling: sample skill from posterior for each pendant
        # High-σ items fluctuate more, naturally surfacing uncertain items
        samples = {p.id: random.gauss(p.mu, p.sigma) for p in pendants if p.id is not None}
        sorted_ids = sorted(samples.keys(), key=lambda x: samples[x], reverse=True)
        
        # Consider adjacent pairs in sampled order (close in sampled skill)
        candidate_pairs = [
            _pair_ids(sorted_ids[i], sorted_ids[i + 1])
            for i in range(len(sorted_ids) - 1)
        ]
    else:
        # EΔσ: evaluate pairs among high-uncertainty pendants
        max_left = min(50, len(pendants_sorted))
        max_right = min(150, len(pendants_sorted))
        candidate_pairs = []
        for i in range(max_left):
            for j in range(i + 1, max_right):
                a_id = pendants_sorted[i].id
                b_id = pendants_sorted[j].id
                if a_id is not None and b_id is not None:
                    candidate_pairs.append(_pair_ids(a_id, b_id))
    
    # Score each candidate pair
    best_pair: Optional[Tuple[int, int]] = None
    best_score = float("-inf")
    
    for a, b in candidate_pairs:
        # Skip recently skipped/drawn pairs (cooldown)
        if (a, b) in recent_skip_draw:
            continue
        
        # Retrieve pendant objects
        left = pendant_by_id.get(a)
        right = pendant_by_id.get(b)
        if left is None or right is None:
            continue
        
        # Compute expected uncertainty reduction (EΔσ)
        delta_sigma = _expected_sigma_reduction(left, right)
        
        # Light penalty for repeated comparisons to encourage coverage
        repeat_penalty = counts.get((a, b), 0)
        score = delta_sigma - 0.5 * repeat_penalty
        
        if score > best_score:
            best_score = score
            best_pair = (a, b)
    
    # Fallback: random pair if nothing viable
    if best_pair is None:
        ids = list(pendant_by_id.keys())
        if len(ids) >= 2:
            a, b = random.sample(ids, 2)
            best_pair = _pair_ids(a, b)
    
    return best_pair


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
