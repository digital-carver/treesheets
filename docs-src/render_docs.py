#!/usr/bin/env python3
"""Render TreeSheets machine-assisted reference documentation.

Requires Python 3.11+ for tomllib.
"""

from __future__ import annotations

import html
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

if sys.version_info < (3, 11):
    print("render_docs.py requires Python 3.11+", file=sys.stderr)
    raise SystemExit(1)

import tomllib


ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parent
OUT = REPO_ROOT / "TS" / "docs" / "machinegen"

EVIDENCE_LABELS = {
    "code_verified": "Code verified",
    "menu_declared": "Menu declared",
    "docs_supported": "Docs supported",
    "example_supported": "Example supported",
    "inferred_from_code": "Inferred from code",
    "needs_human_check": "Needs human check",
}

SOURCE_TYPES = {"implementation", "menu", "docs", "history", "example", "script", "file_format"}
DOC_SOURCE_TYPES = {"docs", "history", "example", "script", "file_format"}
GENERATED_SOURCE_PREFIXES = ("TS/docs/machinegen/", "docs-src/")
BEHAVIOR_FIELDS = ("summary", "context", "effects", "edge_cases")
ID_RE = re.compile(r"\b(?:A_[A-Z0-9_]+|wxID_[A-Z0-9_]+)\b")

MENU_VAR_PATHS = {
    "filemenu": "File",
    "expmenu": "File > Export view as",
    "impmenu": "File > Import from",
    "editmenu": "Edit",
    "selmenu": "Edit > Selection",
    "orgmenu": "Edit > Grid Reorganization",
    "laymenu": "Edit > Layout & Render Style",
    "imgmenu": "Edit > Images",
    "navmenu": "Edit > Browsing",
    "temenu": "Edit > Text Editing",
    "sizemenu": "Edit > Text Sizing",
    "stmenu": "Edit > Text Style",
    "bordmenu": "Edit > Set Grid Border Width",
    "tagmenu": "Edit > Tag",
    "semenu": "Search",
    "scrollmenu": "View > Scroll Sheet",
    "filtermenu": "View > Filter",
    "viewmenu": "View",
    "roundmenu": "Options > Roundness of grid borders",
    "autoexportmenu": "Options > Autoexport to HTML",
    "optmenu": "Options",
    "scriptmenu": "Script",
    "markmenu": "Program > Mark as",
    "langmenu": "Program",
    "helpmenu": "Help",
}


@dataclass
class Source:
    feature_id: str
    feature_title: str
    index: int
    type: str
    file: str
    lines: str
    label: str
    commit: str | None = None


@dataclass
class MenuItem:
    action_id: str
    label: str
    path: str
    line: int
    documented: bool = False


def load_toml(path: Path) -> dict[str, Any]:
    with path.open("rb") as f:
        return tomllib.load(f)


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def strip_menu_markup(value: str) -> str:
    return value.replace("&", "").replace("&&", "&").strip()


def text_to_paragraphs(text: str) -> str:
    blocks = [block.strip() for block in str(text).strip().split("\n\n") if block.strip()]
    return "\n".join(f"<p>{esc(block)}</p>" for block in blocks)


def read_template(name: str) -> str:
    return (ROOT / "templates" / name).read_text(encoding="utf-8")


def replace(template: str, values: dict[str, str]) -> str:
    result = template
    for key, value in values.items():
        result = result.replace("{{ " + key + " }}", value)
    return result


def page_url(page_id: str) -> str:
    return "index.html" if page_id == "index" else f"{page_id}.html"


def evidence(feature: dict[str, Any]) -> dict[str, Any]:
    return feature.get("evidence") or feature.get("verification") or {}


def source_line_label(source: Source) -> str:
    if "-" in source.lines:
        start, end = source.lines.split("-", 1)
        return f"{source.file}:L{start}-L{end}"
    return f"{source.file}:L{source.lines}"


def source_href(config: dict[str, Any], source: Source) -> str:
    commit = source.commit or config["source_commit"]
    if "-" in source.lines:
        start, end = source.lines.split("-", 1)
        fragment = f"#L{start}-L{end}"
    else:
        fragment = f"#L{source.lines}"
    return f"{config['source_repo']}/blob/{commit}/{source.file}{fragment}"


