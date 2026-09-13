---
task: "Kingshot Pet Material Planner — material-to-Advance planning tool"
project: pet-material-planner
phase: learn
progress: 17/17
started: 2026-09-06T00:00:00Z
updated: 2026-09-06T00:00:00Z
iteration: 2
resumed_at: 2026-09-07T06:48:46.356Z
resumed_from_phase: complete
---

<!-- Seeded from the repository's own build session and cross-checked against
index.html, tools/solve.py, README.md, and data/pet-advance-costs.json.
Figures used as illustration below are drawn from examples/sample-loadout.json,
which is itself already a labeled example in the repo, not a real account. -->

## Problem

Advancing a pet in Kingshot charges Pet Food, Growth Manuals, Nutrient
Potions, and Promotion Medallions **simultaneously**, at every multiple of
ten levels; a shortage of any single one blocks that Advance outright. A
player holding a stock of materials and a roster of pets at various levels
has no way to see, without manual arithmetic across up to seven generations'
worth of hundred-level cost tables, which Advances their current stock can
actually reach, what a Pet Chest is best opened as, or whether a pet already
fed to a milestone but not yet ascended still needs feeding (it does not —
only the ascend). The obvious framing — "optimize what to open my chests
as" — turns out to be the wrong problem: chests are rarely the binding
constraint, and a value-density approach to spending them produces wrong
answers because Advance costs are conjunctive, not independent.

## Vision

A player opens the tool, pastes in their material counts and roster (or
loads a saved one from `localStorage`), and immediately sees three ranked,
already-correct plans — furthest reach, chest-free, and event-optimized —
each stating plainly how many chests to open and as what, how much is left
over, and which pets get nothing this cycle. No arithmetic, no spreadsheet,
no risk of accidentally re-charging food for a milestone already fed.

## Out of Scope

- **Pet stats or ability values.** Only Advance-milestone counts are
  modeled; the source data carries no stat tables, so a pet's *combat*
  value per Advance is not represented — only the material/food cost.
- **Game-account integration.** No API pull of live material counts or
  roster state; entry is manual, by design (see Constraints).
- **Server-side accounts or multi-device sync via a backend.** State lives
  in the visitor's own browser only.
- **Splitting SG and KvK event scores.** The source publishes one shared
  figure for both; the tool labels it KvK throughout rather than inventing
  a distinction the data doesn't support.
- **An objective that avoids "wasting" stranded materials**, and one that
  explicitly maximizes spread across pets. Both were built, tested, and
  removed — see Decisions.

## Principles

- **Materials, not chests, are the unit of value.** A chest is a wrapper
  that lets a player cherry-pick which of three materials they get; it does
  not change the underlying cost arithmetic. Chest-equivalent pricing is
  kept as one clearly labeled comparison column, never as the primary unit.
- **Advances lead, KvK points follow.** An Advance milestone changes how a
  pet plays every day; the event score is a by-product of the same action.
  Every plan card headlines the Advance count first and states points third.
- **Present options, not a recommendation.** No card is marked "best" —
  which plan fits depends on account state the tool cannot see (an active
  event, a pet's actual combat value, how soon a relocation or other real
  constraint bites). The tool's job is to make each option's true cost
  legible, not to choose for the player.
- **The player decides which pets are worth planning for.** The tool has no
  ability or stat data, so it cannot judge whether a given pet will recoup
  its materials. A per-pet "Plan it?" flag lets the player exclude pets they
  judge aren't worth advancing right now, rather than the tool guessing.

## Constraints

- **Single self-contained HTML file.** `index.html` has no
  build step and no dependency beyond a Google Fonts stylesheet, so it can
  be opened from disk or dropped on any static host (GitHub Pages, Netlify,
  S3, a plain nginx directory) with zero backend.
- **Client-side persistence only.** Saved state lives in the visitor's own
  `localStorage`; there is no server-side store. This is load-bearing, not
  incidental — a shared backend would either mix players' accounts together
  or require per-user infrastructure the tool is explicitly trying to avoid
  (see Decisions).
- **CLI companion runs on the Python standard library alone.**
  `tools/solve.py` takes no third-party dependencies, so it stays runnable
  anywhere Python 3 exists, with no environment setup.
- **Cost data must self-verify against the published source on load.** The
  CLI asserts the loaded tables reproduce the source's published cumulative
  total for a Generation 4–7 pet from level 1 to 100; a data-entry error in
  `data/pet-advance-costs.json` should fail loudly rather than silently
  mis-price every plan.
- **The page opens empty.** Zeroed materials and no pets on first load, so a
  hosted copy never lets one visitor mistake another's saved figures — or
  the shipped example — for their own current state.

