#!/usr/bin/env python3
"""Monthly deal cash flow: sources and uses, peak funding, NPV, IRR, exit coverage.

Reads numbers.json. Inflows: anchor offers (with payment schedules), plot sales
spread over the absorption window, and any one-off cash events. Outflows:
development cost, payouts to exiting stakeholders, settlements, interest.
A missing required field is an error, never a guess. Standard library only.

  python3 cashflow.py bhoomi/numbers.json --out bhoomi/cfo-calc.md --json bhoomi/cfo.json
"""
import argparse
import json
import sys


class InputError(Exception):
    pass


def need(d, path):
    cur = d
    for k in path.split("."):
        if not isinstance(cur, dict) or k not in cur:
            raise InputError(f"missing required input: {path}")
        cur = cur[k]
    return cur


def build_flows(d):
    saleable = need(d, "land.saleable_acres")
    plot_price = need(d, "sales.plot_price_per_acre_inr")
    absorb = need(d, "sales.absorption_months")
    s_start = need(d, "sales.start_month")
    sell_pct = need(d, "sales.selling_cost_pct") / 100
    dev_cost = need(d, "development.cost_inr")
    dev_months = need(d, "development.months")
    dev_start = d["development"].get("start_month", 1)
    subsidy = d["development"].get("subsidy_inr", 0)
    subsidy_month = d["development"].get("subsidy_month", dev_start + dev_months)

    events = []  # (month, amount, label)
    anchored = 0.0
    for o in d.get("offers", []):
        for k in ("party", "acres", "price_per_acre_inr"):
            if k not in o:
                raise InputError(f"offer missing '{k}'")
        total = o["acres"] * o["price_per_acre_inr"]
        anchored += o["acres"]
        sched = o.get("payment_schedule") or [{"month": o.get("month", 1), "pct": 100}]
        if abs(sum(s["pct"] for s in sched) - 100) > 0.01:
            raise InputError(f"payment_schedule for {o['party']} must add up to 100%")
        for s in sched:
            events.append((s["month"], total * s["pct"] / 100 * (1 - sell_pct), f"{o['party']} ({s['pct']:g}%)"))
    if anchored > saleable:
        raise InputError("offers cover more acres than land.saleable_acres")
    remaining = saleable - anchored
    per_month = remaining * plot_price * (1 - sell_pct) / absorb if absorb else 0
    for i in range(absorb):
        events.append((s_start + i, per_month, "plot sales"))
    for i in range(dev_months):
        events.append((dev_start + i, -dev_cost / dev_months, "development"))
    if subsidy:
        events.append((subsidy_month, subsidy, "capital subsidy"))
    for p in d.get("payouts", []):
        for k in ("to", "amount_inr", "month"):
            if k not in p:
                raise InputError(f"payout missing '{k}'")
        events.append((p["month"], -p["amount_inr"], f"payout: {p['to']}"))
    for e in d.get("cash_events", []):
        for k in ("label", "month", "amount_inr"):
            if k not in e:
                raise InputError(f"cash_event missing '{k}'")
        events.append((e["month"], e["amount_inr"], e["label"]))
    horizon = max(m for m, _, _ in events) if events else 0
    flows = [0.0] * (horizon + 1)  # index 0 = today
    for m, amt, _ in events:
        if m < 0:
            raise InputError("months must be 0 or later")
        flows[m] += amt
    return flows, events, remaining


def npv(flows, annual_pct):
    r = (1 + annual_pct / 100) ** (1 / 12) - 1
    return sum(f / (1 + r) ** t for t, f in enumerate(flows))


def irr(flows):
    """Annualised IRR by bisection on the monthly rate; None if no sign change."""
    signs = [f > 0 for f in flows if f != 0]
    changes = sum(1 for a, b in zip(signs, signs[1:]) if a != b)
    if changes != 1:
        return None  # zero or several roots: IRR is not meaningful

    def f(r):
        return sum(c / (1 + r) ** t for t, c in enumerate(flows))
    lo, hi = -0.99, 1.0
    flo, fhi = f(lo), f(hi)
    if flo * fhi > 0:
        return None
    for _ in range(200):
        mid = (lo + hi) / 2
        fm = f(mid)
        if flo * fm <= 0:
            hi, fhi = mid, fm
        else:
            lo, flo = mid, fm
    return ((1 + (lo + hi) / 2) ** 12 - 1) * 100