def command_ids(features: list[dict[str, Any]]) -> set[str]:
    ids: set[str] = set()
    for feature in features:
        for command in feature.get("commands", []):
            ids.update(ID_RE.findall(str(command.get("command_id", ""))))
    return ids


def command_table(feature: dict[str, Any]) -> str:
    commands = feature.get("commands", [])
    if not commands:
        return ""
    rows = []
    for command in commands:
        rows.append(
            "<tr>"
            f"<td>{esc(command.get('name', ''))}</td>"
            f"<td>{esc(command.get('menu_path', ''))}</td>"
            f"<td>{esc(command.get('shortcut', ''))}</td>"
            "</tr>"
        )
    return (
        '<div class="command-block"><div class="block-title">Where to find it</div>'
        "<table><thead><tr><th>Action</th><th>Menu or option</th><th>Shortcut</th>"
        "</tr></thead><tbody>"
        + "\n".join(rows)
        + "</tbody></table></div>"
    )


def behavior_article(feature: dict[str, Any]) -> str:
    behavior = feature.get("behavior", {})
    parts = ['<div class="feature-body">']
    summary = str(behavior.get("summary", "")).strip()
    if summary:
        parts.append(f'<div class="lead">{text_to_paragraphs(summary)}</div>')

    notes = [str(behavior.get(key, "")).strip() for key in BEHAVIOR_FIELDS[1:]]
    notes = [note for note in notes if note]
    if notes:
        parts.append('<ul class="usage-notes">')
        for note in notes:
            parts.append(f"<li>{esc(note)}</li>")
        parts.append("</ul>")

    quirks = str(behavior.get("quirks", "")).strip()
    if quirks:
        parts.append(f'<aside class="callout">{text_to_paragraphs(quirks)}</aside>')
    parts.append("</div>")
    return "\n".join(parts)


def related_links(feature: dict[str, Any], by_id: dict[str, dict[str, Any]]) -> str:
    related = feature.get("related", [])
    if not related:
        return ""
    items = []
    for rid in related:
        target = by_id.get(rid)
        label = target["title"] if target else rid
        href = f"{page_url(target['page'])}#{rid}" if target else "#"
        items.append(f'<li><a href="{esc(href)}">{esc(label)}</a></li>')
    return '<div class="related"><h3>Related</h3><ul>' + "\n".join(items) + "</ul></div>"


def source_refs(feature: dict[str, Any]) -> str:
    sources = feature.get("sources", [])
    if not sources:
        return ""
    refs = [f'<a href="#src-{esc(feature["id"])}-{i}">[{i}]</a>' for i, _ in enumerate(sources, 1)]
    return '<div class="source-refs">Sources: ' + " ".join(refs) + "</div>"


def render_feature(feature: dict[str, Any], by_id: dict[str, dict[str, Any]]) -> str:
    ev = evidence(feature)
    level = ev.get("level", "needs_human_check")
    return replace(
        read_template("feature.html"),
        {
            "id": esc(feature["id"]),
            "title": esc(feature["title"]),
            "evidence_level": esc(level),
            "evidence_label": esc(EVIDENCE_LABELS.get(level, level.replace("_", " ").title())),
            "evidence_text": esc(ev.get("text", "")),
            "command_table": command_table(feature),
            "behavior_sections": behavior_article(feature),
            "related_links": related_links(feature, by_id),
            "source_refs": source_refs(feature),
        },
    )


def collect_sources(features: list[dict[str, Any]]) -> list[Source]:
    collected: list[Source] = []
    for feature in features:
        for i, source in enumerate(feature.get("sources", []), 1):
            collected.append(
                Source(
                    feature_id=feature["id"],
                    feature_title=feature["title"],
                    index=i,
                    type=source.get("type", ""),
                    file=source.get("file", ""),
                    lines=str(source.get("lines", "")),
                    label=source.get("label", ""),
                    commit=source.get("commit"),
                )
            )
    return collected


