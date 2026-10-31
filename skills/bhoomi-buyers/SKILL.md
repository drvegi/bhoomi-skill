---
name: bhoomi-buyers
description: Bhoomi Board buyer and investor panel. Deals 20-50 simulated Indian buyers (logistics park developers, township developers, regional developers, end users, funds, family offices, NRIs, local investors and more), runs one sub-agent per buyer against the deal, and tallies who buys, at what price, in which structure, and why not. Use to test demand, price and structure before going to real buyers.
---

# Bhoomi buyer panel

Simulated buyers, not customers. The panel finds objections, segments and
price bands quickly. It is not a forecast.

## Inputs

`bhoomi/deal.md` and `bhoomi/question.md`. If `bhoomi/pitch.md` does not
exist, write it first: a factual one-page offer as the seller would present
it, with nothing in it the seller cannot prove.

## Steps

1. **Deal the cards** (from the plugin's `skills/bhoomi-buyers/`):
   ```
   python3 panel.py init --dir bhoomi/buyers --n 30 --seed 7
   ```
   Use `--only id1,id2` to restrict to relevant archetypes (ids are in
   `archetypes.json`). Use `--n 12` for a quick read.
2. **Run one sub-agent per buyer**, using the `bhoomi-buyer` agent where the
   plugin is installed (otherwise a general sub-agent). Give each only its
   brief path: `bhoomi/buyers/briefs/buyer-NN.md`. Run them in parallel
   batches of about 10. Never answer for a buyer yourself.
3. **Check and tally:**
   ```
   python3 panel.py check --dir bhoomi/buyers
   python3 panel.py tally --dir bhoomi/buyers --out bhoomi/buyers.md --json bhoomi/buyers.json
   ```
   Re-run any buyer whose answer fails the check.
4. **Add an interpretation** at the top of `bhoomi/buyers.md` (keep the
   tool's tables below it): which buyer types are real prospects, the price
   band they support, the structure they want, the three objections to fix,
   and which real buyers to approach first.

## Without sub-agents (chat edition)

Role-play 8 contrasting archetypes one at a time, each answering the same
JSON fields, then summarise. Say clearly that the sample is small.

## Rules

- Language models lean agreeable. Treat interest and prices as an upper
  bound, and recommend testing with at least three real buyers.
- Panel answers are research. Never present them as real buyer quotes,
  testimonials or evidence of demand to third parties.
- Next step: `/bhoomi-redteam`.
