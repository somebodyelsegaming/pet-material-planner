#!/usr/bin/env python3
"""
Kingshot pet Advance solver.

Given a stock of materials and a roster of pets, find which combinations of
Advances are reachable. This is the same model the HTML planner runs on;
it exists separately so results can be checked and scripted.

Why this is not a knapsack: a knapsack picks items with independent values
under one budget. Advance gates are CONJUNCTIVE -- the Advance to 50 needs
220 Manuals AND 50 Potions AND 10 Medallions AND 54,050 Pet Food together,
and missing any one blocks the whole gate. So this enumerates plans by
depth-first search with pruning, rather than sorting by value density.

Usage:
    python3 solve.py                     # solve the roster defined below
    python3 solve.py --food 500000       # override a stock value
"""

import argparse
import json
import math
import os
import signal
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, os.pardir, "data", "pet-advance-costs.json")

CHEST_YIELD = {"gm": 7, "np": 2, "pm": 1}

# ---------------------------------------------------------------- edit me
# An EXAMPLE account, not anyone's real one — replace with your own, or
# override from the command line with --pet and the material flags.
#
# The fourth field is "ascended": True means the Advance AT that level has
# already been taken. A pet fed to a milestone but not yet ascended is False,
# and that Advance then costs no further Pet Food — which is usually the
# cheapest milestone available, so it is worth getting right.
ROSTER = [
    ("Ironclad War Elephant", "gen4plus", 30, True),
    ("Regal White Lion",      "gen4plus", 50, True),
    ("Mighty Bison",          "gen4plus", 80, False),
]
STOCK = {"food": 200000, "gm": 500, "np": 100, "pm": 0, "chests": 150}
# ------------------------------------------------------------------------


def load_tables(path=DATA):
    with open(path) as fh:
        return json.load(fh)["generations"]


def cumulative_food(rows, level):
    """Food eaten standing at `level`. Food inside a band is spread evenly."""
    prev_food, prev_level = 0, 0
    for r in rows:
        if level >= r[0]:
            prev_food, prev_level = r[1], r[0]
        else:
            frac = (level - prev_level) / (r[0] - prev_level)
            return prev_food + frac * (r[1] - prev_food)
    return prev_food


def owed_advances(rows, level, ascended):
    """Advances still owed, cheapest first, with the food each one needs."""
    out, food_so_far = [], cumulative_food(rows, level)
    for to_level, cum_food, gm, np_, pm, kvk, _brawl in rows:
        if to_level < level:
            continue
        if to_level == level and ascended:
            continue
        base = food_so_far if level > to_level - 10 else cumulative_food(rows, to_level - 10)
        out.append({"to": to_level, "food": round(cum_food - base),
                    "gm": gm, "np": np_, "pm": pm, "kvk": kvk})
        food_so_far = cum_food
    return out


def chests_needed(gm, np_, pm, stock):
    """Chests are opened only for the shortfall; stock is spent first."""
    return (math.ceil(max(0, gm - stock["gm"]) / CHEST_YIELD["gm"])
            + math.ceil(max(0, np_ - stock["np"]) / CHEST_YIELD["np"])
            + max(0, pm - stock["pm"]))