def footnotes(config: dict[str, Any], features: list[dict[str, Any]]) -> str:
    sources = collect_sources(features)
    if not sources:
        return ""
    items = []
    for source in sources:
        sid = f"src-{source.feature_id}-{source.index}"
        items.append(
            f'<li id="{esc(sid)}">'
            f'<a href="{esc(source_href(config, source))}">{esc(source_line_label(source))}</a>'
            f' - {esc(source.label)}'
            "</li>"
        )
    return '<section class="footnotes"><h2>Sources</h2><ol>' + "\n".join(items) + "</ol></section>"


def nav_html(pages: list[dict[str, Any]], active: str) -> str:
    links = []
    for page in pages:
        cls = ' class="active"' if page["id"] == active else ""
        links.append(f'<a{cls} href="{page_url(page["id"])}">{esc(page["title"])}</a>')
    for page_id, label in (("audit", "Documentation Audit"), ("sources", "Source Index")):
        cls = ' class="active"' if active == page_id else ""
        links.append(f'<a{cls} href="{page_id}.html">{label}</a>')
    return "\n".join(links)


def parse_menu_inventory(documented_ids: set[str]) -> list[MenuItem]:
    path = REPO_ROOT / "src" / "tsframe.h"
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    items: list[MenuItem] = []
    for lineno, line in enumerate(lines, 1):
        if "MyAppend(" not in line and "AppendCheckItem(" not in line and "AppendRadioItem(" not in line:
            continue
        chunk = " ".join(lines[lineno - 1 : min(len(lines), lineno + 6)])
        match = re.search(
            r"(?:MyAppend|AppendCheckItem|AppendRadioItem)\s*\(\s*(?:(\w+)\s*,\s*)?"
            r"((?:A|wxID)_[A-Z0-9_]+)\s*,\s*_\(\"([^\"]+)\"",
            chunk,
        )
        if not match:
            continue
        menu_var, action_id, label = match.groups()
        menu_var = menu_var or ""
        label = strip_menu_markup(label)
        shortcut_match = re.search(r"\\t([^\"]+)", chunk)
        shortcut = f" ({shortcut_match.group(1)})" if shortcut_match else ""
        items.append(
            MenuItem(
                action_id=action_id,
                label=label + shortcut,
                path=MENU_VAR_PATHS.get(menu_var, menu_var or "Menu"),
                line=lineno,
                documented=action_id in documented_ids,
            )
        )
    return items


def menu_reference(config: dict[str, Any], menu_items: list[MenuItem]) -> str:
    grouped: dict[str, list[MenuItem]] = defaultdict(list)
    for item in menu_items:
        grouped[item.path].append(item)
    sections = []
    for path in sorted(grouped):
        rows = []
        for item in grouped[path]:
            source = Source("", "", 1, "menu", "src/tsframe.h", str(item.line), "Menu declaration")
            rows.append(
                "<tr>"
                f"<td>{esc(item.label)}</td>"
                f"<td><a href=\"{esc(source_href(config, source))}\">src/tsframe.h:L{item.line}</a></td>"
                f"<td>{'documented' if item.documented else 'gap'}</td>"
                "</tr>"
            )
        sections.append(
            f"<h2>{esc(path)}</h2><table><thead><tr><th>Menu item</th><th>Declaration</th><th>Status</th>"
            "</tr></thead><tbody>"
            + "\n".join(rows)
            + "</tbody></table>"
        )
    return (
        "<p>This source-derived menu index is generated from TreeSheets menu declarations and is used by "
        "the documentation audit to spot missing coverage.</p>"
        + "\n".join(sections)
    )