def build(d):
    flows, events, remaining = build_flows(d)
    cum, running, low, low_m, pos_m = [], 0.0, 0.0, 0, None
    for t, f in enumerate(flows):
        running += f
        cum.append(running)
        if running < low:
            low, low_m = running, t
    for t in range(len(cum)):
        if all(c >= 0 for c in cum[t:]):
            pos_m = t
            break
    rate = need(d, "finance.discount_rate_pct")
    implied = []
    for s in d.get("stakeholders", []):
        if s.get("ask_inr") and s.get("stake_pct"):
            implied.append({"name": s["name"], "stake_pct": s["stake_pct"], "ask_inr": s["ask_inr"],
                            "implied_whole_value_inr": s["ask_inr"] / (s["stake_pct"] / 100)})
    summary = {
        "horizon_months": len(flows) - 1,
        "net_cash_total_inr": sum(flows),
        "peak_funding_need_inr": -low,
        "peak_funding_month": low_m,
        "cash_positive_from_month": pos_m,
        "npv_inr": npv(flows, rate),
        "irr_annual_pct": irr(flows),
        "payouts_covered_without_funding": low >= 0,
        "unanchored_saleable_acres": remaining,
        "implied_valuations": implied,
    }
    return summary, flows, cum, events


def cr(x):
    return f"₹{x / 1e7:,.2f} Cr"


def report(d, summary, flows, cum, events):
    L = [f"# CFO calculations: {d.get('deal', 'deal')}", "",
         "Computed from numbers.json. Selling costs are netted off sale receipts.", "",
         "## Headline", "", "| Measure | Value |", "|---|---|",
         f"| Net cash over {summary['horizon_months']} months | {cr(summary['net_cash_total_inr'])} |",
         f"| Peak funding need | {cr(summary['peak_funding_need_inr'])} (month {summary['peak_funding_month']}) |",
         f"| Cash stays positive from | month {summary['cash_positive_from_month']} |",
         f"| NPV at {d['finance']['discount_rate_pct']}% | {cr(summary['npv_inr'])} |",
         f"| IRR (annual) | {summary['irr_annual_pct']:.1f}% |" if summary["irr_annual_pct"] is not None
         else "| IRR (annual) | not meaningful: cash flow changes sign more than once (advance in, then spend, then sales). Use NPV and peak funding. |",
         f"| Payouts covered without outside funding | {'Yes' if summary['payouts_covered_without_funding'] else 'No'} |",
         ""]
    if summary["implied_valuations"]:
        L += ["## What each stakeholder's ask implies for the whole", "",
              "| Stakeholder | Stake | Ask | Implied value of 100% |", "|---|---|---|---|"]
        for s in summary["implied_valuations"]:
            L.append(f"| {s['name']} | {s['stake_pct']:g}% | {cr(s['ask_inr'])} | {cr(s['implied_whole_value_inr'])} |")
        L.append("")
    L += ["## Quarterly cash flow", "", "| Quarter | Net flow | Cumulative |", "|---|---|---|"]
    q = 0
    for start in range(0, len(flows), 3):
        net = sum(flows[start:start + 3])
        L.append(f"| Q{q} (months {start}-{min(start + 2, len(flows) - 1)}) | {cr(net)} | {cr(cum[min(start + 2, len(cum) - 1)])} |")
        q += 1
    L += ["", "## Named events", "", "| Month | Item | Amount |", "|---|---|---|"]
    for m, amt, label in sorted(e for e in events if e[2] not in ("plot sales", "development")):
        L.append(f"| {m} | {label} | {cr(amt)} |")
    L.append("")
    return "\n".join(L)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("numbers")
    p.add_argument("--out")
    p.add_argument("--json")
    a = p.parse_args(argv)
    with open(a.numbers) as f:
        d = json.load(f)
    try:
        summary, flows, cum, events = build(d)
    except InputError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    md = report(d, summary, flows, cum, events)
    if a.out:
        open(a.out, "w").write(md)
    else:
        print(md)
    if a.json:
        json.dump(summary, open(a.json, "w"), indent=2)
    return 0


if __name__ == "__main__":
    sys.exit(main())
