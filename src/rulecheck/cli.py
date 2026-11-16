"""Command line entry point.

rulecheck extract --city austin
rulecheck check   --rules data/austin.rules.json --property examples/austin-house.json
"""

import argparse
from pathlib import Path

from dotenv import load_dotenv

from .check import check
from .models import Property, RuleSet, Status

_MARK = {
    Status.SATISFIED: "SATISFIED",
    Status.VIOLATED: "MISSING",
    Status.UNKNOWN: "NEEDS A HUMAN",
}


def _report(findings: list) -> int:
    """Group by the reason rather than listing every rule.

    Austin states the licence requirement in ten separate places. Ten identical
    violations is technically accurate and useless to read, so findings that
    share a cause are collapsed under it.
    """
    counts = {s: 0 for s in Status}
    for f in findings:
        counts[f.status] += 1

    for status in (Status.VIOLATED, Status.UNKNOWN, Status.SATISFIED):
        group = [f for f in findings if f.status is status]
        if not group:
            continue
        print(f"\n{_MARK[status]}  ({len(group)})")
        by_reason: dict[str, list] = {}
        for f in group:
            by_reason.setdefault(f.reason, []).append(f)
        for reason, items in by_reason.items():
            print(f"\n  {reason}")
            for f in items:
                print(f"    {f.rule.section:<10} {f.rule.requirement}")

    print(
        f"\n{len(findings)} rules checked: "
        f"{counts[Status.SATISFIED]} satisfied, "
        f"{counts[Status.VIOLATED]} missing, "
        f"{counts[Status.UNKNOWN]} need a human."
    )
    return 1 if counts[Status.VIOLATED] else 0


def _cmd_check(args) -> int:
    rules = RuleSet.model_validate_json(Path(args.rules).read_text())
    prop = Property.model_validate_json(Path(args.property).read_text())
    return _report(check(rules, prop))


def _cmd_extract(args) -> int:
    from .extract import extract
    from .sources import SOURCES

    load_dotenv()
    names = [args.city] if args.city else list(SOURCES)
    for name in names:
        source = Path("data") / f"{name}.txt"
        rules = extract(SOURCES[name].city, source.read_text())
        out = source.with_suffix(".rules.json")
        out.write_text(rules.model_dump_json(indent=2))
        print(f"{out}  {len(rules.rules)} rules")
    return 0


def _cmd_evaluate(args) -> int:
    from .evaluate import report, score

    load_dotenv()
    scores = score(
        Path(f"eval/{args.city}.key.json"),
        Path(f"data/{args.city}.rules.json"),
        verbose=args.verbose,
    )
    print(report(scores))
    return 0


def _cmd_compare(args) -> int:
    from .canonical import CANONICAL
    from .compare import load, matrix, unmapped

    cities = load()
    table = matrix(cities)
    names = list(cities)

    width = max(len(k) for k in table) + 2
    cols = {
        name: max(len(name), *(len(row[name].threshold) or 3 for row in table.values()))
        + 2
        for name in names
    }
    print(f"{'':<{width}}" + "".join(f"{n:<{cols[n]}}" for n in names))
    for key, row in table.items():
        cells = "".join(
            f"{(row[n].threshold or ('yes' if row[n].present else chr(183))):<{cols[n]}}"
            for n in names
        )
        print(f"{key:<{width}}{cells}")

    print()
    for city, rules in unmapped(cities).items():
        if rules:
            print(f"{city}: {len(rules)} rules outside the canonical set")
    print(f"\n{len(table)} shared requirements across {len(names)} cities.")
    print(
        f"{sum(len(r) for r in cities.values())} rules in total; "
        f"{len(CANONICAL) - 1} canonical entries defined."
    )
    return 0


def _cmd_match(args) -> int:
    from .match import match_file
    from .sources import SOURCES

    load_dotenv()
    names = [args.city] if args.city else list(SOURCES)
    for name in names:
        path = Path("data") / f"{name}.rules.json"
        mapped = match_file(path, SOURCES[name].city)
        print(f"{path}  {mapped} rules mapped to a canonical requirement")
    return 0


def _cmd_fetch(args) -> int:
    from .fetch import fetch
    from .sources import DROP, SOURCES

    names = [args.city] if args.city else list(SOURCES)
    for name in names:
        source = SOURCES[name]
        text = fetch(source, DROP)
        out = Path("data") / f"{name}.txt"
        out.write_text(text)
        print(f"{out}  {len(text):>7,} chars  {source.description}")
    return 0


def _cmd_serve(args) -> int:
    import uvicorn

    uvicorn.run(
        "rulecheck.web:app", host="127.0.0.1", port=args.port, reload=args.reload
    )
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(prog="rulecheck")
    sub = parser.add_subparsers(dest="command", required=True)

    e = sub.add_parser("extract", help="turn an ordinance into rules, using Claude")
    e.add_argument("--city", help="defaults to every known city")
    e.set_defaults(func=_cmd_extract)

    c = sub.add_parser("check", help="check a property against extracted rules")
    c.add_argument("--rules", required=True)
    c.add_argument("--property", required=True)
    c.set_defaults(func=_cmd_check)

    ev = sub.add_parser(
        "evaluate", help="score the extraction against a hand-written key"
    )
    ev.add_argument("--city", default="austin")
    ev.add_argument("--verbose", action="store_true")
    ev.set_defaults(func=_cmd_evaluate)

    cp = sub.add_parser("compare", help="show the cities side by side")
    cp.set_defaults(func=_cmd_compare)

    mp = sub.add_parser("match", help="map each city's rules onto the canonical set")
    mp.add_argument("--city", help="defaults to every known city")
    mp.set_defaults(func=_cmd_match)

    fp = sub.add_parser("fetch", help="download ordinances into data/")
    fp.add_argument("--city", help="defaults to every known city")
    fp.set_defaults(func=_cmd_fetch)

    s = sub.add_parser("serve", help="run the web interface")
    s.add_argument("--port", type=int, default=8000)
    s.add_argument("--reload", action="store_true")
    s.set_defaults(func=_cmd_serve)

    args = parser.parse_args()
    raise SystemExit(args.func(args))