## Goal

Given a stock of Pet Food, Growth Manuals, Nutrient Potions, Promotion
Medallions, and Pet Chests, plus a roster of pets at stated levels and
ascension states, produce three ranked, immediately actionable plans —
furthest reach, chest-free, and highest event score — that respect the
conjunctive nature of Advance gates and never recommend hoarding chests at
the cost of a strictly worse plan, computed identically by both a browser
tool and a CLI.

## Features

### F0 · Cross-cutting — the shared cost/search model

Why: every other feature depends on this model being right; getting it
wrong silently mis-prices every plan the tool produces.

- [x] C1: Advance costs are modeled as a small integer-program search
      (depth-first enumeration pruned on two monotonic ceilings — Pet Food
      and chest budget) rather than a knapsack sorted by value density,
      because an Advance's four material requirements must all be met at
      once and a shortfall in any one blocks the gate regardless of surplus
      elsewhere.
- [x] C2: A pet fed to a milestone level but not yet ascended to it owes
      that Advance's non-food materials but **zero further Pet Food** — the
      food was already spent reaching the level; only the ascend is unpaid.
      This is exposed as an explicit "Ascended?" checkbox per pet rather
      than asking the player to enter one level lower, because entering
      `89` instead of `90` gets the owed-Advance count right but wrongly
      re-charges the food for level 90 a second time.
- [x] C3: Among plans tied on Advance count, the tiebreak is **least Pet
      Food spent**, never fewest chests opened. Chests are a stockpile with
      no competing use once a plan is chosen, so a chest-hoarding tiebreak
      can recommend a plan that is strictly worse on every other axis
      (fewer Advances possible, less event score, more food spent) purely
      to keep chests in the bank.
- Anti: a ranked plan is never surfaced that another available plan
  dominates on Advances, Pet Food, and event score simultaneously, solely
  because it opens fewer chests.

### F1 · Solver engine

Why: the search that turns a stock + roster into ranked, correct plans —
the part both the web tool and the CLI must agree on.

- [x] C4: The search enumerates candidate Advance sequences per pet
      depth-first, pruning any branch that exceeds either the Pet Food
      ceiling or the chest budget, since both are monotonically increasing
      and safe to prune on.
- [x] C5: Three objectives are supported — **Most Advances** (tie-break:
      least Pet Food, then most KvK), **Without opening a chest** (best
      plan reachable from materials already on hand, banking every chest),
      and **Most KvK points** (for a live event push).
- [x] C6: A "Plan it?" flag per pet excludes that pet from consideration
      entirely, without requiring the tool to model whether that pet's
      materials will ever be recouped.
- [x] C7: For every produced plan, the number of chests opened, the number
      left in the bank, remaining Pet Food, and any stranded materials are
      all reported alongside the Advance count and KvK score — so a plan
      that leaves chests unopened reads as an expected outcome, not a gap.

### F2 · Web tool (`index.html`)

Why: the primary, zero-install surface a player actually uses.

- [x] C8: The page is a single self-contained HTML file requiring no build
      step and no backend, deployable to any static host.
- [x] C9: Material and roster state persists to the visitor's own
      `localStorage` across reloads, with JSON export/import for backup or
      moving between devices.
- [x] C10: The page's initial state is zeroed materials and an empty
      roster, never a filled-in example, so a fresh visitor cannot mistake
      shipped sample data for their own account.
- [x] C11: A per-pet "Ascended?" checkbox and "Plan it?" checkbox are both
      present and independently affect the plan the solver returns for
      that pet (C2, C6).
- [x] C12: Each plan card states, in order: Advances unlocked, chests
      opened of chests available, Pet Food spent, and KvK points — Advances
      first, points last, per the Advances-lead-points-follow principle.

### F3 · CLI parity tool (`tools/solve.py`)

Why: a scriptable, stdlib-only way to check the web tool's output and run
one-off scenarios (larger stocks, hypothetical rosters) without a browser.

- [x] C13: The CLI accepts all five stock quantities as flags (`--food`,
      `--manuals`/`--gm`, `--potions`/`--np`, `--medallions`/`--pm`,
      `--chests`) and a roster override via repeated `--pet
      NAME:LEVEL[:ASCENDED]`.
- [x] C14: `--list-pets` prints valid pet names for `--pet`, so a caller
      never has to open the data file to discover the roster vocabulary.
- [x] C15: The CLI's solve/prune/tiebreak logic implements the same model
      as F0/F1 — same objectives, same tiebreak, same ascended-food rule —
      so it can be used to independently check the web tool's answer for a
      given stock and roster.

### F4 · Data integrity (`data/pet-advance-costs.json`)

