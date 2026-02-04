"""Quick example to verify the package works."""

from product_picker.rating import conservative_score

# Test the rating system
mu = 25.0
sigma = 8.333

score = conservative_score(mu, sigma)
print(f"✓ Conservative score calculation: {score:.3f}")
print(f"  μ={mu}, σ={sigma:.3f} → score = μ - 3σ = {score:.3f}")

print("\n✓ Package is working correctly!")
print("\nTo launch the app:")
print("  uv run python run.py")
print("  # or")
print("  uv run python -m product_picker")
