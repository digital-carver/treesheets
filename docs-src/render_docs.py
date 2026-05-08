#!/usr/bin/env python3
"""Render TreeSheets machine-generated reference documentation.

Requires Python 3.11+ for tomllib.
"""

from __future__ import annotations

import html
import re
import sys
from collections import defaultdict
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

VERIFY_LABELS = {
    "implementation_verified": "Implementation verified",
    "ui_verified": "UI verified",
    "docs_history_verified": "Docs/history verified",
    "source_not_found": "Source not found",
    "needs_human_check": "Needs human check",
}

USAGE_NOTE_FIELDS = ["context", "effects", "edge_cases"]


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


def load_toml(path: Path) -> dict[str, Any]:
    with path.open("rb") as f:
        return tomllib.load(f)


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


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
        "<table><thead><tr><th>Action</th><th>Menu</th><th>Shortcut</th>"
        "</tr></thead><tbody>"
        + "\n".join(rows)
        + "</tbody></table></div>"
    )


def behavior_article(feature: dict[str, Any]) -> str:
    behavior = feature.get("behavior", {})
    parts = ['<div class="feature-body">']
    summary = behavior.get("summary", "").strip()
    if summary:
        parts.append(f'<div class="lead">{text_to_paragraphs(summary)}</div>')

    usage_notes = [behavior.get(key, "").strip() for key in USAGE_NOTE_FIELDS]
    usage_notes = [note for note in usage_notes if note]
    if usage_notes:
        parts.append('<ul class="usage-notes">')
        for note in usage_notes:
            parts.append(f"<li>{esc(note)}</li>")
        parts.append("</ul>")

    quirks = behavior.get("quirks", "").strip()
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
    return "<h3>Related</h3><ul>" + "\n".join(items) + "</ul>"


def source_refs(feature: dict[str, Any]) -> str:
    sources = feature.get("sources", [])
    if not sources:
        return ""
    refs = []
    for i, source in enumerate(sources, 1):
        refs.append(f'<a href="#src-{esc(feature["id"])}-{i}">[{i}]</a>')
    return '<div class="source-refs">Sources: ' + " ".join(refs) + "</div>"


def render_feature(feature: dict[str, Any], by_id: dict[str, dict[str, Any]]) -> str:
    verification = feature.get("verification", {})
    level = verification.get("level", "needs_human_check")
    return replace(
        read_template("feature.html"),
        {
            "id": esc(feature["id"]),
            "title": esc(feature["title"]),
            "verification_level": esc(level),
            "verification_label": esc(VERIFY_LABELS.get(level, level.replace("_", " ").title())),
            "verification_text": esc(verification.get("text", "")),
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
    cls = ' class="active"' if active == "sources" else ""
    links.append(f'<a{cls} href="sources.html">Source Audit</a>')
    return "\n".join(links)


def render_page(
    config: dict[str, Any],
    pages: list[dict[str, Any]],
    page: dict[str, Any],
    features: list[dict[str, Any]],
    by_id: dict[str, dict[str, Any]],
) -> str:
    page_features = [feature for feature in features if feature.get("page") == page["id"]]
    if page["id"] == "index":
        feature_count = len(features)
        implementation_count = sum(
            1
            for f in features
            if f.get("verification", {}).get("level") == "implementation_verified"
        )
        pages_list = "\n".join(
            f'<li><a href="{page_url(p["id"])}">{esc(p["title"])}</a> - {esc(p.get("description", ""))}</li>'
            for p in pages
            if p["id"] != "index"
        )
        content = (
            text_to_paragraphs(page.get("intro", ""))
            + f'<div class="audit-grid"><div class="audit-box"><strong>{feature_count}</strong><br>feature sections</div>'
            + f'<div class="audit-box"><strong>{implementation_count}</strong><br>implementation verified</div>'
            + f'<div class="audit-box"><strong>{esc(config["source_commit"][:12])}</strong><br>source commit</div></div>'
            + "<h2>Pages</h2><ul>"
            + pages_list
            + '<li><a href="sources.html">Source Audit</a> - cited files, verification status, and override checks.</li>'
            + "</ul>"
            + "".join(render_feature(feature, by_id) for feature in page_features)
        )
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


def render_audit(
    config: dict[str, Any],
    pages: list[dict[str, Any]],
    features: list[dict[str, Any]],
) -> str:
    sources = collect_sources(features)
    by_level: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for feature in features:
        by_level[feature.get("verification", {}).get("level", "needs_human_check")].append(feature)

    cited = defaultdict(list)
    for source in sources:
        cited[source.file].append(source)

    cited_items = []
    for file, file_sources in sorted(cited.items()):
        ranges = ", ".join(
            f'<a href="{esc(source_href(config, source))}">L{esc(source.lines)}</a>'
            for source in file_sources
        )
        cited_items.append(f"<li><code>{esc(file)}</code>: {ranges}</li>")

    level_boxes = []
    for level in VERIFY_LABELS:
        items = by_level.get(level, [])
        links = ", ".join(
            f'<a href="{page_url(f["page"])}#{esc(f["id"])}">{esc(f["title"])}</a>' for f in items
        ) or "None"
        level_boxes.append(
            f'<div class="audit-box"><h2>{esc(VERIFY_LABELS[level])}</h2><p>{links}</p></div>'
        )

    lacking = [
        f
        for f in features
        if f.get("verification", {}).get("level") != "implementation_verified"
    ]
    lacking_items = "\n".join(
        f'<li><a href="{page_url(f["page"])}#{esc(f["id"])}">{esc(f["title"])}</a></li>'
        for f in lacking
    ) or "<li>None</li>"

    overrides = [s for s in sources if s.commit]
    override_items = "\n".join(
        f"<li>{esc(s.feature_title)}: <code>{esc(s.file)}</code> L{esc(s.lines)} uses {esc(s.commit)}</li>"
        for s in overrides
    ) or "<li>None</li>"

    content = (
        '<div class="audit-grid">'
        + "\n".join(level_boxes)
        + "</div>"
        + "<h2>Cited Files and Ranges</h2><ul>"
        + "\n".join(cited_items)
        + "</ul>"
        + "<h2>Features Lacking Implementation Verification</h2><ul>"
        + lacking_items
        + "</ul>"
        + "<h2>Non-default Commit Overrides</h2><ul>"
        + override_items
        + "</ul>"
    )

    return replace(
        read_template("page.html"),
        {
            "page_title": "Source Audit",
            "site_title": esc(config["site_title"]),
            "page_description": "Cited source ranges, verification coverage, and citation override checks.",
            "updated_last_on": esc(config["updated_last_on"]),
            "short_commit": esc(config["source_commit"][:12]),
            "notice": esc(config.get("notice", "")),
            "nav": nav_html(pages, "sources"),
            "content": content,
        },
    )


def validate_sources(features: list[dict[str, Any]]) -> list[str]:
    errors = []
    line_re = re.compile(r"^\d+(?:-\d+)?$")
    for feature in features:
        for source in feature.get("sources", []):
            file = source.get("file")
            lines = str(source.get("lines", ""))
            if not file or not (REPO_ROOT / file).exists():
                errors.append(f"{feature['id']}: missing source file {file!r}")
            if not line_re.match(lines):
                errors.append(f"{feature['id']}: invalid line range {lines!r}")
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

    errors = validate_sources(features)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1

    OUT.mkdir(parents=True, exist_ok=True)
    for page in pages:
        (OUT / page_url(page["id"])).write_text(
            render_page(config, pages, page, features, by_id),
            encoding="utf-8",
        )
    (OUT / "sources.html").write_text(render_audit(config, pages, features), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
