---
name: bhoomi-intake
description: Start a Bhoomi Board review of any Indian land or real-estate deal. Interviews the user and reads their documents, then writes the deal folder (deal.md, numbers.json, docs.md, question.md) that every other Bhoomi skill reads. Use first, or whenever the facts of a deal change.
---

# Bhoomi intake

You set up the deal folder. Every other Bhoomi skill reads what you write, so
accuracy here matters more than speed.

## Output: the `bhoomi/` folder in the user's project

| File | What goes in it |
|---|---|
| `bhoomi/deal.md` | The facts. First line is `# <deal name>`. |
| `bhoomi/question.md` | The decision being asked, and the options on the table. |
| `bhoomi/numbers.json` | Every number the calculators need (schema below). |
| `bhoomi/docs.md` | Each document provided, what it proves, and its date. |

## Steps

1. **Read before asking.** Read every document the user attached or points to
   (title deeds, government orders, layout plans, valuations, MoUs, balance
   sheets, partnership deeds). Record each in `docs.md`.
2. **Ask only for what is missing**, in one batch of short questions. Never
   ask for something a document already answers.
3. **Write `deal.md`** with these sections: Parties and ownership; Land (survey
   numbers, areas, encumbrances); Location and access; Approvals (granted /
   pending, with dates); Infrastructure (built / approved / promised);
   Commercial position (asks, offers, comparables); Relationships (partners,
   developers, brokers, prior agreements); Open issues.
4. **Tag every fact** with its source: `[doc: name]`, `[stated]` (the user said
   it), or `[assumption]`. Assumptions must be few and named as such.
5. **Write `question.md`**: the decision in one sentence, the options being
   compared, the user's constraints (timing, who must agree, what they will
   not do), and what a good outcome looks like to them.
6. **Write `numbers.json`** using the schema in
   `examples/coastal-park/bhoomi/numbers.json`. Required for the valuer:
   `land`, `comparables`, `development`, `sales`, `finance`. The CFO also
   needs `sales.plot_price_per_acre_inr`, plus `offers`, `stakeholders`,
   `payouts` and `cash_events` where they exist. Leave a field out rather
   than inventing it: the tools stop with a clear error, which is the point.
7. **Check units twice.** Write each comparable price in the unit the source
   used (`inr/sqm`, `inr/sqyd`, `cr/acre`, `lakh/cent`, ...). Confirm the unit
   with the user if the source is ambiguous: per sq m and per sq yd differ by
   about 20%. `skills/bhoomi-valuer/units.py` converts.
8. **Flag inconsistencies** between documents (areas, dates, ownership
   percentages) at the top of `deal.md` under "Inconsistencies to resolve".

## Rules

- Private deal data stays in the user's project. Never put it in the plugin
  folder or in examples.
- Use Indian units and denominations (lakh, crore, acre, sq yd, gunta, cent).
- Next step: tell the user to run `/bhoomi-valuer`, or `/bhoomi-chair` to run
  the whole panel.
