"""A small web front end over the same checker the CLI uses.

There is no logic here. The form is turned into a Property, the Property goes
through check(), and the findings are rendered. If the page and the CLI ever
disagree, one of them is calling the wrong function.
"""

import json
import re
from pathlib import Path

from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse

from .canonical import CANONICAL
from .check import check
from .compare import load, matrix, unmapped
from .models import Blocked, Finding, Property, RuleSet, Status

app = FastAPI(title="rulecheck")

DATA = Path("data")

STYLE = """
:root {
  --bg:#fcfcfb; --panel:#ffffff; --fg:#17171a; --muted:#6e6e76; --faint:#a3a3ab;
  --line:#e6e6e2; --accent:#1c4f8f; --bad:#a8291f; --ok:#1d6b43; --idk:#8a6a16;
  --radius:12px;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --bg:#121214; --panel:#191920; --fg:#ececef; --muted:#9a9aa4; --faint:#6a6a74;
    --line:#2a2a33; --accent:#89b4f0; --bad:#e8857c; --ok:#6fcf9a; --idk:#e0bd63;
  }
}
* { box-sizing:border-box }
body { margin:0; background:var(--bg); color:var(--fg);
  font:16px/1.6 ui-sans-serif,-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;
  -webkit-font-smoothing:antialiased }
.wrap { max-width:1000px; margin:0 auto; padding:56px 28px 120px }
code, .mono { font-family:ui-monospace,SFMono-Regular,"SF Mono",Menlo,monospace }

header { margin-bottom:8px }
h1 { font-size:30px; margin:0; letter-spacing:-.025em; font-weight:650 }
.tagline { color:var(--muted); margin:6px 0 0; font-size:17px; max-width:62ch }

nav { display:flex; gap:26px; margin:30px 0 36px; border-bottom:1px solid var(--line) }
nav a { text-decoration:none; color:var(--muted); padding:0 0 12px; font-size:15px;
  border-bottom:2px solid transparent; margin-bottom:-1px }
nav a:hover { color:var(--fg) }
nav a.on { color:var(--fg); border-bottom-color:var(--fg); font-weight:550 }

h2 { font-size:15px; text-transform:uppercase; letter-spacing:.07em; color:var(--muted);
  font-weight:550; margin:44px 0 14px }
h2:first-of-type { margin-top:0 }
p.lead { color:var(--muted); max-width:70ch; margin:0 0 26px }

.panel { background:var(--panel); border:1px solid var(--line); border-radius:var(--radius) }

form.panel { padding:24px 24px 8px; margin-bottom:34px }
.row { display:flex; gap:18px; flex-wrap:wrap }
.field { flex:1 1 190px; margin-bottom:18px }
label { display:block; font-size:12px; letter-spacing:.04em; text-transform:uppercase;
  color:var(--faint); margin-bottom:7px }
select, input { width:100%; padding:10px 12px; border:1px solid var(--line); border-radius:8px;
  font-size:15px; background:var(--bg); color:var(--fg); font-family:inherit }
select:focus, input:focus { outline:2px solid var(--accent); outline-offset:-1px; border-color:transparent }
button { background:var(--fg); color:var(--bg); border:0; border-radius:8px; padding:11px 24px;
  font-size:15px; font-weight:550; cursor:pointer; font-family:inherit }
button:hover { opacity:.88 }

.counts { display:flex; gap:12px; margin:0 0 34px; flex-wrap:wrap }
.count { flex:1 1 160px; background:var(--panel); border:1px solid var(--line);
  border-radius:var(--radius); padding:16px 18px }
.count b { display:block; font-size:28px; letter-spacing:-.03em; font-variant-numeric:tabular-nums }
.count span { font-size:13px; color:var(--muted) }
.field.wide { flex:1 1 100%; max-width:380px }
.field.submit { flex:0 0 auto; display:flex; align-items:flex-end; margin-bottom:18px }
.unit { color:var(--faint); text-transform:none; letter-spacing:0 }
.hint { color:var(--faint); font-size:13px; margin:4px 0 16px }
.verdict { font-size:19px; line-height:1.55; margin:0 0 34px; max-width:62ch }
.verdict b { font-weight:600; display:block; margin-bottom:4px }
.cause { background:var(--panel); border:1px solid var(--line); border-left:3px solid var(--line);
  border-radius:10px; padding:16px 20px; margin-bottom:10px }
.cause.violated { border-left-color:var(--bad) }
.cause.satisfied { border-left-color:var(--ok) }
.cause.unknown { border-left-color:var(--idk) }
.cause-head { display:flex; justify-content:space-between; align-items:baseline; gap:16px }
.cause-title { font-size:16px; font-weight:550 }
.cause-count { color:var(--faint); font-size:13px; white-space:nowrap }
.cause details { border:0; padding:0; margin:10px 0 0 }
.cause summary { font-size:13px }
.cause .rule { margin-top:10px }
.verdict i { font-style:normal; font-weight:550 }
details.rest { margin-top:34px }
details.rest > summary { font-size:14px; color:var(--muted) }
details.rest h2 { margin:30px 0 12px }
.count.bad b { color:var(--bad) } .count.ok b { color:var(--ok) } .count.idk b { color:var(--idk) }

.group { margin-bottom:30px }
.reason { font-size:12px; text-transform:uppercase; letter-spacing:.06em; color:var(--muted);
  margin:0 0 12px; padding-bottom:8px; border-bottom:1px solid var(--line) }
.rule { background:var(--panel); border:1px solid var(--line); border-left:3px solid var(--line);
  border-radius:8px; padding:14px 18px; margin-bottom:9px }
.rule.violated { border-left-color:var(--bad) }
.rule.satisfied { border-left-color:var(--ok) }
.rule.unknown { border-left-color:var(--idk) }
.sec { font-size:11px; color:var(--faint); letter-spacing:.04em }
.quote { margin:9px 0 0; padding-left:14px; border-left:2px solid var(--line);
  color:var(--muted); font-size:14px; font-style:italic }

.scroll { overflow-x:auto; border:1px solid var(--line); border-radius:var(--radius);
  background:var(--panel) }
table { border-collapse:collapse; width:100%; font-size:14px; min-width:720px }
th, td { text-align:left; padding:12px 14px; border-bottom:1px solid var(--line) }
tr:last-child td { border-bottom:0 }
thead th { font-size:11px; text-transform:uppercase; letter-spacing:.07em; color:var(--faint);
  font-weight:550; background:var(--bg) }
td.req { font-family:ui-monospace,SFMono-Regular,Menlo,monospace; font-size:12px;
  white-space:nowrap; color:var(--fg) }
td.val { font-variant-numeric:tabular-nums; white-space:nowrap }
.yes { color:var(--ok); font-weight:550 } .no { color:var(--faint) }

details { margin-top:28px; border-top:1px solid var(--line); padding-top:18px }
summary { cursor:pointer; color:var(--muted); font-size:14px; list-style:none }
summary::-webkit-details-marker { display:none }
summary::before { content:"+ "; color:var(--faint) }
details[open] summary::before { content:"\2212 " }
details ul { color:var(--muted); font-size:14px; line-height:1.7; margin-top:14px }

pre { margin:0; padding:22px; overflow-x:auto; font-size:13px; line-height:1.65;
  font-family:ui-monospace,SFMono-Regular,Menlo,monospace }
.k { color:var(--accent) } .s { color:var(--ok) } .n { color:var(--bad) } .p { color:var(--faint) }

dl { margin:0 }
dt { font-family:ui-monospace,SFMono-Regular,Menlo,monospace; font-size:12.5px;
  color:var(--fg); margin-top:16px }
dt:first-child { margin-top:0 }
dd { margin:3px 0 0; color:var(--muted); font-size:14px }
.pad { padding:24px }

footer { margin-top:70px; padding-top:22px; border-top:1px solid var(--line);
  color:var(--faint); font-size:13px }
footer a { color:var(--muted) }
"""


