# Valuer methods (summary in our own words)

## 1. Comparables with an adjustment grid

Start from the closest evidence and adjust each comparable towards the
subject. Typical adjustments for Indian industrial and layout land:

| Factor | Typical range | Direction |
|---|---|---|
| Infrastructure status | 10-30% | Subject not yet built: discount |
| Time to infrastructure | ~8-15% per year of delay | Discount for delay |
| Plot size | 5-20% | Small plots sell higher per unit than large |
| Location / access | 5-25% | Frontage, highway, port distance |
| Title and approvals | 5-30% | Pending approvals or encumbrances: discount |
| Market timing | per month or year | Older evidence: index forward |
| Asking vs transacted | 5-15% | Asking prices sit above deals |

Weight registered transactions above asking prices, and recent above old.

## 2. Residual land value

Land value = Gross development value − development cost (net of subsidy) −
selling cost − developer's profit, discounted for time. The calculator does
this on a monthly basis. A residual at or below zero means the scheme does
not pay for the land at those assumptions.

## 3. Layout yield

Saleable ÷ gross area. Industrial parks in India commonly reach 55-70%.
Common gains: plots fronting existing external roads, roads that serve plots
on both sides, putting required green space in leftover triangles.
Required open space, buffers (coastal, pollution, high-tension lines) and
utility plots do not disappear when the layout changes.

## 4. Absorption

How many acres sell per month. Small-plot schemes sell more slowly but at
higher unit prices. An anchor buyer can re-rate the rest of the scheme.

## 5. Indian reference points to look up

- Sub-registrar guideline (market) value for the village: the floor for
  stamp duty and for tax under Section 50C.
- State industrial corporation (e.g. APIIC, TSIIC, SIPCOT, MIDC) allotment
  rates nearby: the price end users compare with.
- Recent registered sales in the same mandal or taluk.

## 6. The unit trap

1 acre = 4,046.86 sq m = 4,840 sq yd. ₹1,000/sq m = ₹836/sq yd. Confusing the
two moves a price by about 20%. Always run `units.py`.
