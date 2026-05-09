# TreeSheets Documentation Generation Agent Instructions

This document defines persistent instructions for future documentation-generation agents working on this TreeSheets repository.

## Mission

Create and maintain detailed, source-cited, machine-assisted TreeSheets documentation from:

- repository source code
- existing docs
- `history.txt`
- tutorial files
- examples
- menu definitions
- option definitions
- command handlers
- scripting references
- in-repo sample files

Treat the existing official tutorial as a quick getting-started page, not as the full documentation. The generated documentation should become a practical reference manual for TreeSheets users.

The documentation should aim for broad, honest coverage. Do not document only features whose implementation has been fully traced. When evidence is weaker, document the feature with a weaker evidence label instead of omitting it entirely.

## Target Audience

Write for a smart technical user of TreeSheets, not primarily for a TreeSheets source-code contributor.

Assume the reader is comfortable with:

- precise UI concepts
- menus and shortcuts
- selection states
- edit modes
- cells, grids, subgrids, and views
- scripting concepts
- file formats
- careful distinctions between similar commands

Do not assume the reader wants to understand the C++ codebase.

Use implementation code as evidence for user-visible behavior, not as normal explanatory text.

Avoid raw internal variable names, enum names, command IDs, constants, and implementation formulas in user-facing prose unless they directly explain a visible behavior, bug, limitation, or scripting/API detail.

If internal identifiers are useful for auditability, keep them in source labels, documentation audit pages, or compact developer notes rather than the main explanation.

## Documentation Architecture

Use this architecture:

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
      layout.html
      menus.html
      scripting.html
      audit.html
      sources.html   # optional raw source index
```

Rules:

* Use `docs-src/` as the source directory for generated documentation inputs.
* Use `TS/docs/machinegen/` as the generated HTML output directory.
* Use TOML feature manifests as the structured source of truth.
* Use a Python renderer script, `docs-src/render_docs.py`, to convert TOML manifests to static HTML.
* The renderer must use Python’s built-in `tomllib`; require Python 3.11+.
* If `docs-src/render_docs.py` does not exist, create it.
* Do not directly hand-write final generated HTML pages except templates.
* Update TOML manifests, templates, and renderer code, then regenerate HTML.
* If generated output is incorrect, fix the TOML manifests, renderer, or templates and regenerate cleanly.
* Do not patch generated HTML directly.

## Required Config

`docs-src/config.toml` must contain at least:

```toml
site_title = "TreeSheets Reference"
source_repo = "https://github.com/<OWNER>/<REPO>"
source_commit = "<COMMIT_HASH>"
updated_last_on = "YYYY-MM-DD"
```

Use the current repository `HEAD` commit as `source_commit` unless instructed otherwise.

Use a docs-wide `source_commit` instead of repeating commit hashes in every source citation.

Source citations in feature manifests should store file paths and line ranges only. The renderer should expand them into GitHub blob links:

```text
{source_repo}/blob/{source_commit}/{file}#L{start}-L{end}
```

Allow an optional per-source `commit` override only when a citation deliberately points to a different commit.

## Visual Design Target

Generate documentation with a dark-mode-first visual design.

Design expectations:

* dark background
* readable text
* subdued borders
* muted accent colors
* comfortable contrast, not harsh high-contrast mode
* no light/dark toggle for now
* no bright warning colors unless something is genuinely dangerous, destructive, or data-loss related

Every generated page should include faded metadata such as:

```text
Updated last on YYYY-MM-DD · Source commit abc1234
```

Every generated page should also include a short faded notice near the metadata:

```text
Machine-assisted reference docs. Reliability indicators and footnote citations are included with every section.
```

## Evidence Model

Do not think of evidence as all-or-nothing. Use the best evidence available and label its strength honestly.

Evidence levels:

* `code_verified`: behavior traced to implementation code.
* `menu_declared`: menu label, shortcut, option, or command declaration found in source, but implementation behavior not fully traced.
* `docs_supported`: behavior supported by existing documentation, tutorial, history, scripting reference, or generated reference file.
* `example_supported`: behavior demonstrated by in-repo examples.
* `inferred_from_code`: behavior inferred from nearby code structure, naming, dispatch flow, or data flow, but not fully traced.
* `needs_human_check`: likely or ambiguous behavior that requires manual testing, maintainer confirmation, or deeper source inspection.

Generated HTML should show a small dark-mode-friendly evidence badge near each feature heading.

Use muted colors:

* muted green for `code_verified`
* muted teal/blue for `menu_declared`
* muted amber/brown for `docs_supported` or `example_supported`
* muted grey/violet for `inferred_from_code` or `needs_human_check`

Do not use `ui_verified` as a label. The agent does not have access to the live GUI unless a later task explicitly provides screenshots or manual observations. Menu declarations in source should be labelled `menu_declared`, not `ui_verified`.

## Use of Existing Docs and History

Existing docs such as `tutorial.html`, `history.txt`, scripting references, and in-repo examples are first-class evidence sources.

Use them actively to improve coverage, especially for:

* terminology
* user-visible workflows
* shortcuts
* menu behavior
* historical behavior changes
* platform-specific notes
* known quirks
* scripting behavior
* examples of intended use

When implementation code is also available, prefer it for exact behavior.

When only docs/history/examples are available, still document the feature, but mark the evidence level honestly.

Do not let “prefer implementation evidence” turn into “ignore docs/history.” The goal is useful coverage with visible evidence quality, not sparse implementation-only documentation.

## Source Boundaries

When gathering evidence about TreeSheets behavior, do not treat generated documentation as source evidence.

Ignore these paths as evidence sources:

- `TS/docs/machinegen/`
- `docs-src/`

These directories are documentation-generation artifacts and outputs, not authoritative information about TreeSheets behavior.

Use `docs-src/` only to read or update documentation manifests, templates, renderer code, and config.

Use `TS/docs/machinegen/` only as generated output. Do not mine it for facts, and do not let previous generated documentation propagate into new documentation as evidence.

Authoritative evidence should come from:

- TreeSheets source code outside generated-docs machinery
- existing official docs and tutorial files outside `TS/docs/machinegen/`
- `history.txt`
- scripting references
- in-repo examples
- menu/option/command declarations
- implementation code

## Feature Manifest Format

Each feature manifest should be TOML. The format may evolve, but it should support at least the following kind of information:

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

[evidence]
level = "docs_supported"
text = "Supported by history documentation describing Ctrl+A behavior."

[[sources]]
type = "history"
file = "TS/docs/history.txt"
lines = "123-125"
label = "History entry describing Ctrl+A selection behavior."

[[sources]]
type = "implementation"
file = "src/..."
lines = "456-510"
label = "Command handler implementation."

[behavior]
summary = """
Describe what the feature does in user-facing terms.
"""

context = """
Describe selection, edit-mode, view, or option requirements.
"""

effects = """
Describe what changes in the document, view, selection, cursor, edit mode, styles, or grid structure.
"""

edge_cases = """
Describe no-op behavior, special cases, ambiguity, or surprising context-specific behavior.
"""

quirks = """
Describe confusing behavior, misleading existing docs, platform differences, rendering issues, or historical notes.
"""
```