def solve(roster, stock, tables):
    """Enumerate every reachable plan. Returns a list of plan dicts."""
    lists = [owed_advances(tables[gen]["advances"], lvl, adv)
             for _name, gen, lvl, adv in roster]
    n, pick, plans = len(lists), [0] * len(lists), []

    def record(food, gm, np_, pm, kvk):
        cg = math.ceil(max(0, gm - stock["gm"]) / CHEST_YIELD["gm"])
        cn = math.ceil(max(0, np_ - stock["np"]) / CHEST_YIELD["np"])
        cp = max(0, pm - stock["pm"])
        plans.append({
            "pick": list(pick), "advances": sum(pick),
            "pets": sum(1 for k in pick if k), "food": food, "kvk": kvk,
            "gm": gm, "np": np_, "pm": pm,
            "chests": cg + cn + cp, "as_manuals": cg, "as_potions": cn, "as_medallions": cp,
            "stranded": (stock["gm"] + cg * CHEST_YIELD["gm"] - gm)
                        + (stock["np"] + cn * CHEST_YIELD["np"] - np_)
                        + (stock["pm"] + cp - pm),
        })

    def walk(i, food, gm, np_, pm, kvk):
        if i == n:
            record(food, gm, np_, pm, kvk)
            return
        f, g, p2, p3, k = food, gm, np_, pm, kvk
        for take in range(len(lists[i]) + 1):
            if take:
                st = lists[i][take - 1]
                f += st["food"]; g += st["gm"]; p2 += st["np"]
                p3 += st["pm"];  k += st["kvk"]
            # Both bounds rise monotonically, so breaking here is safe.
            if f > stock["food"]:
                break
            if chests_needed(g, p2, p3, stock) > stock["chests"]:
                break
            pick[i] = take
            walk(i + 1, f, g, p2, p3, k)
        pick[i] = 0

    walk(0, 0, 0, 0, 0, 0)
    return plans, lists


def describe(plan, roster, lists):
    return ", ".join(f"{roster[i][0]} -> {lists[i][k - 1]['to']}"
                     for i, k in enumerate(plan["pick"]) if k) or "nothing"


def pet_index(tables):
    """Map every pet name to the generation whose cost table it uses."""
    idx = {}
    for gen, spec in tables.items():
        for pet in spec["pets"]:
            idx[pet.lower()] = gen
    return idx


def parse_pet(spec, idx):
    """Parse a --pet argument: 'Name:level' or 'Name:level:ascended'."""
    parts = spec.split(":")
    if len(parts) < 2:
        raise argparse.ArgumentTypeError(
            f"--pet needs at least Name:level, got {spec!r}")
    name = parts[0].strip()
    gen = idx.get(name.lower())
    if gen is None:
        raise argparse.ArgumentTypeError(
            f"unknown pet {name!r}. Run --list-pets to see valid names.")
    try:
        level = int(parts[1])
    except ValueError:
        raise argparse.ArgumentTypeError(f"level must be a number, got {parts[1]!r}")
    ascended = False
    if len(parts) > 2:
        flag = parts[2].strip().lower()
        if flag not in ("yes", "no", "y", "n", "true", "false", "1", "0"):
            raise argparse.ArgumentTypeError(
                f"ascended must be yes or no, got {parts[2]!r}")
        ascended = flag in ("yes", "y", "true", "1")
    return (name, gen, level, ascended)


