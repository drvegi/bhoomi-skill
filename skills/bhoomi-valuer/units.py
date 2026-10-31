#!/usr/bin/env python3
"""Area and price-per-area conversion for Indian land deals.

Standard library only. Every factor is in square metres.

Examples:
  python3 units.py 10 acre --to sqyd
  python3 units.py 4500 inr/sqm --to inr/acre
  python3 units.py 1.82 cr/acre --to inr/sqyd
"""
import argparse
import sys

SQM = {
    "sqm": 1.0,
    "sqft": 0.09290304,
    "sqyd": 0.83612736,
    "acre": 4046.8564224,
    "hectare": 10000.0,
    "ha": 10000.0,
    "gunta": 4046.8564224 / 40,   # 1/40 acre, used in AP/Telangana/Karnataka
    "cent": 4046.8564224 / 100,   # 1/100 acre, used in AP/Kerala/Tamil Nadu
    "ankanam": 72 * 0.09290304,   # 72 sq ft, used in Andhra Pradesh
    "guntha": 4046.8564224 / 40,
}

MONEY = {"inr": 1.0, "lakh": 1e5, "lac": 1e5, "cr": 1e7, "crore": 1e7}


def area(value, frm, to):
    """Convert an area from one unit to another."""
    return value * SQM[_u(frm)] / SQM[_u(to)]


def price(value, frm, to):
    """Convert a price-per-area, e.g. ('inr/sqm' -> 'cr/acre')."""
    m1, a1 = _split(frm)
    m2, a2 = _split(to)
    inr_per_sqm = value * MONEY[m1] / SQM[a1]
    return inr_per_sqm * SQM[a2] / MONEY[m2]


def _u(unit):
    unit = unit.lower().strip()
    if unit not in SQM:
        raise ValueError(f"unknown area unit '{unit}'. Known: {', '.join(sorted(SQM))}")
    return unit


def _split(spec):
    if "/" not in spec:
        raise ValueError(f"price unit must look like 'inr/sqm', got '{spec}'")
    money, ar = spec.lower().split("/", 1)
    if money not in MONEY:
        raise ValueError(f"unknown money unit '{money}'. Known: {', '.join(sorted(MONEY))}")
    return money, _u(ar)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("value", type=float)
    p.add_argument("unit", help="area unit (acre) or price unit (inr/sqm)")
    p.add_argument("--to", required=True)
    a = p.parse_args(argv)
    try:
        if "/" in a.unit:
            out = price(a.value, a.unit, a.to)
        else:
            out = area(a.value, a.unit, a.to)
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    print(f"{a.value:g} {a.unit} = {out:,.4f} {a.to}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
