import json
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SK = os.path.join(ROOT, "skills")
for s in ("bhoomi-valuer", "bhoomi-cfo", "bhoomi-buyers", "bhoomi-chair"):
    sys.path.insert(0, os.path.join(SK, s))

import units  # noqa: E402
import residual  # noqa: E402
import cashflow  # noqa: E402
import panel  # noqa: E402
import verdict  # noqa: E402

EXAMPLE = os.path.join(ROOT, "examples", "coastal-park", "bhoomi", "numbers.json")


def example():
    with open(EXAMPLE) as f:
        return json.load(f)


class Units(unittest.TestCase):
    def test_acre_in_sqyd(self):
        self.assertAlmostEqual(units.area(1, "acre", "sqyd"), 4840.0, places=3)

    def test_acre_in_sqm(self):
        self.assertAlmostEqual(units.area(1, "acre", "sqm"), 4046.8564, places=3)

    def test_sqm_price_to_acre(self):
        # 4,500 per sq m is about 1.82 crore per acre (the classic sq m / sq yd trap)
        self.assertAlmostEqual(units.price(4500, "inr/sqm", "cr/acre"), 1.8211, places=3)

    def test_sqyd_price_to_acre(self):
        self.assertAlmostEqual(units.price(4500, "inr/sqyd", "cr/acre"), 2.178, places=3)

    def test_local_units(self):
        self.assertAlmostEqual(units.area(40, "gunta", "acre"), 1.0)
        self.assertAlmostEqual(units.area(100, "cent", "acre"), 1.0)

    def test_unknown_unit(self):
        with self.assertRaises(ValueError):
            units.area(1, "bigha", "acre")


class Residual(unittest.TestCase):
    def test_runs_and_is_consistent(self):
        s, rows, base, grid = residual.build(example())
        self.assertAlmostEqual(base["yield_pct"], 100 * 40 / 60)
        self.assertAlmostEqual(base["gdv"], 40 * s["comparable_price_per_saleable_acre"])
        # higher price must raise residual; higher cost must lower it
        self.assertLess(grid[0][1][1], grid[3][1][1])
        self.assertGreater(grid[2][1][0], grid[2][1][2])

    def test_break_even_formula(self):
        d = example()
        be = residual.break_even(d, 6000000)
        expected = (6000000 * 60 + 160000000 - 30000000) / (40 * 0.97)
        self.assertAlmostEqual(be, expected)

    def test_missing_field_is_error(self):
        d = example()
        del d["development"]["cost_inr"]
        with self.assertRaises(residual.InputError):
            residual.build(d)

    def test_saleable_cannot_exceed_gross(self):
        d = example()
        d["land"]["saleable_acres"] = 70
        with self.assertRaises(residual.InputError):
            residual.build(d)


class Cashflow(unittest.TestCase):
    def test_irr_simple(self):
        flows = [-100] + [0] * 11 + [115]
        self.assertAlmostEqual(cashflow.irr(flows), 15.0, places=2)

    def test_example_runs(self):
        s, flows, cum, events = cashflow.build(example())
        self.assertGreaterEqual(s["peak_funding_need_inr"], 0)
        self.assertAlmostEqual(s["unanchored_saleable_acres"], 32)
        vals = {v["name"]: v["implied_whole_value_inr"] for v in s["implied_valuations"]}
        self.assertAlmostEqual(vals["Partner A"], 300000000)

    def test_schedule_must_total_100(self):
        d = example()
        d["offers"][0]["payment_schedule"][0]["pct"] = 20
        with self.assertRaises(cashflow.InputError):
            cashflow.build(d)

    def test_missing_plot_price(self):
        d = example()
        del d["sales"]["plot_price_per_acre_inr"]
        with self.assertRaises(cashflow.InputError):
            cashflow.build(d)


class Panel(unittest.TestCase):
    def test_same_seed_same_cards(self):
        self.assertEqual(panel.deal_cards(20, 3), panel.deal_cards(20, 3))

    def test_only_filter(self):
        cards = panel.deal_cards(10, 1, ["msme_manufacturer"])
        self.assertTrue(all(c["archetype"] == "msme_manufacturer" for c in cards))

    def test_init_check_tally(self):
        with tempfile.TemporaryDirectory() as t:
            d = os.path.join(t, "buyers")
            panel.main(["init", "--dir", d, "--n", "3", "--seed", "1"])
            self.assertEqual(panel.main(["check", "--dir", d]), 1)  # no answers yet
            for i, interest in enumerate(["yes", "maybe", "no"], 1):
                ans = {"buyer": f"buyer-{i:02d}", "interest": interest, "acres_wanted": 5,
                       "price_per_acre_inr": 14000000 if interest != "no" else None,
                       "walk_away_per_acre_inr": None, "preferred_structure": "outright",
                       "conditions": ["clear title"], "top_objection": "approvals pending",
                       "what_flips_a_no": "Finished access road."}
                json.dump(ans, open(os.path.join(d, "answers", f"buyer-{i:02d}.json"), "w"))
            self.assertEqual(panel.main(["check", "--dir", d]), 0)
            js = os.path.join(t, "b.json")
            panel.main(["tally", "--dir", d, "--out", os.path.join(t, "b.md"), "--json", js])
            s = json.load(open(js))
            self.assertEqual(s["interest"], {"yes": 1, "maybe": 1, "no": 1})
            self.assertAlmostEqual(s["interest_rate_pct"], 50.0)

    def test_price_outlier_flagged(self):
        ans = {f"buyer-{i:02d}": {"price_per_acre_inr": v, "walk_away_per_acre_inr": None}
               for i, v in enumerate([9500000, 10500000, 11000000, 95000000], 1)}
        errs = panel.price_outliers(ans)
        self.assertEqual(len(errs), 1)
        self.assertIn("buyer-04", errs[0])


class Verdict(unittest.TestCase):
    base = {
        "valuer": {"residual_pv_per_gross_acre": 5e6, "offers": [{"party": "A", "vs_break_even_pct": 5}]},
        "cfo": {"payouts_covered_without_funding": True, "npv_inr": 1e7, "peak_funding_need_inr": 0, "peak_funding_month": 0},
        "legal": {"blockers": [], "conditions": [], "sign_offs": []},
        "buyers": {"interest_rate_pct": 60},
        "redteam": {"kill_risks": []},
    }

    def copy(self):
        return json.loads(json.dumps(self.base))

    def test_incomplete(self):
        s = self.copy()
        s["legal"] = None
        self.assertEqual(verdict.decide(s)[0], "Incomplete")

    def test_proceed_if_market_confirmation(self):
        self.assertEqual(verdict.decide(self.copy())[0], "Proceed if")

    def test_stop_on_unmitigated_blocker(self):
        s = self.copy()
        s["legal"]["blockers"] = [{"item": "title dispute", "status": "open"}]
        self.assertEqual(verdict.decide(s)[0], "Don't proceed")

    def test_stop_on_low_offer(self):
        s = self.copy()
        s["valuer"]["offers"][0]["vs_break_even_pct"] = -15
        self.assertEqual(verdict.decide(s)[0], "Don't proceed")

    def test_proceed_when_clean_and_buyers_skipped(self):
        self.assertEqual(verdict.decide(self.copy(), skip=("buyers",))[0], "Proceed")


class CLI(unittest.TestCase):
    def test_units_cli(self):
        out = subprocess.run([sys.executable, os.path.join(SK, "bhoomi-valuer", "units.py"), "1", "acre", "--to", "sqyd"],
                             capture_output=True, text=True)
        self.assertIn("4,840", out.stdout)


if __name__ == "__main__":
    unittest.main()