Why: every plan's correctness is only as good as the underlying cost table;
a silent transcription error would mis-price every Advance downstream.

- [x] C16: Cost tables cover all seven pet generations, sourced from a
      named, dated external source (the Kingshot Optimizer pets database),
      with the retrieval date recorded in the data file.
- [x] C17: On load, the CLI asserts the tables reproduce the source's
      published cumulative totals for a Generation 4–7 pet from level 1 to
      100 (2,990 Growth Manuals · 600 Nutrient Potions · 310 Promotion
      Medallions · 834,625 Pet Food), so a bad data edit fails loudly
      instead of silently shifting every plan's numbers.

## Test Strategy

| isc | type | check | threshold | tool | anchors_to |
|-----|------|-------|-----------|------|------------|
| C1 | manual | search enumerates depth-first with monotonic pruning, not sorted value-density | search never greedily sorts materials | code read | `tools/solve.py` `solve()`/`walk()` |
| C2 | manual | ascended=false at a milestone level charges zero food for that Advance | food delta is 0 for the owed Advance | code read | `tools/solve.py` `owed_advances()`/`cumulative_food()`; `index.html` Ascended? column |
| C3 | manual | tie-break tuple orders least-food before fewest-chests | food ordered before chests in the comparison key | code read | `index.html` sort key (`[nadv, -food, kvk, -chests]`) |
| C4 | manual | pruning ceilings are monotonic (food, chest budget) | branch pruned once either ceiling is exceeded | code read | `tools/solve.py` `walk()` |
| C5 | manual | three objective definitions present with stated tie-breaks | labels + tie-break text match spec | code read | `index.html` objective table (`"Most Advances"`/`"Without opening a chest"`/`"Most KvK points"`) |
| C6 | manual | excluded pet contributes nothing to any plan | excluded pet absent from all three plans | manual run | `index.html` "Plan it?" column / roster `on` field |
| C7 | manual | plan output states chests opened/kept, food remaining, stranded materials | all four figures present per plan | manual run | `index.html` leftover/eyebrow rendering |
| C8 | build | file opens standalone with no build step | opens directly in a browser from disk | manual run | `index.html` |
| C9 | manual | state round-trips through reload and export/import | roster + stock identical after reload | manual run | `index.html` `save()`/`restore()`, export/import |
| C10 | manual | first load with no saved state shows zeroed materials, empty roster | all stock fields 0, roster empty | manual run | `index.html` initial state |
| C11 | manual | toggling Ascended?/Plan it? changes the computed plan | plan output changes on toggle | manual run | `index.html` roster table |
| C12 | manual | card text order is Advances, chests, food, KvK | order matches spec | manual run | `index.html` card rendering |
| C13 | cli | `solve.py --help` lists all stock flags and `--pet` | flags present and documented | shell | `tools/solve.py` argparse setup |
| C14 | cli | `solve.py --list-pets` prints roster names | non-empty name list | shell | `tools/solve.py` `--list-pets` |
| C15 | manual | CLI and web tool agree on plans for the same stock/roster | identical Advances/food/chests/KvK per objective | manual cross-check | `tools/solve.py` vs `index.html` |
| C16 | manual | all seven generations present with source + retrieval date recorded | `_source`/`_retrieved` fields present; 7 `generations` entries | code read | `data/pet-advance-costs.json` |
| C17 | cli | loaded tables reproduce source's published Gen4-7 cumulative totals | exact match to documented totals | script (`assert` on load) | `tools/solve.py` load-time assertion |

## Decisions

- 2026-09-06: Modeled Advance planning as a pruned depth-first search over
  conjunctive requirements rather than a knapsack, after establishing that
  Advance gates need all four materials plus food at once — there is no
  single value-per-weight ordering to sort by. (C1)
- 2026-09-06: Added an explicit per-pet "Ascended?" checkbox rather than
  asking players to enter one level below their real level to fake the
  un-ascended state, because the level-minus-one workaround gets the owed
  Advance count right but silently re-charges food for a level already
  paid for. (C2)
- 2026-09-06: Fixed the "Most Advances" tiebreak from fewest-chests-opened
  to least-Pet-Food-spent, after finding the original tiebreak picked a
  plan that was worse on Advances unlocked, KvK score, and Pet Food spent,
  purely to leave more chests unopened — a stockpile with no competing use.
  (C3, Anti-C3)
- 2026-09-06: Cut a fourth "Least waste" objective (minimize stranded
  materials). Once the tiebreak above was fixed, this objective only ever
  selected plans dominated by "Most Advances" — stranding a handful of
  materials to save a large amount of food is the obviously correct trade,
  so an objective built to avoid stranding was optimizing against noise.
