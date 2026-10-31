#!/usr/bin/env python3
"""Residual land value, break-even plot price and offer tests for a land deal.

Reads one numbers.json (see examples/coastal-park/bhoomi/numbers.json).
Every number in the report traces to an input. A missing required field is an
error, never a guess. Standard library only.

  python3 residual.py bhoomi/numbers.json --out bhoomi/valuer-calc.md --json bhoomi/valuer.json
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import units  # noqa: E402

REQUIRED = {
    "land": ["gross_acres", "saleable_acres"],
    "development": ["cost_inr", "months"],
    "sales": ["absorption_months", "start_month", "selling_cost_pct"],
    "finance": ["discount_rate_pct", "developer_margin_pct"],
}


class InputError(Exception):
    pass


def need(d, section, key):
    try:
        return d[section][key]
    except (KeyError, TypeError):
        raise InputError(f"missing required input: {section}.{key}")


def validate(d):
    for sec, keys in REQUIRED.items():
        for k in keys:
            need(d, sec, k)
    if not d.get("comparables"):
        raise InputError("missing required input: comparables (at least one)")
    if d["land"]["saleable_acres"] > d["land"]["gross_acres"]:
        raise InputError("land.saleable_acres cannot exceed land.gross_acres")


def comparable_price_per_acre(comps):
    """Weighted, adjusted comparable price in INR per saleable acre."""
    rows, tw, total = [], 0.0, 0.0
    for c in comps:
        for k in ("name", "price", "unit"):
            if k not in c:
                raise InputError(f"comparable missing '{k}': {c}")
        raw = units.price(c["price"], c["unit"], "inr/acre")
        adj = raw * (1 + c.get("adjust_pct", 0) / 100)
        w = c.get("weight", 1)
        rows.append({"name": c["name"], "raw_inr_acre": raw, "adjust_pct": c.get("adjust_pct", 0),
                     "adjusted_inr_acre": adj, "weight": w, "note": c.get("note", "")})
        tw += w
        total += adj * w
    return total / tw, rows


def monthly_rate(annual_pct):
    return (1 + annual_pct / 100) ** (1 / 12) - 1


def pv_even(amount, start, months, r):
    """PV of `amount` spread evenly over `months` starting in month `start` (1-based)."""
    if months <= 0:
        return amount / (1 + r) ** start
    per = amount / months
    return sum(per / (1 + r) ** (start + i) for i in range(months))


def residual(d, price_per_acre=None, cost_mult=1.0):
    L, D, S, F = d["land"], d["development"], d["sales"], d["finance"]
    p = price_per_acre if price_per_acre is not None else comparable_price_per_acre(d["comparables"])[0]
    r = monthly_rate(F["discount_rate_pct"])
    gdv = L["saleable_acres"] * p
    sell = gdv * S["selling_cost_pct"] / 100
    dev_net = D["cost_inr"] * cost_mult - D.get("subsidy_inr", 0)
    margin = gdv * F["developer_margin_pct"] / 100
    undiscounted = gdv - sell - dev_net - margin
    pv_rev = pv_even(gdv - sell, S["start_month"], S["absorption_months"], r)
    pv_cost = pv_even(dev_net, 1, D["months"], r)
    pv_margin = pv_rev * F["developer_margin_pct"] / 100
    discounted = pv_rev - pv_cost - pv_margin
    return {
        "plot_price_per_acre": p,
        "gdv": gdv,
        "selling_cost": sell,
        "dev_cost_net": dev_net,
        "developer_margin": margin,
        "residual_undiscounted": undiscounted,
        "residual_pv": discounted,
        "residual_pv_per_gross_acre": discounted / L["gross_acres"],
        "residual_undiscounted_per_gross_acre": undiscounted / L["gross_acres"],
        "yield_pct": 100 * L["saleable_acres"] / L["gross_acres"],
    }


def break_even(d, land_per_gross_acre):
    """Plot price per saleable acre that recovers land value + net development cost (no margin)."""
    L, D, S = d["land"], d["development"], d["sales"]
    dev_net = D["cost_inr"] - D.get("subsidy_inr", 0)
    need_inr = land_per_gross_acre * L["gross_acres"] + dev_net
    return need_inr / (L["saleable_acres"] * (1 - S["selling_cost_pct"] / 100))


def offer_tests(d, comp_price, be):
    out = []
    L, D, S = d["land"], d["development"], d["sales"]
    dev_net = D["cost_inr"] - D.get("subsidy_inr", 0)
    for o in d.get("offers", []):
        for k in ("party", "acres", "price_per_acre_inr"):
            if k not in o:
                raise InputError(f"offer missing '{k}': {o}")
        pr = o["price_per_acre_inr"]
        implied_land = (pr * L["saleable_acres"] * (1 - S["selling_cost_pct"] / 100) - dev_net) / L["gross_acres"]
        out.append({
            "party": o["party"], "acres": o["acres"], "price_per_acre": pr,
            "total": pr * o["acres"],
            "vs_comparable_pct": 100 * (pr / comp_price - 1),
            "vs_break_even_pct": (100 * (pr / be - 1)) if be else None,
            "implied_land_per_gross_acre": implied_land,
            "includes_infra": o.get("includes_infra"),
        })
    return out


def cr(x):
    return f"₹{x / 1e7:,.2f} Cr"


def build(d):
    validate(d)
    comp_price, comp_rows = comparable_price_per_acre(d["comparables"])
    base = residual(d)
    asking = d.get("land_value", {}).get("asking_per_gross_acre_inr")
    land_for_be = asking if asking else base["residual_undiscounted_per_gross_acre"]
    be = break_even(d, land_for_be)
    offers = offer_tests(d, comp_price, be)
    grid = []
    for pm in (-20, -10, 0, 10):
        row = []
        for cm in (-20, 0, 20):
            res = residual(d, comp_price * (1 + pm / 100), 1 + cm / 100)
            row.append(res["residual_pv_per_gross_acre"])
        grid.append((pm, row))
    summary = {
        "comparable_price_per_saleable_acre": comp_price,
        "yield_pct": base["yield_pct"],
        "gdv": base["gdv"],
        "residual_pv_per_gross_acre": base["residual_pv_per_gross_acre"],
        "residual_undiscounted_per_gross_acre": base["residual_undiscounted_per_gross_acre"],
        "break_even_basis": "asking land value" if asking else "undiscounted residual",
        "break_even_per_saleable_acre": be,
        "offers": offers,
    }
    return summary, comp_rows, base, grid


def report(d, summary, comp_rows, base, grid):
    L = d["land"]
    lines = [f"# Valuer calculations: {d.get('deal', 'deal')}", "",
             "Every figure below is computed from numbers.json. Estimates in the inputs stay estimates.", "",
             "## Comparables (converted to ₹ per saleable acre)", "",
             "| Comparable | Raw | Adjustment | Adjusted | Weight | Note |", "|---|---|---|---|---|---|"]
    for c in comp_rows:
        lines.append(f"| {c['name']} | {cr(c['raw_inr_acre'])} | {c['adjust_pct']:+g}% | {cr(c['adjusted_inr_acre'])} | {c['weight']} | {c['note']} |")
    lines += ["", f"**Weighted plot price:** {cr(summary['comparable_price_per_saleable_acre'])} per saleable acre "
              f"(₹{units.price(summary['comparable_price_per_saleable_acre'], 'inr/acre', 'inr/sqm'):,.0f}/sq m, "
              f"₹{units.price(summary['comparable_price_per_saleable_acre'], 'inr/acre', 'inr/sqyd'):,.0f}/sq yd)", "",
              "## Residual land value", "",
              "| Item | Amount |", "|---|---|",
              f"| Gross / saleable area | {L['gross_acres']:g} / {L['saleable_acres']:g} acres (yield {base['yield_pct']:.1f}%) |",
              f"| Gross development value | {cr(base['gdv'])} |",
              f"| Less selling cost | {cr(base['selling_cost'])} |",
              f"| Less development cost net of subsidy | {cr(base['dev_cost_net'])} |",
              f"| Less developer margin | {cr(base['developer_margin'])} |",
              f"| Residual, undiscounted | {cr(base['residual_undiscounted'])} ({cr(base['residual_undiscounted_per_gross_acre'])}/gross acre) |",
              f"| Residual, present value | {cr(base['residual_pv'])} ({cr(base['residual_pv_per_gross_acre'])}/gross acre) |",
              "", "## Break-even plot price", "",
              f"Land held at {summary['break_even_basis']}: **{cr(summary['break_even_per_saleable_acre'])} per saleable acre** "
              "(recovers land value and net development cost, no profit).", ""]
    if summary["offers"]:
        lines += ["## Offer tests", "", "| Party | Acres | ₹/acre | Total | vs comparable | vs break-even | Implied land value / gross acre |",
                  "|---|---|---|---|---|---|---|"]
        for o in summary["offers"]:
            vbe = f"{o['vs_break_even_pct']:+.1f}%" if o["vs_break_even_pct"] is not None else "n/a"
            lines.append(f"| {o['party']} | {o['acres']:g} | {cr(o['price_per_acre'])} | {cr(o['total'])} | "
                         f"{o['vs_comparable_pct']:+.1f}% | {vbe} | {cr(o['implied_land_per_gross_acre'])} |")
        lines.append("")
    lines += ["## Sensitivity: residual present value per gross acre", "",
              "| Plot price | Cost −20% | Cost base | Cost +20% |", "|---|---|---|---|"]
    for pm, row in grid:
        lines.append(f"| {pm:+d}% | " + " | ".join(cr(v) for v in row) + " |")
    lines.append("")
    return "\n".join(lines)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("numbers")
    p.add_argument("--out")
    p.add_argument("--json")
    a = p.parse_args(argv)
    with open(a.numbers) as f:
        d = json.load(f)
    try:
        summary, comp_rows, base, grid = build(d)
    except InputError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    md = report(d, summary, comp_rows, base, grid)
    if a.out:
        with open(a.out, "w") as f:
            f.write(md)
    else:
        print(md)
    if a.json:
        with open(a.json, "w") as f:
            json.dump(summary, f, indent=2)
    return 0


if __name__ == "__main__":
    sys.exit(main())