def main():
    ap = argparse.ArgumentParser(
        prog="solve.py",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Stock defaults come from the STOCK constant near the top of this file; the
roster comes from ROSTER unless overridden with --pet.

examples:
  solve.py                                  solve the built-in roster
  solve.py --chests 400                     what 400 chests would reach
  solve.py --food 500000 --medallions 150   try a different stock
  solve.py --pet "Giant Rhino:81" --pet "Great Moose:60:yes"
                                            replace the roster entirely
  solve.py --list-pets                      valid pet names for --pet
""")

    stock_args = ap.add_argument_group("materials on hand")
    stock_args.add_argument("--food", type=int, default=STOCK["food"], metavar="N",
                            help=f"Pet Food (default: {STOCK['food']:,})")
    stock_args.add_argument("--manuals", "--gm", type=int, default=STOCK["gm"],
                            dest="gm", metavar="N",
                            help=f"Growth Manuals (default: {STOCK['gm']})")
    stock_args.add_argument("--potions", "--np", type=int, default=STOCK["np"],
                            dest="np", metavar="N",
                            help=f"Nutrient Potions (default: {STOCK['np']})")
    stock_args.add_argument("--medallions", "--pm", type=int, default=STOCK["pm"],
                            dest="pm", metavar="N",
                            help=f"Promotion Medallions (default: {STOCK['pm']})")
    stock_args.add_argument("--chests", type=int, default=STOCK["chests"], metavar="N",
                            help=f"Pet Chests, each worth 7 manuals / 2 potions / "
                                 f"1 medallion (default: {STOCK['chests']})")

    roster_args = ap.add_argument_group("roster")
    roster_args.add_argument("--pet", action="append", metavar="NAME:LEVEL[:ASCENDED]",
                             help="replace the built-in roster; repeat per pet. "
                                  "ASCENDED is yes/no and defaults to no — use no for "
                                  "a pet fed to a milestone but not yet ascended, "
                                  "whose Advance then costs no further food.")
    roster_args.add_argument("--list-pets", action="store_true",
                             help="print every valid pet name and exit")

    args = ap.parse_args()
    tables = load_tables()
    idx = pet_index(tables)

    if args.list_pets:
        for gen, spec in tables.items():
            print(f"{spec['label']}  (max level {spec['maxLevel']})")
            for pet in spec["pets"]:
                print(f"    {pet}")
        return

    global ROSTER
    if args.pet:
        try:
            ROSTER = [parse_pet(p, idx) for p in args.pet]
        except argparse.ArgumentTypeError as exc:
            ap.error(str(exc))

    stock = {k: getattr(args, k) for k in ("food", "gm", "np", "pm", "chests")}
    plans, lists = solve(ROSTER, stock, tables)
    plans = [p for p in plans if p["advances"]]
    if not plans:
        print("No Advance is affordable with this stock.")
        return

    print(f"Stock: {stock['food']:,} food | {stock['gm']} manuals | "
          f"{stock['np']} potions | {stock['pm']} medallions | {stock['chests']} chests")
    print(f"{len(plans):,} reachable plans\n")

    # Chests are a stockpile with no competing use, so ties never break toward
    # hoarding them ahead of saving Pet Food, which nothing else can produce.
    objectives = [
        ("Most Advances",           lambda p: (p["advances"], -p["food"], p["kvk"], -p["chests"])),
        ("Without opening a chest", lambda p: (p["chests"] == 0, p["advances"], p["kvk"], -p["food"])),
        ("Most KvK points",         lambda p: (p["kvk"], -p["food"], -p["chests"])),
    ]
    for label, key in objectives:
        best = max(plans, key=key)
        if label.startswith("Without") and best["chests"]:
            print(f"{label}\n   nothing reachable without opening a chest\n")
            continue
        print(f"{label}\n   {describe(best, ROSTER, lists)}")
        adv_word = "Advance" if best["advances"] == 1 else "Advances"
        pet_word = "pet" if best["pets"] == 1 else "pets"
        print(f"   {best['advances']} {adv_word} across {best['pets']} {pet_word} | "
              f"{best['kvk']:,} KvK | {best['food']:,} food")
        print(f"   open {best['chests']} of {stock['chests']} chests: "
              f"{best['as_manuals']} manuals, {best['as_potions']} potions, "
              f"{best['as_medallions']} medallions "
              f"({best['stranded']} materials stranded)\n")

    free = [(name, owed_advances(tables[gen]["advances"], lvl, adv)[0])
            for name, gen, lvl, adv in ROSTER
            if lvl % 10 == 0 and not adv and owed_advances(tables[gen]["advances"], lvl, adv)]
    free = [(n, s) for n, s in free if s["food"] == 0]
    if free:
        print("Zero-food Advances waiting (fed to a milestone, not yet ascended):")
        for name, st in free:
            print(f"   {name} -> {st['to']}: {st['kvk']:,} KvK for "
                  f"{chests_needed(st['gm'], st['np'], st['pm'], stock)} chests, no food")


if __name__ == "__main__":
    # Let `solve.py | head` exit quietly instead of raising BrokenPipeError.
    try:
        signal.signal(signal.SIGPIPE, signal.SIG_DFL)
    except (AttributeError, ValueError):
        pass  # Windows, or not the main thread
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