def render_page(
    config: dict[str, Any],
    pages: list[dict[str, Any]],
    page: dict[str, Any],
    features: list[dict[str, Any]],
    by_id: dict[str, dict[str, Any]],
    menu_items: list[MenuItem],
) -> str:
    page_features = [feature for feature in features if feature.get("page") == page["id"]]
    if page["id"] == "index":
        by_level = Counter(evidence(f).get("level", "needs_human_check") for f in features)
        pages_list = "\n".join(
            f'<li><a href="{page_url(p["id"])}">{esc(p["title"])}</a> - {esc(p.get("description", ""))}</li>'
            for p in pages
            if p["id"] != "index"
        )
        content = (
            text_to_paragraphs(page.get("intro", ""))
            + f'<div class="audit-grid"><div class="audit-box"><strong>{len(features)}</strong><br>feature sections</div>'
            + f'<div class="audit-box"><strong>{by_level.get("code_verified", 0)}</strong><br>code verified</div>'
            + f'<div class="audit-box"><strong>{esc(config["source_commit"][:12])}</strong><br>source commit</div></div>'
            + "<h2>Pages</h2><ul>"
            + pages_list
            + '<li><a href="audit.html">Documentation Audit</a> - coverage, evidence strength, and missing menu declarations.</li>'
            + '<li><a href="sources.html">Source Index</a> - cited files and line ranges.</li>'
            + "</ul>"
            + "".join(render_feature(feature, by_id) for feature in page_features)
        )
    elif page["id"] == "menus":
        content = text_to_paragraphs(page.get("intro", "")) + menu_reference(config, menu_items)
    else:
        content = text_to_paragraphs(page.get("intro", "")) + "".join(
            render_feature(feature, by_id) for feature in page_features
        )
    content += footnotes(config, page_features)
    return replace(
        read_template("page.html"),
        {
            "page_title": esc(page["title"]),
            "site_title": esc(config["site_title"]),
            "page_description": esc(page.get("description", "")),
            "updated_last_on": esc(config["updated_last_on"]),
            "short_commit": esc(config["source_commit"][:12]),
            "notice": esc(config.get("notice", "")),
            "nav": nav_html(pages, page["id"]),
            "content": content,
        },
    )


def feature_link(feature: dict[str, Any]) -> str:
    return f'<a href="{page_url(feature["page"])}#{esc(feature["id"])}">{esc(feature["title"])}</a>'


