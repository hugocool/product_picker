# Part 1: The Pendant Problem

*How a Valentine's Day shopping crisis led me down a Bayesian rabbit hole*

---

## The Setup

It's February 2nd. Valentine's Day is in 12 days. And I'm staring at my screen, completely overwhelmed.

My partner mentioned—once, briefly, months ago—that she'd love a nice pendant. Simple enough, right? Just find a pendant. How hard could that be?

Two hundred and thirty-seven. That's how many pendant options I've saved across various browser tabs, Pinterest boards, and screenshot folders. Delicate gold chains, statement pieces, minimalist geometric shapes, vintage-inspired cameos, modern sculptural designs. Each one beautiful in its own way. Each one *potentially* the perfect gift.

And I cannot, for the life of me, figure out which one to buy.

---

## The Rating Trap

My first instinct was obvious: rate everything on a 1-5 scale. Open a spreadsheet, go through each pendant, assign a score, sort by rating, done.

I got about 30 pendants in before I realized the problem.

"Is this a 4 or a 5?" I muttered, staring at a rose gold teardrop design. It was nice. Really nice. But was it *five-star* nice? What even is five-star nice? The geometric pendant I rated 5 earlier was completely different in style—how could they be the same score?

Rating things absolutely is *hard*. Our brains aren't calibrated for it. What felt like a 4 at 10am feels like a 3 by 2pm when you've seen fifty more options. The scale drifts. The mental fatigue sets in. By pendant #50, everything was getting 3s and 4s because my brain had given up making distinctions.

I needed a different approach.

---

## The Pairwise Insight

Here's something psychologists have known for decades: **humans are comparison machines**.[^1]

Ask someone "How good is this pendant on a scale of 1-5?" and watch them struggle. But ask "Which of these two pendants do you prefer?" and the answer is often instant.

Pairwise comparison is cognitively natural. We don't need to calibrate some internal scale. We don't need to hold abstract standards in our heads. We just look at two things and pick the one we like more.

> **Absolute vs. Relative Judgment**
>
> ❌ *"Rate this pendant 1-5"*
>
> - Requires calibrated internal scale
> - Scale drifts over time  
> - Cognitively exhausting
>
> ✅ *"Which pendant do you prefer, A or B?"*
>
> - Direct comparison
> - No calibration needed
> - Fast and intuitive

This is the insight behind everything from taste tests to Elo ratings in chess.[^2] Pairwise comparisons are cheap, fast, and surprisingly informative.

But there's a catch.

---

## The Combinatorial Explosion

With 237 pendants, there are:

$$\binom{237}{2} = \frac{237 \times 236}{2} = 27{,}966 \text{ possible pairs}$$

Twenty-eight *thousand* comparisons to evaluate every possible matchup. At 5 seconds per comparison, that's 39 hours of clicking. Valentine's Day would be long gone.

Obviously, I don't need to compare every pair. If pendant A beats B, and B beats C, I can probably assume A beats C (transitivity, mostly). But how do I pick which pairs to compare?

Random selection? That wastes comparisons on obvious matchups ("Do you prefer this gorgeous gold piece or this blob that you already rated poorly?").

Round-robin? Better, but still inefficient. Why keep comparing items I've already ranked confidently?

What I needed was an algorithm that could:

1. **Learn a ranking** from relatively few comparisons
2. **Pick informative pairs** to compare next
3. **Know when to stop** (or at least slow down)

---

## Enter the Algorithm

This is where my inner engineer took over. Surely someone has solved this problem before?

Spoiler: they have. Several someones, in fact.

The system I eventually built combines two powerful ideas from the world of competitive gaming and Bayesian statistics:

1. **TrueSkill**[^3] — Microsoft's rating system, originally built to match Xbox players. It models each item as having a "true skill" we're uncertain about, and updates our beliefs after each match.

2. **Active Learning**[^4] — A branch of machine learning about asking the *right* questions. Instead of random sampling, actively choose the most informative data points.

The result? An app that shows me two pendants, I click which one I prefer, and it learns. Fast.

![The Pendant Picker comparison interface](./screenshots/comparison_interface.png)
*Figure 1: The app presents two pendants side-by-side. Click the pendant you prefer, choose "Draw" if they're equal, or "Skip" to move on. The algorithm uses each choice to update its beliefs about all items.*

After just 47 comparisons—less than 0.2% of all possible pairs—the ranking had stabilized. My top 3 were clearly separated from the pack. I had my answer.

---

## Try It Yourself

This isn't just a pendant picker—you can use it to choose between *anything*. Vacation destinations, apartment listings, color schemes, restaurant menu items, baby names—if you have a folder of images representing your options, you can rank them.

**Getting started is simple:**

1. Clone the repository: `git clone https://github.com/hugoevers/product_picker`
2. Follow the README instructions to set up the environment
3. Launch the app and point it to a folder containing images of your options
4. Start comparing! The algorithm will guide you to discover your true preferences

The entire codebase is open source, including the TrueSkill implementation and the active learning pair selection algorithm we'll explore in Parts 2 and 3.

*Too lazy to set it up yourself? Ask your Claude or ChatGPT coding assistant to help—they can walk you through the setup in minutes.*

---

## What's Coming Up

In the next parts of this series, I'll dive into the beautiful mathematics that makes this work:

**[Part 2: TrueSkill Demystified](./part2-trueskill-demystified.md)**

- How Xbox's matchmaking algorithm reveals your true preferences
- What $\mu$ (mu) and $\sigma$ (sigma) really mean—belief and uncertainty
- Why "conservative score" prevents lucky first impressions from dominating

**[Part 3: The Pair Selection Puzzle](./part3-pair-selection-puzzle.md)**

- The explore vs. exploit dilemma
- $E[\Delta\sigma]$: Expected Uncertainty Reduction (the Bayesian way to pick pairs)
- Thompson Sampling: Let randomness guide you (wisely)
- The hybrid approach that makes it all work

But first, let me show you the core insight that makes TrueSkill so elegant: **every pendant has an appeal to you that you don't consciously know, and every comparison reveals something new about your preferences**.

---

## References

[^1]: Thurstone, L. L. (1927). "A law of comparative judgment." *Psychological Review*, 34(4), 273–286. The foundational paper on pairwise comparison and comparative judgment.

[^2]: Elo, A. E. (1978). *The Rating of Chessplayers, Past and Present*. Arco Publishing. The classic text introducing the Elo rating system.

[^3]: Herbrich, R., Minka, T., & Graepel, T. (2007). "TrueSkill™: A Bayesian Skill Rating System." *Advances in Neural Information Processing Systems*, 19. Microsoft Research's foundational paper on TrueSkill.

[^4]: Settles, B. (2009). "Active Learning Literature Survey." *Computer Sciences Technical Report 1648*, University of Wisconsin-Madison. Comprehensive overview of active learning methods.

---

*Next up: [Part 2 - TrueSkill Demystified](./part2-trueskill-demystified.md)*
