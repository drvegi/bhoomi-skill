#!/usr/bin/env python3
"""Compile the board pack and compute the verdict from the panel's JSON summaries.

Verdict is computed, not written:
  Incomplete      a required summary is missing
  Don't proceed   an open legal blocker with no mitigation, an unmitigated
                  high-likelihood/high-impact risk, a lead offer more than
                  10% below break-even, or a non-positive residual land value
  Proceed if      anything that needs a condition (listed as a checklist)
  Proceed         nothing above applies

  python3 verdict.py --dir bhoomi [--skip buyers]
"""
import argparse
import json
import os
import sys

REQUIRED = ["valuer", "cfo", "legal", "buyers", "redteam"]
SECTION_TITLES = {"valuer": "Valuer", "cfo": "CFO", "legal": "Legal & regulatory",
                  "buyers": "Buyer panel", "redteam": "Red team"}


def load(d, name):
    p = os.path.join(d, f"{name}.json")
    if not os.path.exists(p):
        return None
    with open(p) as f:
        return json.load(f)


def decide(s, skip=()):
    missing = [n for n in REQUIRED if n not in skip and s.get(n) is None]
    if missing:
        return "Incomplete", [f"missing summary: bhoomi/{m}.json" for m in missing], []
    stop, cond = [], []
    v, c, l, b, r = (s.get(k) or {} for k in REQUIRED)

    if v.get("residual_pv_per_gross_acre") is not None and v["residual_pv_per_gross_acre"] <= 0:
        stop.append("residual land value is zero or negative at current assumptions")
    offers = v.get("offers") or []
    if offers:
        lead = offers[0]
        vb = lead.get("vs_break_even_pct")
        if vb is not None and vb < -10:
            stop.append(f"lead offer ({lead['party']}) is {vb:.1f}% below break-even")
        elif vb is not None and vb < 0:
            cond.append(f"lead offer ({lead['party']}) is {vb:.1f}% below break-even: renegotiate price or accept the loss knowingly")

    for blk in l.get("blockers", []):
        if blk.get("status") != "resolved":
            if blk.get("mitigation"):
                cond.append(f"legal: {blk['item']} — {blk['mitigation']}")
            else:
                stop.append(f"open legal blocker with no mitigation: {blk['item']}")
    cond += [f"legal: {x}" for x in l.get("conditions", [])]

    for k in r.get("kill_risks", []):
        if k.get("mitigated"):
            continue
        hi = k.get("likelihood") == "high" and k.get("impact") == "high"
        if hi and not k.get("mitigation"):
            stop.append(f"unmitigated kill risk: {k['risk']}")
        elif k.get("impact") in ("high", "medium"):
            cond.append(f"risk: {k['risk']}" + (f" — {k['mitigation']}" if k.get("mitigation") else ""))

    if c and c.get("payouts_covered_without_funding") is False:
        cond.append(f"funding: arrange about ₹{c['peak_funding_need_inr'] / 1e7:,.2f} Cr by month {c['peak_funding_month']}")
    if c and c.get("npv_inr") is not None and c["npv_inr"] < 0:
        cond.append("CFO: project NPV is negative at the chosen discount rate")

    if "buyers" not in skip and b:
        if b.get("interest_rate_pct", 0) < 30:
            cond.append(f"market: weighted simulated interest only {b['interest_rate_pct']:.0f}% — test with real buyers before committing")
        else:
            cond.append("market: confirm simulated buyer interest with at least three real buyers")

    signoffs = l.get("sign_offs", [])
    if stop:
        return "Don't proceed", stop, cond + [f"sign-off: {x}" for x in signoffs]
    if cond or signoffs:
        return "Proceed if", [], cond + [f"sign-off: {x}" for x in signoffs]
    return "Proceed", [], []


def compile_pack(d, verdict, reasons, conds, skip):
    deal = ""
    dp = os.path.join(d, "deal.md")
    if os.path.exists(dp):
        first = open(dp).readline().strip("# \n")
        deal = first
    L = [f"# Board pack: {deal or 'deal'}", "", f"## Verdict: **{verdict}**", ""]
    if reasons:
        L += ["### Why", ""] + [f"- {x}" for x in reasons] + [""]
    if conds:
        L += ["### Conditions to clear", ""] + [f"- [ ] {x}" for x in conds] + [""]
    chair = os.path.join(d, "chair.md")
    if os.path.exists(chair):
        L += [open(chair).read().strip(), ""]
    for n in REQUIRED:
        if n in skip:
            continue
        p = os.path.join(d, f"{n}.md")
        calc = os.path.join(d, f"{n}-calc.md")
        L += ["---", "", f"## {SECTION_TITLES[n]}", ""]
        if os.path.exists(p):
            L += [open(p).read().strip(), ""]
        elif os.path.exists(calc):
            L += [f"_Narrative bhoomi/{n}.md not written yet; calculator output follows._", "",
                  open(calc).read().strip(), ""]
        else:
            L += [f"_bhoomi/{n}.md not written yet._", ""]
    L += ["---", "",
          "_Simulated advisers apply published methods; they are not the firms they draw on. "
          "Not financial, legal or tax advice. A qualified chartered accountant and advocate must confirm "
          "every item marked sign-off before money moves._", ""]
    return "\n".join(L)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--dir", default="bhoomi")
    p.add_argument("--skip", default="", help="comma-separated sections to skip, e.g. buyers")
    p.add_argument("--out", help="default: <dir>/board-pack.md")
    a = p.parse_args(argv)
    skip = tuple(x for x in a.skip.split(",") if x)
    s = {n: load(a.dir, n) for n in REQUIRED}
    verdict, reasons, conds = decide(s, skip)
    out = a.out or os.path.join(a.dir, "board-pack.md")
    with open(out, "w") as f:
        f.write(compile_pack(a.dir, verdict, reasons, conds, skip))
    with open(os.path.join(a.dir, "verdict.json"), "w") as f:
        json.dump({"verdict": verdict, "reasons": reasons, "conditions": conds}, f, indent=2)
    print(f"Verdict: {verdict}")
    for x in reasons:
        print(f"  why: {x}")
    for x in conds:
        print(f"  if:  {x}")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
