# TreeSheets Documentation Generation Agent Instructions

This document defines persistent instructions for future documentation-generation agents working on this TreeSheets repository.

## Mission

Create and maintain detailed, source-cited TreeSheets documentation from repository source code, existing docs, `history.txt`, tutorial files, examples, menu definitions, command handlers, and scripting references.

Treat the existing tutorial as a quick getting-started page, **not** as the full documentation. The generated documentation should be a proper reference manual.

## Documentation Architecture

- Use `docs-src/` as the source directory for generated documentation inputs.
- Use `TS/docs/machinegen/` as the generated HTML output directory.
- Use TOML feature manifests as the structured source of truth.
- Use a Python renderer script, `docs-src/render_docs.py`, to convert TOML manifests to static HTML.
- The renderer must use Python’s built-in `tomllib`, so it must require Python 3.11+.
- If `docs-src/render_docs.py` does not exist, create it.
- Do **not** manually hand-write final HTML pages except templates. Update TOML manifests and templates, then run the renderer.

Suggested structure:

```text
docs-src/
  config.toml
  features/
    *.toml
  pages/
    *.toml
  templates/
    page.html
    feature.html
  render_docs.py

TS/
  docs/
    machinegen/
      index.html
      editing.html
      selection.html
      grids.html
      scripting.html
      sources.html
```

## Required Config

`docs-src/config.toml` must contain at least:

```toml
site_title = "TreeSheets Reference"
source_repo = "https://github.com/<OWNER>/<REPO>"
source_commit = "<COMMIT_HASH>"
updated_last_on = "YYYY-MM-DD"
```

Use a docs-wide `source_commit` instead of repeating commit hashes in every source citation.

Source citations in feature manifests should store file paths and line ranges only. The renderer should expand them into GitHub blob links:

```text
{source_repo}/blob/{source_commit}/{file}#L{start}-L{end}
```

Allow an optional per-source `commit` override only when a citation deliberately points to a different commit.

## Feature Manifest Format

Each feature manifest should be TOML and include fields like:

```toml
id = "selection-current-grid"
title = "Select the current grid"
category = "selection"
page = "selection"

[[commands]]
name = "Select current grid"
menu_path = "Edit > ..."
shortcut = "Ctrl+A"
command_id = ""

[verification]
level = "implementation_verified"
text = "Verified from menu definition and command implementation."

[[sources]]
type = "ui"
file = "src/..."
lines = "123-145"
label = "Menu entry or shortcut definition."

[[sources]]
type = "implementation"
file = "src/..."
lines = "456-510"
label = "Command handler implementation."

[behavior]
summary = """
Describe what the feature does.
"""

context = """
Describe selection/edit-mode/view requirements.
"""

effects = """
Describe what changes in the document, view, selection, or edit state.
"""

edge_cases = """
Describe no-op behavior, special cases, or ambiguity.
"""

quirks = """
Describe known confusing behavior, misleading docs, platform differences, or historical notes.
"""
```

Feature documentation should document behavior, not only menu labels.

For each feature, try to trace:

```text
menu label / shortcut → command ID → event handler → implementation behavior
```

Document:

- menu path, if any
- shortcut, if any
- command ID / handler, if found
- behavior
- selection/context requirements
- effects on document, view, selection, cursor, edit mode, styles, or grid structure
- edge cases and no-op behavior
- related commands
- known quirks
- source citations

Do not invent behavior. If source evidence is incomplete, mark it clearly.

## Verification Levels

- `implementation_verified`: UI/menu/shortcut and implementation traced.
- `ui_verified`: UI/menu/shortcut found, implementation not fully traced.
- `docs_history_verified`: existing docs or history or tutorial only.
- `source_not_found`: behavior mentioned but source not yet located.
- `needs_human_check`: likely behavior or ambiguous behavior that requires manual testing or maintainer confirmation.

Generated HTML should show a small dark-mode-friendly verification badge near each feature heading.

Use muted colors:

- muted green for `implementation_verified`
- muted teal/blue for `ui_verified`
- muted amber/brown for `docs_history_verified`
- muted grey/violet for `source_not_found` or `needs_human_check`

## Page Metadata and Notice

Each generated page should include faded metadata such as:

```text
Updated last on YYYY-MM-DD · Source commit abc1234
```

Each generated page should also include a short faded notice near the metadata:

```text
AI-generated reference docs. Reliability indicators and footnote citations are included with every section.
```

## Visual Design Target

- Generate documentation with a dark-mode-first visual design.
- Use dark backgrounds, readable text, subdued borders, and muted accent colors.
- Avoid bright warning colors unless something is genuinely dangerous, destructive, or data-loss related.

## Required Outputs

The renderer should generate:

- normal documentation pages
- a source audit page at `TS/docs/machinegen/sources.html`

The source audit page should list:

- all cited files and line ranges
- features grouped by verification level
- features lacking implementation verification
- sources that use non-default commit overrides

The generated HTML should include source footnotes or source reference links near the relevant section text. A source reference should link to the footnote, and the footnote should link to the exact GitHub file and line range.

Example rendered source link target:

```html
<li id="src-selection-current-grid-1">
  <a href="https://github.com/<OWNER>/<REPO>/blob/<COMMIT>/TS/docs/history.txt#L229-L230">
    TS/docs/history.txt:L229-L230
  </a>
  — History entry for Ctrl+A behavior.
</li>
```

Prefer exact line ranges. Do not cite a whole file if a line range can be found.

## Documentation Priorities

- Core concepts: cells, grids, subgrids, selections, views
- Text edit mode
- Selection behavior
- Grid creation and navigation
- Menu commands and shortcuts
- Layout: text size, column width, zoom, F12 scaling mode
- Styling and colors
- Import/export
- Scripting/Lobster integration
- Known quirks and misleading existing docs

Existing docs such as `tutorial.html` and `history.txt` may be cited, but they should not be treated as automatically authoritative when behavior can be traced in implementation code. Prefer implementation evidence where possible.

## Process Constraint

Do not directly edit generated HTML pages in docs. Editing the  shared templates in docs-src is allowed.
If generated output is incorrect, or if there are issues while trying to generate it, fix the TOML manifests, renderer, or templates and regenerate the documentation cleanly.