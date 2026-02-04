# Pair Selection Algorithm - Hybrid EΔσ + Thompson Sampling

## Overview

This app uses a principled **hybrid approach** combining:

1. **EΔσ (Expected Uncertainty Reduction)**: The gold-standard Bayesian active learning objective
2. **Thompson Sampling**: Natural explore/exploit balance via posterior sampling

This replaces the previous ad-hoc heuristic with TrueSkill-native calculations.

---

## Why Hybrid?

| Pure EΔσ | Pure Thompson | Hybrid |
|----------|---------------|--------|
| Can get stuck on near-ties | Optimized for "find best" | Best of both worlds |
| Deterministic → loops | Random → variety | Controlled randomness |
| Full ranking focus | Top-K focus | Adapts to both |

---

## The EΔσ Calculation

For each candidate pair (i, j), we compute the **expected reduction in total uncertainty**:

```
EΔσ(i,j) = Σ p(y) × [Δσ under outcome y]
         = p(L wins) × Δσ_L + p(R wins) × Δσ_R + p(draw) × Δσ_D
```

### Step 1: Estimate Outcome Probabilities

Using TrueSkill's generative model (skills → performances → outcomes):

```python
# Probability left wins (ignoring draws)
delta_mu = μ_left - μ_right
denom = √(2β² + σ_left² + σ_right²)
p_left_nd = Φ(delta_mu / denom)  # Normal CDF

# Draw probability from TrueSkill match quality
p_draw = quality_1vs1(rating_left, rating_right)

# Split non-draw probability
p_left = p_left_nd × (1 - p_draw)
p_right = (1 - p_left_nd) × (1 - p_draw)
```

### Step 2: Hypothetical Updates

For each possible outcome, do a hypothetical `rate_1vs1()` call:

```python
# Left wins
newL_w, newR_w = rate_1vs1(rL, rR, drawn=False)

# Right wins  
newR_l, newL_l = rate_1vs1(rR, rL, drawn=False)

# Draw
newL_d, newR_d = rate_1vs1(rL, rR, drawn=True)
```

### Step 3: Compute Expected Reduction

```python
sigma_sum = σ_left + σ_right
delta_w = sigma_sum - (newL_w.σ + newR_w.σ)
delta_l = sigma_sum - (newL_l.σ + newR_l.σ)
delta_d = sigma_sum - (newL_d.σ + newR_d.σ)

EΔσ = p_left × delta_w + p_right × delta_l + p_draw × delta_d
```

### Why This Works

- **High-σ items**: Large potential shrinkage → high EΔσ
- **Close matches**: Uncertain outcomes → balanced shrinkage across outcomes
- **Well-measured items**: Small σ → small EΔσ (stops obsessing over them!)
- **Lopsided matches**: One outcome dominates → less shrinkage on average

---

## Thompson Sampling Integration

With probability `ts_prob` (default 25%), we use Thompson Sampling instead of pure EΔσ:

```python
# Sample skill from posterior for each pendant
samples = {p.id: gauss(p.mu, p.sigma) for p in pendants}

# Sort by sampled skill
sorted_ids = sorted(samples.keys(), key=samples.get, reverse=True)

# Consider adjacent pairs (close in sampled skill)
candidate_pairs = [(sorted_ids[i], sorted_ids[i+1]) for i in range(len-1)]
```

### Why Thompson Works

- **High-σ items** fluctuate wildly → frequently surface in top positions
- **Low-σ items** stay stable → only appear when truly competitive
- **Adjacent pairs** are informative (close sampled skills = uncertain outcome)

Then we still score these candidates by EΔσ to pick the most informative one.

---

## TrueSkill Integration

| TrueSkill Feature | How We Use It |
|-------------------|---------------|
| `quality_1vs1()` | Draw probability for outcome estimation |
| `rate_1vs1()` | Hypothetical updates for EΔσ calculation |
| `σ (sigma)` | Drives exploration naturally |
| `β (beta)` | Performance noise in outcome probability |
| `draw_probability` | Affects posterior updates |

---

## Cooldown & Repeat Handling

- **Last 2 skip/draw pairs**: Hard excluded (immediate cooldown)
- **Repeat penalty**: `score = EΔσ - 0.5 × repeat_count`
- **Pairs can return**: When their EΔσ rises above alternatives

---

## Parameters

| Parameter | Default | Effect |
|-----------|---------|--------|
| `policy` | "hybrid" | "hybrid", "edelta", or "thompson" |
| `ts_prob` | 0.25 | Probability of Thompson step in hybrid mode |
| `repeat_penalty` | 0.5 | Discount per previous comparison |
| `cooldown` | 2 | Number of recent matches to exclude skip/draw pairs |

---

## Comparison with Previous Heuristic

| Old Approach | New Approach |
|--------------|--------------|
| `(σ₁+σ₂)/μ_gap` | `EΔσ = expected shrinkage` |
| Hardcoded +100/+50 bonuses | Natural from σ in calculation |
| Phase threshold `avg_games < 5` | Continuous adaptation |
| No match quality | Uses `quality_1vs1()` |
| Deterministic greedy | 25% Thompson sampling |

---

## Summary

The hybrid EΔσ + Thompson Sampling approach:

1. **Principled**: Uses actual TrueSkill quantities, not ad-hoc formulas
2. **Self-balancing**: EΔσ naturally stops when uncertainty is low
3. **Diverse**: Thompson sampling prevents greedy loops
4. **Efficient**: Maximizes information gain per comparison
5. **Robust**: Cooldown prevents immediate repeats