def _page(body: str, active: str) -> HTMLResponse:
    tabs = {
        "/": "Check a property",
        "/compare": "Compare cities",
        "/schema": "The model",
    }
    nav = "".join(
        f"<a href='{href}' class='{'on' if href == active else ''}'>{label}</a>"
        for href, label in tabs.items()
    )
    return HTMLResponse(
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<title>rulecheck</title>"
        f"<style>{STYLE}</style></head><body><div class='wrap'>"
        "<header><h1>rulecheck</h1>"
        "<p class='tagline'>Five cities write their short-term rental rules five different "
        "ways. A model reads each ordinance once; everything after that is ordinary code.</p>"
        "</header>"
        f"<nav>{nav}</nav>"
        f"{body}"
        "<footer>Ordinances are public documents, downloaded unedited and quoted in place. "
        "Nothing here is legal advice.</footer>"
        "</div></body></html>"
    )


CITY_NAMES = {
    "austin": "Austin, Texas",
    "denver": "Denver, Colorado",
    "nashville": "Nashville, Tennessee",
    "new-orleans": "New Orleans, Louisiana",
    "san-diego": "San Diego, California",
}

# Each question is phrased the way the ordinance asks it, not the way the
# database stores it. "owner_occupies" means nothing to someone with a spare
# room to rent; "Do you live in this property yourself?" does.
QUESTIONS = [
    ("has_license", "Do you already hold a rental licence or permit?"),
    ("owner_owns", "Do you own this property?"),
    ("owner_occupies", "Do you live in it yourself?"),
    ("has_insurance", "Do you carry liability insurance on it?"),
    ("registered_for_tax", "Are you registered to collect lodging tax?"),
]