def render_audit(
    config: dict[str, Any],
    pages: list[dict[str, Any]],
    features: list[dict[str, Any]],
    menu_items: list[MenuItem],
) -> str:
    sources = collect_sources(features)
    by_level: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for feature in features:
        by_level[evidence(feature).get("level", "needs_human_check")].append(feature)

    by_category = Counter(feature.get("category", "uncategorized") for feature in features)
    documented_menu = sum(1 for item in menu_items if item.documented)
    undocumented = [item for item in menu_items if not item.documented]
    has_impl = {
        source.feature_id
        for source in sources
        if source.type == "implementation" or source.file.startswith("src/")
    }
    has_doc = {
        source.feature_id
        for source in sources
        if source.type in DOC_SOURCE_TYPES or source.file.startswith("TS/docs/") or source.file.startswith("TS/examples/")
    }

    metric_boxes = [
        ("documented features", len(features)),
        ("menu declarations found", len(menu_items)),
        ("documented menu declarations", documented_menu),
        ("undocumented menu declarations", len(undocumented)),
        ("without implementation citation", len(features) - len(has_impl)),
        ("without docs/history/example citation", len(features) - len(has_doc)),
    ]
    metrics = "".join(
        f'<div class="audit-box"><strong>{count}</strong><br>{esc(label)}</div>'
        for label, count in metric_boxes
    )

    level_sections = []
    for level, label in EVIDENCE_LABELS.items():
        links = ", ".join(feature_link(f) for f in by_level.get(level, [])) or "None"
        level_sections.append(f"<h3>{esc(label)}</h3><p>{links}</p>")

    category_rows = "\n".join(
        f"<tr><td>{esc(category)}</td><td>{count}</td></tr>"
        for category, count in sorted(by_category.items())
    )
    undocumented_rows = "\n".join(
        "<tr>"
        f"<td>{esc(item.path)}</td>"
        f"<td>{esc(item.label)}</td>"
        f"<td><a href=\"{esc(source_href(config, Source('', '', 1, 'menu', 'src/tsframe.h', str(item.line), 'Menu declaration')))}\">L{item.line}</a></td>"
        "</tr>"
        for item in undocumented[:120]
    ) or '<tr><td colspan="3">None</td></tr>'

    cited_rows = "\n".join(
        "<tr>"
        f"<td>{feature_link(next(f for f in features if f['id'] == source.feature_id))}</td>"
        f"<td>{esc(source.type)}</td>"
        f"<td><a href=\"{esc(source_href(config, source))}\">{esc(source_line_label(source))}</a></td>"
        f"<td>{esc(source.label)}</td>"
        "</tr>"
        for source in sources
    )
    overrides = [s for s in sources if s.commit]
    override_items = "\n".join(
        f"<li>{esc(s.feature_title)}: <code>{esc(s.file)}</code> L{esc(s.lines)} uses {esc(s.commit)}</li>"
        for s in overrides
    ) or "<li>None</li>"

    thin_pages = [
        page
        for page in pages
        if page["id"] != "menus" and sum(1 for f in features if f.get("page") == page["id"]) < 2
    ]
    thin_items = "\n".join(f"<li>{esc(page['title'])}</li>" for page in thin_pages) or "<li>None</li>"

    likely_gaps = """
    <ul>
      <li>Many File, Options, View, Help, toolbar, and platform-specific commands are inventoried but still need fuller behavior writeups.</li>
      <li>Mouse gestures, drag/drop details, and toolbar dropdown workflows are only partially represented.</li>
      <li>Program evaluator semantics beyond menu markers need deeper user-facing examples.</li>
      <li>Some generated menu labels use platform conditionals, so the audit lists declaration coverage rather than a single guaranteed runtime menu text.</li>
    </ul>
    """

    content = (
        '<div class="audit-grid">' + metrics + "</div>"
        + "<h2>Coverage by Category</h2><table><thead><tr><th>Category</th><th>Features</th></tr></thead><tbody>"
        + category_rows
        + "</tbody></table>"
        + "<h2>Documented Features by Evidence Level</h2>"
        + "\n".join(level_sections)
        + "<h2>Menu Items, Options, and Commands Not Yet Documented</h2>"
        + "<table><thead><tr><th>Menu</th><th>Declaration</th><th>Source</th></tr></thead><tbody>"
        + undocumented_rows
        + "</tbody></table>"
        + "<h2>Cited Files and Ranges</h2><table><thead><tr><th>Feature</th><th>Type</th><th>Range</th><th>Label</th></tr></thead><tbody>"
        + cited_rows
        + "</tbody></table>"
        + "<h2>Non-default Commit Overrides</h2><ul>"
        + override_items
        + "</ul>"
        + "<h2>Likely Gaps</h2>"
        + likely_gaps
        + "<h2>Thin Pages</h2><ul>"
        + thin_items
        + "</ul>"
    )

    return replace(
        read_template("page.html"),
        {
            "page_title": "Documentation Audit",
            "site_title": esc(config["site_title"]),
            "page_description": "Coverage, evidence quality, and missing source-declared behavior.",
            "updated_last_on": esc(config["updated_last_on"]),
            "short_commit": esc(config["source_commit"][:12]),
            "notice": esc(config.get("notice", "")),
            "nav": nav_html(pages, "audit"),
            "content": content,
        },
    )


def render_sources(
    config: dict[str, Any],
    pages: list[dict[str, Any]],
    features: list[dict[str, Any]],
) -> str:
    grouped: dict[str, list[Source]] = defaultdict(list)
    for source in collect_sources(features):
        grouped[source.file].append(source)
    items = []
    for file, file_sources in sorted(grouped.items()):
        links = ", ".join(
            f'<a href="{esc(source_href(config, source))}">L{esc(source.lines)}</a>'
            for source in file_sources
        )
        items.append(f"<li><code>{esc(file)}</code>: {links}</li>")
    content = "<p>Raw citation index for generated documentation.</p><ul>" + "\n".join(items) + "</ul>"
    return replace(
        read_template("page.html"),
        {
            "page_title": "Source Index",
            "site_title": esc(config["site_title"]),
            "page_description": "All cited source files and line ranges.",
            "updated_last_on": esc(config["updated_last_on"]),
            "short_commit": esc(config["source_commit"][:12]),
            "notice": esc(config.get("notice", "")),
            "nav": nav_html(pages, "sources"),
            "content": content,
        },
    )


