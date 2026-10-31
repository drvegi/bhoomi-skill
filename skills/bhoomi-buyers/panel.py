#!/usr/bin/env python3
"""Buyer/investor panel: deal persona cards, write one brief per buyer, check and tally answers.

The tool never answers for a buyer. Sub-agents read the briefs and write answers.
Same seed, same cards. Standard library only.

  python3 panel.py init  --dir bhoomi/buyers --n 30 --seed 7 [--only id1,id2]
  python3 panel.py check --dir bhoomi/buyers
  python3 panel.py tally --dir bhoomi/buyers --out bhoomi/buyers.md --json bhoomi/buyers.json
"""
import argparse
import glob
import json
import os
import random
import statistics
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
INTEREST = {"yes", "maybe", "no"}
STRUCTURES = {"outright", "lease", "jda", "stake", "structured debt", "forward purchase", "other"}


def load_archetypes(only=None):
    with open(os.path.join(HERE, "archetypes.json")) as f:
        arch = json.load(f)["archetypes"]
    if only:
        ids = set(only)
        unknown = ids - {a["id"] for a in arch}
        if unknown:
            raise SystemExit(f"error: unknown archetype id(s): {', '.join(sorted(unknown))}")
        arch = [a for a in arch if a["id"] in ids]
    return arch


def deal_cards(n, seed, only=None):
    rng = random.Random(seed)
    arch = load_archetypes(only)
    weights = [a["weight"] for a in arch]
    cards = []
    for i in range(1, n + 1):
        a = rng.choices(arch, weights=weights)[0]
        lo, hi = a["acres"]
        cards.append({
            "buyer": f"buyer-{i:02d}",
            "archetype": a["id"],
            "label": a["label"],
            "reference_points": a["reference_points"],
            "acres_needed": round(rng.uniform(lo, hi), 2),
            "urgency": rng.choice(["low", "medium", "high"]),
            "financing": rng.choice(["own equity", "bank debt", "equity plus debt", "fund capital"]),
            "decision_maker": rng.choice(["promoter decides alone", "board approval needed", "investment committee", "family council"]),
            "main_worry": rng.choice(a["objections"]),
            "priorities": a["priorities"],
            "structures_considered": a["structures"],
            "price_posture": a["price_posture"],
            "horizon": a["horizon"],
        })
    return cards


BRIEF = """# Buyer brief: {buyer}

You are one prospective buyer or investor looking at a land deal in India.
You are **not** a real company. You behave the way a {label} typically
behaves (reference points: {reference_points}). Never claim to be or speak for
those firms.

## Who you are
- Type: {label}
- Land you need: about {acres_needed} acres
- Urgency: {urgency}
- Financing: {financing}
- Decision: {decision_maker}
- Horizon: {horizon}
- What you care about: {priorities}
- Your main worry going in: {main_worry}
- Structures you would consider: {structures}
- How you think about price: {price_posture}

## What to read
1. `bhoomi/deal.md` (the facts)
2. `bhoomi/pitch.md` if it exists (the offer as the seller would present it)

## Rules
- Answer as this buyer would in a real negotiation: self-interested, sceptical,
  specific. Language models lean agreeable; push against that. If the deal does
  not fit you, say **no**.
- Prices in INR per acre. Use null if you would not name a price.
- Do not invent facts about the deal. If something you need is missing, list it
  in `conditions`.

## Write your answer
Write exactly this JSON to `bhoomi/buyers/answers/{buyer}.json`:

```json
{{
  "buyer": "{buyer}",
  "interest": "yes | maybe | no",
  "acres_wanted": 0,
  "price_per_acre_inr": null,
  "walk_away_per_acre_inr": null,
  "preferred_structure": "outright | lease | jda | stake | structured debt | forward purchase | other",
  "conditions": ["short phrase", "short phrase"],
  "top_objection": "short phrase, 3-8 words",
  "what_flips_a_no": "one sentence"
}}
```
"""