NUMBERS = [
    ("units_operated", "How many rentals do you run?", "units", "e.g. 1"),
    (
        "feet_to_nearest_rental",
        "Distance to your nearest other rental",
        "feet",
        "e.g. 1400",
    ),
]


def _cities() -> list[str]:
    return sorted(p.name.replace(".rules.json", "") for p in DATA.glob("*.rules.json"))


def _label(city: str) -> str:
    return CITY_NAMES.get(city, city.replace("-", " ").title())


def _bool_field(name: str, label: str, value: str = "") -> str:
    def sel(v: str) -> str:
        return " selected" if value == v else ""

    return (
        f"<div class='field'><label for='{name}'>{label}</label>"
        f"<select id='{name}' name='{name}'>"
        f"<option value=''{sel('')}>Not sure yet</option>"
        f"<option value='yes'{sel('yes')}>Yes</option>"
        f"<option value='no'{sel('no')}>No</option>"
        f"</select></div>"
    )


def _form(city: str = "", form: dict | None = None) -> str:
    f = form or {}
    options = "".join(
        f"<option value='{c}'{' selected' if c == city else ''}>{_label(c)}</option>"
        for c in _cities()
    )
    booleans = "".join(_bool_field(n, q, f.get(n, "")) for n, q in QUESTIONS)
    numbers = "".join(
        f"<div class='field'><label for='{n}'>{q} <span class='unit'>({u})</span></label>"
        f"<input id='{n}' name='{n}' type='number' min='0' placeholder='{ph}' "
        f"value='{f.get(n, '')}'></div>"
        for n, q, u, ph in NUMBERS
    )
    return f"""
    <form class="panel" method="post" action="/check">
      <div class="field wide"><label for="city">Which city is the property in?</label>
        <select id="city" name="city">{options}</select></div>
      <div class="row">{booleans}</div>
      <div class="row">{numbers}
        <div class="field submit"><button>Check the rules</button></div>
      </div>
      <p class="hint">Leave anything you are unsure about on <b>Not sure yet</b>.
      Unanswered is treated as unanswered, never as a breach.</p>
    </form>"""