Feature documentation should document behavior, not only menu labels.

The TOML manifest structure is an authoring aid. Do not mechanically expose it as the HTML reading structure.

In particular, do not render `[behavior].summary`, `[behavior].context`, `[behavior].effects`, `[behavior].edge_cases`, and `[behavior].quirks` as repeated visible subheadings for every feature.

Render each feature as readable user-facing documentation:

* Start with practical behavior in plain prose.
* Mention context requirements only when they matter to using the feature.
* Mention effects and edge cases near the behavior they affect.
* Use a note/callout only for genuinely surprising quirks, misleading existing docs, platform differences, destructive behavior, data-loss risk, or likely user confusion.
* Omit empty, redundant, or unimportant fields from visible output.
* Use bullets or tables when they improve clarity.
* Make the page read like a manual, not a schema dump.

## User-Facing Prose Rules

Explain what the user can do and what they will observe.

Prefer this style:

> Text edit mode lets you change the text content of a cell. Press `Enter` to start editing with the existing text selected, or press `F2` to start editing with the cursor at the end of the text.

Avoid this style:

> Text edit mode turns a single cell selection into an insertion cursor or text range.

Avoid source-code lifecycle language such as:

* “sets paint-scroll flag”
* “updates cursor position fields”
* “dispatches command ID”
* “stores value as action minus constant”
* “refreshes canvas state”

Translate those details into visible behavior:

* “TreeSheets shows a text cursor and lets you edit the selected cell.”
* “The command exits text edit mode and moves the selection according to the current navigation option.”
* “This option changes whether cursor-key navigation stops on grid lines between cells.”

If a behavior depends on another option, link to that option’s documentation section.

Examples:

* If `Enter`/`F2` exits text edit mode and the subsequent movement depends on `Options > Navigate in between cells with cursor keys`, mention and link that option.
* If a rendering mode such as F12 affects grid line visibility, describe the visible rendering effect, not only the internal scaling flag.
* If a command ID is required for tracing, cite it in a source label or developer note, not in the main prose.

## Source Tracing

For each feature, try to trace:

```text
menu label / shortcut / option declaration → command ID → event handler → implementation behavior
```

But do not require full tracing before documenting anything. If a feature is visible in menu declarations or existing docs but implementation tracing is incomplete, document it with an appropriate evidence level.

Document these when available:

* menu path
* option path
* shortcut
* practical behavior
* selection/context requirements
* effects on document, view, selection, cursor, edit mode, styles, or grid structure
* edge cases and no-op behavior
* related commands/options
* known quirks
* source citations