def cmd_init(a):
    only = a.only.split(",") if a.only else None
    cards = deal_cards(a.n, a.seed, only)
    os.makedirs(os.path.join(a.dir, "briefs"), exist_ok=True)
    os.makedirs(os.path.join(a.dir, "answers"), exist_ok=True)
    with open(os.path.join(a.dir, "cards.json"), "w") as f:
        json.dump({"seed": a.seed, "n": a.n, "cards": cards}, f, indent=2)
    for c in cards:
        fields = dict(c, priorities="; ".join(c["priorities"]),
                      structures=", ".join(c["structures_considered"]))
        txt = BRIEF.format(**fields)
        with open(os.path.join(a.dir, "briefs", f"{c['buyer']}.md"), "w") as f:
            f.write(txt)
    mix = Counter(c["archetype"] for c in cards)
    print(f"dealt {len(cards)} cards (seed {a.seed}) into {a.dir}/briefs")
    for k, v in mix.most_common():
        print(f"  {v:3d}  {k}")
    return 0


def validate_answer(ans, name):
    errs = []
    for k in ("buyer", "interest", "acres_wanted", "price_per_acre_inr", "walk_away_per_acre_inr",
              "preferred_structure", "conditions", "top_objection", "what_flips_a_no"):
        if k not in ans:
            errs.append(f"{name}: missing '{k}'")
    if ans.get("interest") not in INTEREST:
        errs.append(f"{name}: interest must be yes, maybe or no")
    if ans.get("preferred_structure") not in STRUCTURES:
        errs.append(f"{name}: preferred_structure must be one of {sorted(STRUCTURES)}")
    for k in ("price_per_acre_inr", "walk_away_per_acre_inr"):
        v = ans.get(k)
        if v is not None and not isinstance(v, (int, float)):
            errs.append(f"{name}: {k} must be a number or null")
    if not isinstance(ans.get("conditions", []), list):
        errs.append(f"{name}: conditions must be a list")
    return errs


def read_answers(d):
    cards = {c["buyer"]: c for c in json.load(open(os.path.join(d, "cards.json")))["cards"]}
    answers, errs = {}, []
    for path in sorted(glob.glob(os.path.join(d, "answers", "*.json"))):
        name = os.path.basename(path)
        try:
            ans = json.load(open(path))
        except json.JSONDecodeError as e:
            errs.append(f"{name}: not valid JSON ({e})")
            continue
        errs += validate_answer(ans, name)
        answers[ans.get("buyer", name[:-5])] = ans
    missing = sorted(set(cards) - set(answers))
    return cards, answers, errs, missing


def cmd_check(a):
    cards, answers, errs, missing = read_answers(a.dir)
    for e in errs:
        print(e)
    if missing:
        print(f"missing answers: {', '.join(missing)}")
    print(f"{len(answers)}/{len(cards)} answers, {len(errs)} problems")
    return 1 if errs or missing else 0


def pct(vals, q):
    vals = sorted(vals)
    if not vals:
        return None
    k = (len(vals) - 1) * q
    f = int(k)
    c = min(f + 1, len(vals) - 1)
    return vals[f] + (vals[c] - vals[f]) * (k - f)


