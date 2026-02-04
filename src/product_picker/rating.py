"""TrueSkill rating system logic."""

import trueskill

from product_picker.models import Pendant


# TrueSkill environment configuration
# draw_probability=0.10 means 10% chance of draws in the model
TS_ENV = trueskill.TrueSkill(draw_probability=0.10)


def conservative_score(mu: float, sigma: float) -> float:
    """
    Calculate conservative score (mu - 3*sigma).

    This represents a 99.7% confidence lower bound on the true skill.
    Used to prevent barely-compared items from floating to the top.
    """
    return mu - 3.0 * sigma


def update_ratings(left: Pendant, right: Pendant, outcome: str) -> None:
    """
    Update TrueSkill ratings for two pendants based on match outcome.

    Args:
        left: Left pendant (modified in place)
        right: Right pendant (modified in place)
        outcome: "L" (left wins), "R" (right wins), or "D" (draw)
    """
    if outcome not in {"L", "R", "D"}:
        return

    rL = TS_ENV.Rating(mu=left.mu, sigma=left.sigma)
    rR = TS_ENV.Rating(mu=right.mu, sigma=right.sigma)

    if outcome == "L":
        newL, newR = TS_ENV.rate_1vs1(rL, rR, drawn=False)
        left.wins += 1
        right.losses += 1
    elif outcome == "R":
        newR, newL = TS_ENV.rate_1vs1(rR, rL, drawn=False)
        left.losses += 1
        right.wins += 1
    else:  # draw
        newL, newR = TS_ENV.rate_1vs1(rL, rR, drawn=True)
        left.draws += 1
        right.draws += 1

    left.mu, left.sigma = float(newL.mu), float(newL.sigma)
    right.mu, right.sigma = float(newR.mu), float(newR.sigma)
    left.games += 1
    right.games += 1