def _tri(value: str | None) -> bool | None:
    return {"yes": True, "no": False}.get(value or "")


# Austin states the licence requirement in twelve separate places. Twelve
# identical rows is accurate and unreadable, so the page groups by the fact
# that decided them and shows the rules themselves only on request.
CAUSES = {
    ("violated", "license"): "You do not have a licence or permit",
    ("violated", "ownership"): "You do not own the property",
    ("violated", "owner_occupancy"): "You do not live in the property",
    ("violated", "insurance"): "You do not carry the required insurance",
    ("violated", "tax"): "You are not registered for lodging tax",
    ("violated", "unit_cap"): "You run more rentals than this city allows",
    ("violated", "distance"): "Your rentals are closer together than allowed",
    ("unknown", "license"): "You did not answer the licence question",
    ("unknown", "ownership"): "You did not answer the ownership question",
    ("unknown", "owner_occupancy"): "You did not answer whether you live there",
    ("unknown", "insurance"): "You did not answer the insurance question",
    ("unknown", "tax"): "You did not answer the tax question",
    (
        "unknown",
        "unit_cap",
    ): "This city measures its limit in a way the checker cannot apply",
    ("unknown", "distance"): "You did not give a distance to your nearest rental",
    ("unknown", "other"): "Noise, upkeep and local contact rules",
}


def _cause(finding: Finding) -> str:
    key = (finding.status.value, finding.rule.kind)
    if key in CAUSES:
        return CAUSES[key]
    return (
        "Already satisfied" if finding.status is Status.SATISFIED else "Needs a person"
    )


def _causes(findings: list[Finding]) -> dict[str, list[Finding]]:
    out: dict[str, list[Finding]] = {}
    for f in findings:
        out.setdefault(_cause(f), []).append(f)
    return dict(sorted(out.items(), key=lambda kv: -len(kv[1])))


def _verdict(findings: list[Finding], city: str) -> str:
    """Lead with the blockers, by name, and say nothing else.

    An earlier version opened with three sentences of arithmetic. Someone with a
    spare room does not want a census of the ordinance, they want to know what is
    standing in their way, so the headline names it and the counting moves to the
    bottom of the page where it belongs.
    """
    bad = [f for f in findings if f.status is Status.VIOLATED]
    if not bad:
        return (
            f"<p class='verdict'><b>Nothing you told us breaks a rule in {city}.</b>"
            "</p>"
        )

    causes = list(_causes(bad))
    if len(causes) == 1:
        detail = f"One thing is in the way: <i>{causes[0].lower()}</i>."
    else:
        listed = ", ".join(c.lower() for c in causes[:-1])
        detail = f"{len(causes)} things are in the way: <i>{listed}</i>, and <i>{causes[-1].lower()}</i>."
    return f"<p class='verdict'><b>You cannot rent this in {city} yet.</b>{detail}</p>"


def _block(title: str, items: list[Finding], status: Status) -> str:
    rules = "".join(
        f"<div class='rule {status.value}'><div>{f.rule.requirement}</div>"
        f"<div class='sec'>{f.rule.section}</div>"
        + (
            f"<p class='quote'>{f.rule.quote.strip()[:220]}</p>"
            if status is Status.VIOLATED
            else ""
        )
        + "</div>"
        for f in items
    )
    n = len(items)
    word = "rule" if n == 1 else "rules"
    return (
        f"<div class='cause {status.value}'>"
        f"<div class='cause-head'><span class='cause-title'>{title}</span>"
        f"<span class='cause-count'>{n} {word} in the ordinance</span></div>"
        f"<details><summary>Show the {word}</summary>{rules}</details>"
        "</div>"
    )