def cmd_tally(a):
    cards, answers, errs, missing = read_answers(a.dir)
    if errs:
        for e in errs:
            print(e)
        print("fix the answers above before tallying", file=sys.stderr)
        return 1
    n = len(answers)
    interest = Counter(x["interest"] for x in answers.values())
    by_arch = defaultdict(Counter)
    for b, x in answers.items():
        by_arch[cards[b]["archetype"] if b in cards else "unknown"][x["interest"]] += 1
    priced = [x["price_per_acre_inr"] for x in answers.values()
              if x["interest"] in ("yes", "maybe") and x["price_per_acre_inr"]]
    walk = [x["walk_away_per_acre_inr"] for x in answers.values()
            if x["interest"] in ("yes", "maybe") and x["walk_away_per_acre_inr"]]
    acres_yes = sum(x["acres_wanted"] or 0 for x in answers.values() if x["interest"] == "yes")
    acres_maybe = sum(x["acres_wanted"] or 0 for x in answers.values() if x["interest"] == "maybe")
    structures = Counter(x["preferred_structure"] for x in answers.values() if x["interest"] != "no")
    objections = Counter(x["top_objection"].strip().lower() for x in answers.values())
    conditions = Counter(c.strip().lower() for x in answers.values() for c in x["conditions"])
    flips = [x["what_flips_a_no"] for x in answers.values() if x["interest"] == "no"]
    summary = {
        "answers": n, "missing": missing,
        "interest": dict(interest),
        "interest_rate_pct": 100 * (interest["yes"] + 0.5 * interest["maybe"]) / n if n else 0,
        "acres_wanted_yes": acres_yes, "acres_wanted_maybe": acres_maybe,
        "price_per_acre_p25": pct(priced, .25), "price_per_acre_median": pct(priced, .5),
        "price_per_acre_p75": pct(priced, .75),
        "walk_away_median": statistics.median(walk) if walk else None,
        "structures": dict(structures),
        "top_objections": objections.most_common(8),
        "top_conditions": conditions.most_common(8),
    }

    def cr(x):
        return "n/a" if x is None else f"₹{x / 1e7:,.2f} Cr"
    L = ["# Buyer panel tally", "",
         f"{n} simulated buyers answered ({len(missing)} missing). Simulated buyers lean agreeable: "
         "read interest and prices as an **upper bound** and confirm with real buyers.", "",
         "| Measure | Value |", "|---|---|",
         f"| Yes / maybe / no | {interest['yes']} / {interest['maybe']} / {interest['no']} |",
         f"| Weighted interest | {summary['interest_rate_pct']:.0f}% |",
         f"| Acres wanted (yes / maybe) | {acres_yes:g} / {acres_maybe:g} |",
         f"| Price per acre, yes+maybe (P25 / median / P75) | {cr(summary['price_per_acre_p25'])} / {cr(summary['price_per_acre_median'])} / {cr(summary['price_per_acre_p75'])} |",
         f"| Median walk-away price | {cr(summary['walk_away_median'])} |", "",
         "## Interest by buyer type", "", "| Type | Yes | Maybe | No |", "|---|---|---|---|"]
    for k, c in sorted(by_arch.items()):
        L.append(f"| {k} | {c['yes']} | {c['maybe']} | {c['no']} |")
    L += ["", "## Preferred structures (yes + maybe)", ""]
    L += [f"- {k}: {v}" for k, v in structures.most_common()]
    L += ["", "## Top objections", ""] + [f"- {k} ({v})" for k, v in summary["top_objections"]]
    L += ["", "## Most common conditions", ""] + [f"- {k} ({v})" for k, v in summary["top_conditions"]]
    L += ["", "## What would flip a no", ""] + [f"- {t}" for t in flips[:12]]
    md = "\n".join(L) + "\n"
    if a.out:
        open(a.out, "w").write(md)
    else:
        print(md)
    if a.json:
        json.dump(summary, open(a.json, "w"), indent=2)
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    i = sub.add_parser("init")
    i.add_argument("--dir", default="bhoomi/buyers")
    i.add_argument("--n", type=int, default=30)
    i.add_argument("--seed", type=int, default=7)
    i.add_argument("--only", help="comma-separated archetype ids to restrict the panel")
    c = sub.add_parser("check")
    c.add_argument("--dir", default="bhoomi/buyers")
    t = sub.add_parser("tally")
    t.add_argument("--dir", default="bhoomi/buyers")
    t.add_argument("--out")
    t.add_argument("--json")
    a = p.parse_args(argv)
    return {"init": cmd_init, "check": cmd_check, "tally": cmd_tally}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