- 2026-09-06: Cut a fifth "Widest spread" objective (maximize the number of
  distinct pets touched). It never diverged from "Most Advances" across a
  wide sweep of test stocks, because Advance prices escalate with level, so
  a fresh pet's next Advance is usually cheaper than an already-advanced
  pet's next one — maximizing count already spreads investment naturally in
  the common case. The two only separate when one under-leveled pet can
  stack several cheap Advances versus several other pets each needing one
  expensive Advance — judged too narrow a case to justify a fourth card.
- 2026-09-06: Chose `localStorage` over any server-side store. The tool is
  meant to be hosted for other players, and a shared backend would either
  mix accounts together or require per-user infrastructure and an
  operator; browser storage gives every visitor a private loadout at zero
  infrastructure cost and keeps the page trivially self-hostable.
- 2026-09-06: Chose to make the page load empty (zeroed stock, no roster)
  rather than pre-filled with a working example, so a hosted copy never
  risks a visitor mistaking a shipped example — or another visitor's
  figures — for their own account. The worked example instead lives at
  `examples/sample-loadout.json`, loaded on request via Paste-a-loadout.
- D-auto-2026-09-07T06:48:46.356Z: Auto-resumed from complete to learn at 2026-09-07T06:48:46.356Z — iteration 2

## Learning

- conjectured: Pet Chests were likely to be the binding constraint on an
  account holding a large stock of them, so the natural question was "how
  should I best spend my chests."
  refuted by: running the solver against a fully-stocked example account
  (see `examples/sample-loadout.json`) showed the best plan under the
  furthest-reach objective used well under a quarter of the available
  chests, because Pet Food ran out first and no chest can mint Pet Food.
  learned: chests are a flexible wrapper around three of four required
  materials, but they cannot address a Pet Food shortfall — Pet Food, not
  chest count, is the actual bottleneck in the account states this tool is
  built around.
  criterion now: C7 — every plan must report chests opened *of* chests
  available and Pet Food remaining side by side, so a plan that leaves most
  chests unopened reads as expected, not as an unsolved case.
- conjectured: averaging a pet's four material shares evenly across levels
  1–100 gives a fair approximation of how much of a pet's total value each
  Advance milestone represents (e.g. reaching level 70 costs roughly 36% of
  everything the pet will ever consume).
  refuted by: Promotion Medallions are 0% of cost until the Advance to 50
  and then dominate every gate after it, so an equal four-way average
  understates early-level cost concentration in Manuals/Potions/Food and
  understates how steep the true curve becomes once Medallions enter —
  which matters specifically when Medallions are a player's actual
  bottleneck resource.
  learned: the milestones-vs-materials curve is a useful approximation of
  relative value, not an exact one, and its accuracy depends on which
  material is scarce for the reader.
  criterion now: the curve is documented with this caveat every place it is
  shown, rather than presented as a precise value measure (see Known
  Limits below, and README.md § Data).

## Verification

- C1–C7, C16: code read, `tools/solve.py` + `index.html` — current committed source.
- C17: `tools/solve.py` load-time `assert` against documented Gen 4–7 totals — passes on load.
- C8–C12: manual run, opened `index.html` from disk with no server.
- C13–C14: manual run, `python3 tools/solve.py --help` / `--list-pets`.
- C15: manual cross-check, `tools/solve.py` against `index.html` for the example loadout.

## Remaining Work

- [x] `README.md`'s file tree listed `SESSION-NOTES.md`, which
  `.gitignore`'s `SESSION-*` pattern deliberately excludes from a fresh
  clone. Fixed — the Layout section now points at `ISA.md` instead.
- [x] No `LICENSE` file yet. Fixed — MIT, held by `somebodyelsegaming`, with
  the `data/pet-advance-costs.json` cost tables explicitly carved out as
  derived from the Kingshot Optimizer database and not the holder's to
  relicense. MIT was chosen so the upstream data source can absorb this tool
  into their own site, commercial or closed, without legal review.
- [ ] No deploy workflow. Optional — the tool is a single static HTML file,
  so pointing GitHub Pages at the repository root is sufficient; a workflow
  only earns its place if a build step is ever introduced.

## Known Limits

- Advance milestones stand in for a pet's value; the source data carries no
  stat or ability tables, so true combat value per Advance is not modeled
  (see Out of Scope).
- Pet Food between two Advance milestones is interpolated evenly across the
  intervening ten levels, since the source publishes cumulative food only
  at each Advance; a level partway between milestones is accurate to
  within a few hundred food, not exact.
- The milestones-vs-total-materials curve averages the four material
  shares equally, which is a judgement call, not a fact drawn from the
  game — see the Medallions caveat under Learning above.