def _rest(findings: list[Finding]) -> str:
    """Everything that is not a blocker, folded away behind one line."""
    groups = [
        (
            "waiting on an answer you have not given",
            [f for f in findings if f.blocked_on is Blocked.ANSWER],
            Status.UNKNOWN,
        ),
        (
            "left to a person, because no program can decide them",
            [f for f in findings if f.blocked_on is Blocked.HUMAN],
            Status.UNKNOWN,
        ),
        (
            "already met",
            [f for f in findings if f.status is Status.SATISFIED],
            Status.SATISFIED,
        ),
    ]
    groups = [(label, items, status) for label, items, status in groups if items]
    if not groups:
        return ""

    total = sum(len(items) for _, items, _ in groups)
    summary = "; ".join(f"{len(items)} {label}" for label, items, _ in groups)
    body = "".join(
        f"<h2>{label[0].upper() + label[1:]}</h2>"
        + "".join(
            _block(title, rules, status) for title, rules in _causes(items).items()
        )
        for label, items, status in groups
    )
    return (
        f"<details class='rest'><summary>The other {total} rules: {summary}.</summary>"
        f"{body}</details>"
    )


def _render(findings: list[Finding], city: str) -> str:
    bad = [f for f in findings if f.status is Status.VIOLATED]
    blockers = "".join(
        _block(title, items, Status.VIOLATED) for title, items in _causes(bad).items()
    )
    return _verdict(findings, city) + blockers + _rest(findings)


@app.get("/compare", response_class=HTMLResponse)
def compare_page() -> HTMLResponse:
    cities = load(DATA)
    table = matrix(cities)
    names = list(cities)

    head = "".join(f"<th>{n.replace('-', ' ').title()}</th>" for n in names)
    rows = ""
    for key, row in table.items():
        cells = ""
        for name in names:
            cell = row[name]
            if cell.threshold:
                body = f"<span class='val'>{cell.threshold}</span>"
            elif cell.present:
                body = "<span class='yes'>yes</span>"
            else:
                body = "<span class='no'>&middot;</span>"
            cells += f"<td class='val'>{body}</td>"
        rows += f"<tr><td class='req' title='{CANONICAL[key]}'>{key}</td>{cells}</tr>"

    left = unmapped(cities)
    extra = "".join(
        f"<li><b>{city.replace('-', ' ').title()}</b> &mdash; "
        + "; ".join(r.requirement.rstrip(".") for r in rules[:5])
        + "</li>"
        for city, rules in left.items()
        if rules
    )
    total = sum(len(r) for r in cities.values())

    return _page(
        "<h2>Where the cities agree, and where they do not</h2>"
        "<p class='lead'>Every row is one obligation, expressed in whatever words that city "
        "chose. A number is the threshold attached to it; <span class='yes'>yes</span> means "
        "the requirement exists with no number on it. Hover a row to see what the shared "
        "requirement means.</p>"
        f"<div class='scroll'><table><thead><tr><th>Requirement</th>{head}</tr>"
        f"</thead><tbody>{rows}</tbody></table></div>"
        f"<details><summary>{sum(len(r) for r in left.values())} of {total} rules did not fit "
        "any shared requirement. They are kept, not quietly dropped.</summary>"
        f"<ul>{extra}</ul></details>",
        "/compare",
    )


@app.get("/", response_class=HTMLResponse)
def index() -> HTMLResponse:
    cities = _cities()
    return _page(
        "<h2>Check one property</h2>"
        "<p class='lead'>Answer what you know and leave the rest alone. An unanswered "
        "question is reported as unanswered, never as a breach: the point of this is to "
        "separate what the ordinance forbids from what nobody has told it yet.</p>"
        + _form(cities[0] if cities else ""),
        "/",
    )


