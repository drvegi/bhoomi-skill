# Bhoomi Board

A board of simulated advisers for Indian land and real-estate deals. Free,
MIT, no API key, nothing to connect.

`/bhoomi-intake` `/bhoomi-valuer` `/bhoomi-cfo` `/bhoomi-legal` `/bhoomi-buyers` `/bhoomi-redteam` `/bhoomi-chair`

Put a land deal in front of a valuer, a CFO, a legal and regulatory adviser,
a panel of 20-50 buyer and investor agents and an independent red team. The
chair sets out where they agree and disagree and **computes** a verdict from
their numbers: **Proceed**, **Proceed if**, **Don't proceed** or
**Incomplete**, with a checklist of conditions and the professional
sign-offs needed before money moves.

Built for the questions landowners, promoters and family partnerships
actually face: sell raw or developed, what price an anchor buyer should pay,
how to fund partner exits, joint development or outright sale, what a
government approval allows, and what a buyer's lawyer will find.

## Install

Paste this repo link into Claude and say `install skill`:

```
https://github.com/drvegi/bhoomi-skill

install skill
```

Or as a plugin in Claude Code:

```
/plugin marketplace add drvegi/bhoomi-skill
/plugin install bhoomi-skill@bhoomi-skill
```

Or copy the folders:

```
git clone https://github.com/drvegi/bhoomi-skill.git
cp -r bhoomi-skill/skills/bhoomi-* ~/.claude/skills/
cp bhoomi-skill/agents/*.md ~/.claude/agents/
```

**No Claude Code?** Use the single-file chat edition in
`editions/chat/bhoomi-board/SKILL.md`. Upload it as a skill in the Claude app,
or paste it at the top of a chat. You lose the sub-agents and the calculators,
but the method works.

The calculators need Python 3.8 or newer. Nothing to pip install.

## The board

| Command | Seat | Lens (methods, not the firms) | Writes |
|---|---|---|---|
| `/bhoomi-intake` | Secretary | Reads your documents, asks only what is missing | `deal.md`, `question.md`, `numbers.json`, `docs.md` |
| `/bhoomi-valuer` | Property adviser | Global property consultancy methods (CBRE, JLL, Knight Frank, Colliers, Anarock): comparables grid, residual value, yield, absorption | `valuer.md`, `valuer.json` |
| `/bhoomi-cfo` | CFO | Big Four transaction advisory practice applied by an Indian chartered accountant: cash flow, exits, structures, tax map | `cfo.md`, `cfo.json` |
| `/bhoomi-legal` | Legal & regulatory | Indian real-estate law practice plus revenue-office experience: title, approvals, CRZ, pollution rules, agreements | `legal.md`, `legal.json` |
| `/bhoomi-buyers` | Buyer panel | 15 Indian buyer archetypes, 20-50 sub-agents, each with its own budget, motive and objection | `buyers.md`, `buyers.json` |
| `/bhoomi-redteam` | Red team | Independent sub-agent that attacks the recommendation | `redteam.md`, `redteam.json` |
| `/bhoomi-chair` | Chair | Weighs the board, names disagreements, computes the verdict | `chair.md`, `board-pack.md`, `verdict.json` |

## How to use it

Run `/bhoomi-chair` and it runs the whole board, or run the seats in order.
Each reads what the others wrote, in a `bhoomi/` folder in your project.

```
intake -> valuer -> cfo -> legal -> buyers -> redteam -> chair
```

The fictional example in `examples/coastal-park/` is a 60-acre MSME park
with an anchor buyer offer and two partners who want to exit. Run the
calculators on it:

```
cd examples/coastal-park
python3 ../../skills/bhoomi-valuer/residual.py bhoomi/numbers.json
python3 ../../skills/bhoomi-cfo/cashflow.py bhoomi/numbers.json
```

## The calculators

All standard-library Python. None touch the network. A missing input is an
error, never a guess.

| Tool | What it does |
|---|---|
| `bhoomi-valuer/units.py` | Converts acres, sq m, sq yd, sq ft, hectares, guntas, cents, ankanams, and prices between them. Stops the sq m / sq yd mistake that moves a price by 20%. |
| `bhoomi-valuer/residual.py` | Adjusted comparables, residual land value (undiscounted and present value), break-even plot price, offer tests, sensitivity grid. |
| `bhoomi-cfo/cashflow.py` | Monthly sources and uses, peak funding need, NPV, IRR where meaningful, exit coverage, what each stakeholder's ask implies for the whole. |
| `bhoomi-buyers/panel.py` | Deals buyer cards from `archetypes.json` (same seed, same cards), writes briefs, checks answers, tallies demand, price bands, structures and objections. It never answers for a buyer. |
| `bhoomi-chair/verdict.py` | Compiles the board pack and computes the verdict from the advisers' JSON. |

```
python3 -m unittest discover -s tests -v
```

## Buyer archetypes

Logistics park developers; integrated township developers; regional
developers diversifying; logistics operators; steel ancillaries; pharma/API
units; MSME manufacturers; real-estate funds; family offices; NRI
investors; local land investors; cold-chain and food processing; solar
developers (for land that cannot be built on); port-linked EXIM / CFS
operators; industrial REITs and InvITs. Edit `archetypes.json` to add your
own.

## Fine print

**The advisers apply published methods. They are not those firms.**
Reference points such as CBRE, EY, Mahindra or Casagrand describe the kind
of method or buying behaviour being modelled. No agent speaks as, quotes or
claims the endorsement of any firm or person. This project is not affiliated
with any of them.

**The buyer panel is simulated buyers, not customers.** Language models lean
agreeable, so read interest and prices as an upper bound and test with real
buyers. Never present panel answers as real demand or testimonials.

**Indian law changes.** The advisers search for current rules and cite them.
Tax and legal outputs are maps of what to check, not opinions.

**Not financial, legal or tax advice.** A qualified chartered accountant and
advocate confirm every sign-off item.

**Your deal data stays in your project.** Nothing here sends data anywhere.

## Roadmap

Seats planned after testing: developer and contractor panel (JDA developers,
EPC contractors), government and approvals lens, stakeholder negotiator,
lender, layout and yield planner, broker and marketing. Editions planned by
deal type: industrial (this one), residential layouts, farmland, commercial.

## License

MIT. Take it, change it, ship it.
