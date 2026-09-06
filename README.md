# Kingshot Pet Material Planner

A single-file web tool that works out which pet Advances a given stock of
materials can actually reach — and how many Pet Chests to open, as what.

## The problem

Advancing a pet in Kingshot charges **Pet Food**, **Growth Manuals**,
**Nutrient Potions** and **Promotion Medallions** at the same time, at every
multiple of 10. A shortage of any one blocks the whole gate.

A **Pet Chest** opens into one material of your choosing:

| Chest opens as | Yield |
| --- | --- |
| Growth Manual | 7 |
| Nutrient Potion | 2 |
| Promotion Medallion | 1 |

So the question "what should I open my chests as?" looks like a knapsack
problem, but isn't. A knapsack picks items with **independent** values under
one budget. Advance gates are **conjunctive** — the Advance to 50 needs 220
Manuals *and* 50 Potions *and* 10 Medallions *and* 54,050 Pet Food together.
Trading one material for another doesn't add value linearly; missing any one
blocks the gate outright. The planner therefore enumerates whole plans and
prunes, rather than sorting by value density.

Chests also cannot mint Pet Food, which is usually what really limits a plan.

## Running it

`pet-material-planner.html` is self-contained — no build step, no backend, no
dependencies beyond a Google Fonts stylesheet. Open it from disk, or drop it
on any static host (GitHub Pages, Netlify, S3, a plain nginx directory).

Saved state lives in the visitor's own `localStorage`, so a hosted copy gives
every player their own private loadout with no server involved. There is also
JSON export/import for backups and moving between devices.

## Layout

```
pet-material-planner.html      the tool — this is the whole app
data/pet-advance-costs.json    Advance cost tables, all 7 generations
tools/solve.py                 the same model as a CLI, for checking results
examples/sample-loadout.json   a filled-in account, to see the tool working
ISA.md                         why it's built this way — design rationale, claims, limits
```

The page opens empty — zeroed materials and no pets — so nobody mistakes
someone else's figures for their own. To see it working straight away, open
**Paste a saved loadout**, drop in the contents of
`examples/sample-loadout.json` and press Load. It carries a mid-game account
with three pets sitting un-ascended on milestones, which is the case worth
understanding: those Advances cost no further Pet Food.

`tools/solve.py` needs only the standard library. `--help` lists everything:

```
python3 tools/solve.py                              # the built-in roster
python3 tools/solve.py --chests 400                 # what 400 chests reach
python3 tools/solve.py --food 500000 --medallions 150
python3 tools/solve.py --pet "Giant Rhino:81" --pet "Ironclad War Bear:100:no"
python3 tools/solve.py --list-pets                  # valid names for --pet
```

All five materials can be set from the command line — `--food`, `--manuals`,
`--potions`, `--medallions`, `--chests` (the short `--gm`, `--np`, `--pm`
aliases also work). Defaults come from the `STOCK` constant near the top of
the file, so an account you check often is easier to set there once.

`--pet NAME:LEVEL[:ASCENDED]` replaces the roster without editing the file;
repeat it per pet. `ASCENDED` is `yes`/`no` and defaults to `no` — use `no` for
a pet fed to a milestone but not yet ascended, whose Advance then costs no
further Pet Food. Otherwise edit the `ROSTER` constant.

## Data

Cost tables come from the [Kingshot Optimizer pets
database](https://kingshotoptimizer.com/database/pets/), retrieved 2026-09-06,
and are checked against its published totals: a Gen 4–7 pet from level 1 to
100 costs **2,990 Growth Manuals, 600 Nutrient Potions, 310 Promotion
Medallions and 834,625 Pet Food**. `tools/solve.py` asserts this on load.

Two things worth knowing about the data:

- The source publishes **one shared score** for SG and KvK events. It is
  labelled KvK throughout this tool.
- Pet Food inside a ten-level band is spread evenly across those levels, since
  the source gives cumulative food only at each Advance. A level partway
  between Advances is therefore accurate to within a few hundred food.

Not affiliated with Kingshot or Century Games.