def _highlight(raw: str) -> str:
    """Enough colour to read a schema, not a syntax highlighter."""
    out = raw.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    out = re.sub(
        r'("(?:[^"\\]|\\.)*")(\s*:)',
        r"<span class='k'>\1</span><span class='p'>\2</span>",
        out,
    )
    out = re.sub(r'(:\s*)("(?:[^"\\]|\\.)*")', r"\1<span class='s'>\2</span>", out)
    out = re.sub(r"\b(true|false|null|\d+)\b", r"<span class='n'>\1</span>", out)
    return out


@app.get("/schema", response_class=HTMLResponse)
def schema_page() -> HTMLResponse:
    from .extract import _schema

    shape = _schema()["properties"]["rules"]["items"]
    # Pydantic adds a title to every field and the canonical enum is listed in
    # full further down the page. Both are noise here.
    for field in shape["properties"].values():
        field.pop("title", None)
    shape["properties"]["canonical_id"] = {
        "description": "One of the shared requirements listed below, or null before matching.",
        "type": ["string", "null"],
    }
    shape.pop("title", None)
    shape = json.dumps(shape, indent=2)

    entries = "".join(
        f"<dt>{key}</dt><dd>{text}</dd>"
        for key, text in CANONICAL.items()
        if key != "UNMAPPED"
    )

    return _page(
        "<h2>Two passes, two different jobs</h2>"
        "<p class='lead'>Reading an ordinance and comparing it to four others are separate "
        "problems, so they are separate steps. Splitting them means a mistake in one can be "
        "told apart from a mistake in the other, which is the only way to measure either.</p>"
        "<h2>Pass one &middot; the shape of an answer</h2>"
        "<p class='lead'>This schema is handed to the model as a tool it is required to call. "
        "It is not a suggestion in a prompt: the enumerated field cannot take a value outside "
        "the list, and the quote is mandatory, so no requirement can be recorded without the "
        "sentence it came from.</p>"
        f"<div class='panel'><pre>{_highlight(shape)}</pre></div>"
        "<h2>Pass two &middot; the shared vocabulary</h2>"
        "<p class='lead'>A second pass assigns every extracted rule to one of these. Austin "
        "writes <i>operator&rsquo;s license</i>, New Orleans writes <i>permit</i>, San Diego "
        "writes <i>short-term residential occupancy licence</i>. The list is fixed on purpose. "
        "A requirement that genuinely does not fit is marked unmapped and shown separately, "
        "because a canonical model that bends to every source is just the sources again.</p>"
        f"<div class='panel pad'><dl>{entries}</dl></div>",
        "/schema",
    )


@app.post("/check", response_class=HTMLResponse)
def run_check(
    city: str = Form(...),
    has_license: str = Form(""),
    owner_owns: str = Form(""),
    owner_occupies: str = Form(""),
    has_insurance: str = Form(""),
    registered_for_tax: str = Form(""),
    units_operated: str = Form(""),
    feet_to_nearest_rental: str = Form(""),
) -> HTMLResponse:
    rules = RuleSet.model_validate_json((DATA / f"{city}.rules.json").read_text())
    prop = Property(
        city=city,
        has_license=_tri(has_license),
        owner_owns=_tri(owner_owns),
        owner_occupies=_tri(owner_occupies),
        has_insurance=_tri(has_insurance),
        registered_for_tax=_tri(registered_for_tax),
        units_operated=int(units_operated) if units_operated.strip() else None,
        feet_to_nearest_rental=float(feet_to_nearest_rental)
        if feet_to_nearest_rental.strip()
        else None,
    )
    submitted = {
        "has_license": has_license,
        "owner_owns": owner_owns,
        "owner_occupies": owner_occupies,
        "has_insurance": has_insurance,
        "registered_for_tax": registered_for_tax,
        "units_operated": units_operated,
        "feet": feet_to_nearest_rental,
    }
    return _page(
        f"<h2>{_label(city)}</h2>"
        + _form(city, submitted)
        + _render(check(rules, prop), _label(city)),
        "/",
    )