def validate_config(config: dict[str, Any]) -> list[str]:
    errors = []
    for key in ("site_title", "source_repo", "source_commit", "updated_last_on"):
        if not config.get(key):
            errors.append(f"config.toml missing required key {key!r}")
    if config.get("source_commit") and not re.match(r"^[0-9a-f]{40}$", config["source_commit"]):
        errors.append("config.toml source_commit must be a full 40-character commit hash")
    return errors


def validate_features(features: list[dict[str, Any]], pages: list[dict[str, Any]]) -> list[str]:
    errors = []
    page_ids = {page["id"] for page in pages}
    feature_ids = set()
    line_re = re.compile(r"^\d+(?:-\d+)?$")
    line_counts: dict[str, int] = {}
    for feature in features:
        for key in ("id", "title", "category", "page"):
            if not feature.get(key):
                errors.append(f"{feature.get('id', '<unknown>')}: missing {key}")
        if feature.get("id") in feature_ids:
            errors.append(f"duplicate feature id {feature['id']}")
        feature_ids.add(feature.get("id"))
        if feature.get("page") not in page_ids:
            errors.append(f"{feature.get('id')}: unknown page {feature.get('page')}")
        level = evidence(feature).get("level")
        if level not in EVIDENCE_LABELS:
            errors.append(f"{feature.get('id')}: invalid evidence level {level!r}")
        if not str(feature.get("behavior", {}).get("summary", "")).strip():
            errors.append(f"{feature.get('id')}: missing behavior.summary")
        if not feature.get("sources"):
            errors.append(f"{feature.get('id')}: no sources")
        for source in feature.get("sources", []):
            file = source.get("file", "")
            lines = str(source.get("lines", ""))
            source_type = source.get("type", "")
            if source_type not in SOURCE_TYPES:
                errors.append(f"{feature.get('id')}: invalid source type {source_type!r}")
            if any(file.startswith(prefix) for prefix in GENERATED_SOURCE_PREFIXES):
                errors.append(f"{feature.get('id')}: generated-docs path cannot be evidence: {file}")
            if not file or not (REPO_ROOT / file).exists():
                errors.append(f"{feature.get('id')}: missing source file {file!r}")
            if not line_re.match(lines):
                errors.append(f"{feature.get('id')}: invalid line range {lines!r}")
            else:
                if "-" in lines:
                    start, end = [int(v) for v in lines.split("-", 1)]
                else:
                    start = end = int(lines)
                if start > end:
                    errors.append(f"{feature.get('id')}: invalid descending line range {lines!r}")
                elif file and (REPO_ROOT / file).exists():
                    if file not in line_counts:
                        line_counts[file] = len((REPO_ROOT / file).read_text(encoding="utf-8").splitlines())
                    if end > line_counts[file]:
                        errors.append(
                            f"{feature.get('id')}: line range {lines!r} exceeds {file} line count {line_counts[file]}"
                        )
            if source.get("commit") and not re.match(r"^[0-9a-f]{40}$", source["commit"]):
                errors.append(f"{feature.get('id')}: invalid source commit override")

    for feature in features:
        for rid in feature.get("related", []):
            if rid not in feature_ids:
                errors.append(f"{feature['id']}: related feature {rid!r} does not exist")
    return errors


def main() -> int:
    config = load_toml(ROOT / "config.toml")
    pages = sorted(
        [load_toml(path) for path in (ROOT / "pages").glob("*.toml")],
        key=lambda p: (p.get("order", 1000), p["id"]),
    )
    features = sorted(
        [load_toml(path) for path in (ROOT / "features").glob("*.toml")],
        key=lambda f: (f.get("category", ""), f["title"]),
    )
    by_id = {feature["id"]: feature for feature in features}

    errors = validate_config(config) + validate_features(features, pages)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1

    menu_items = parse_menu_inventory(command_ids(features))

    OUT.mkdir(parents=True, exist_ok=True)
    for page in pages:
        (OUT / page_url(page["id"])).write_text(
            render_page(config, pages, page, features, by_id, menu_items),
            encoding="utf-8",
        )
    (OUT / "audit.html").write_text(render_audit(config, pages, features, menu_items), encoding="utf-8")
    (OUT / "sources.html").write_text(render_sources(config, pages, features), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