Trace command IDs and handlers for source verification, but do not normally show them in user-facing documentation.

Do not invent behavior. If evidence is incomplete, mark it clearly with the evidence level and wording.

## Citations

The generated HTML should include source footnotes or source reference links near each feature section.

A source reference should link to a footnote, and the footnote should link to the exact GitHub file and line range.

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

Feature-level citations are acceptable. Do not introduce a more complex paragraph-level citation schema unless a later task explicitly asks for it.

Keep source links close to the relevant feature. The documentation audit page is not a substitute for citations in normal documentation.

## Documentation Audit

Generate a documentation audit page at:

```text
TS/docs/machinegen/audit.html
```

The audit page is not user documentation. It is a review and maintenance tool for improving the generated docs.

The documentation audit page should show:

* documentation coverage by menu/category
* menu items, shortcuts, options, or command declarations found but not yet documented
* documented features grouped by evidence level
* features backed by implementation code
* features backed only by docs/history/examples
* features inferred from code but not fully traced
* features that need human checking
* cited files and line ranges
* sources that use non-default commit overrides
* likely gaps in the generated reference
* pages or categories that are thin and need expansion

If possible, include counts such as:

* total menu items found
* documented menu items
* undocumented menu items
* total documented features
* features by evidence level
* features with no implementation citation
* features with no docs/history citation

Optionally also generate:

```text
TS/docs/machinegen/sources.html
```

as a raw source index. But the primary review page should be `audit.html`.

## Coverage Expectations

Build an inventory of menus, menu items, shortcuts, options, and command declarations found in the source.

Document as many of them as possible.

Do not restrict documentation only to features whose implementation was fully traced.

Prefer broad, honest coverage over sparse implementation-only coverage.

For each major menu/category page, include useful user-facing content even if some features are only `menu_declared` or `docs_supported`.

If a section is thin because evidence is incomplete, mark it clearly in the documentation audit and continue.

The first-pass documentation should prioritize:

* Core concepts: cells, grids, subgrids, selections, views
* Text edit mode
* Selection behavior
* Grid creation and navigation
* Menu commands and shortcuts
* Options menu
* Layout: text size, column width, zoom, F12 scaling mode
* Styling and colors
* Import/export
* Scripting/Lobster integration
* Known quirks and misleading existing docs

## Suggested Page Structure

The generated reference may use pages like:

* `index.html` — overview and navigation
* `concepts.html` — cells, grids, subgrids, views, selections
* `editing.html` — text edit mode, typing, Enter/F2, paste, undo/redo
* `selection.html` — selecting cells, grids, Ctrl+A, boundary selection, movement
* `grids.html` — creating, deleting, nesting, flattening, hierarchify, hierarchy swap
* `layout.html` — zoom, text size, column width, F12 scaling, rendering quirks
* `menus.html` — menu and shortcut reference
* `scripting.html` — Lobster scripting and TreeSheets scripting APIs
* `audit.html` — documentation audit and coverage report
* `sources.html` — optional raw source index

This is not mandatory, but generated docs should be organized for users, not for source-file structure.

## Renderer Requirements

`docs-src/render_docs.py` should:

* read `docs-src/config.toml`
* read TOML feature manifests
* read page definitions if present
* validate required fields
* expand source links using `source_repo`, `source_commit`, file path, and line range
* support optional per-source commit overrides
* generate dark-mode-first HTML
* generate evidence badges
* generate source footnotes/source references
* generate `audit.html`
* optionally generate `sources.html`
* fail loudly on malformed TOML, missing required fields, invalid source references, or broken internal links

The renderer should not require third-party dependencies in the first pass.

Use only the Python standard library unless there is a strong reason to add a dependency.

## Process Constraint

Do not directly edit generated HTML pages in `TS/docs/machinegen/`.

Editing shared templates in `docs-src/templates/` is allowed.

If generated output is incorrect, fix one or more of:

* TOML manifests
* page definitions
* renderer
* templates

Then regenerate documentation cleanly.

The generated HTML should be reproducible from `docs-src/`.

## Quality Checklist

Before finishing a documentation-generation task, check:

* Generated pages exist under `TS/docs/machinegen/`.
* `source_commit` matches current `HEAD`.
* The renderer runs cleanly.
* Pages use dark-mode-first styling.
* Pages include updated date and source commit metadata.
* Pages include the machine-assisted docs notice.
* Feature sections have evidence badges.
* Feature sections have source references.
* User-facing prose does not read like implementation notes.
* Internal command IDs and implementation variable names are not exposed in normal prose.
* Behavior/context/effects/edge cases/quirks are not rendered as repeated boilerplate subheadings.
* Major menus/options are covered or listed as gaps in `audit.html`.
* `audit.html` shows coverage and evidence quality, not only a raw list of sources.
* Generated docs were not used as source evidence for new generated docs.
