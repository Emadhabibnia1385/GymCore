---
name: nasim
description: How to build and review any NYXON dashboard screen with @nyxon/nasim (libs/nasim), the shared app UI library on HeroUI 3 and React Aria - Persian-first, right to left, light and dark, product palettes. Use before writing or reviewing a screen, a form, a table, a state, a theme change or a new Nasim part, in apps/paynyx/web or any future dashboard. Not for the marketing sites, which have their own scenes.
---

# Building with Nasim

`libs/nasim/README.md` is the contract: every part, its props and an example. This skill is the order
of work and the checks; open the README section of each part you use before you call its props right
or wrong.

## The rules (README «Rules»)

1. Screens import UI from `@nyxon/nasim` only. HeroUI and React Aria are imported inside
   `libs/nasim` and nowhere else; `bun run check` fails otherwise.
2. A screen passes its own copy as props, from its own strings module. No Latin text in JSX, no
   literal `aria-label`, `placeholder`, `title` or `alt`.
3. Colours, radii and fonts come from tokens (`bg-surface`, `text-muted`, `border-border`,
   `bg-accent`). No hex values and no `dark:` utilities in an app: the tokens switch with the theme.
4. Logical layout (`ms-*`, `pe-*`, `text-start`); safe-area insets are physical (`px-safe`,
   `px-page`). Direction-bound icons get `rtl:rotate-180`; ids, links and card numbers get
   `dir="ltr"` and `font-mono`.
5. One theme controller, `NasimProvider`. A product's colours arrive as its `palette`
   (README «A product's own palette»); `checkPalette` proves every text and fill pair before it ships.
6. Variants with `tv()`; never a long class string in a screen.

## Which part for which job

| Job | Part |
| --- | --- |
| The app frame, navigation, the bottom bar | `AppShell`, `NavTabs`, `useBottomBar` |
| A page title and its back control | `PageHeader` |
| A list | `DataTable` with `Pager`; `cards` turns rows into cards on a phone |
| A small fixed table | `StaticTable` |
| One record's fields | `KeyValueList` inside a `SectionCard` |
| A figure or a trend | `StatCard`, `ColumnChart`, `BarTable` (every value also as text) |
| A status | `StatusChip` with words, never colour alone |
| Waiting, nothing, failure | `PageSkeleton` / `TableSkeleton`, `EmptyState`, `ErrorState` |
| A form | `FormRoot` with the `*Field` parts and `SubmitButton` (it blocks a second submit) |
| A destructive action | `ConfirmDialog` |
| A secret or an id to copy | `CopyField`, `CopyButton` |
| A notice on the page | `Notice`, `MessageBar` |
| A sheet on a phone | `BottomSheet` |

## Adding to Nasim

Add a part only when it is generic: the next dashboard would use it as it is. A part that only one
product understands is composed from Nasim parts inside that product's feature. A new part comes
with its tests (`libs/nasim/__tests__`, contrast and accessibility where they apply), a README
section with an example, and a CHANGELOG entry with a version bump.

Before you write a part, search, never memory: the `heroui-react` MCP (`list_components`,
`get_component_docs`, `get_component_source_code`) for the current API of HeroUI 3 (`npm view
@heroui/react version` says whether Nasim's pin is still the newest; an upgrade moves `@heroui/react` and
`@heroui/styles` together and runs every test), and the `heroui-pro` MCP (`HEROUI_PERSONAL_TOKEN`) or
heroui.pro's component pages for the layout and interaction to learn from. Follow its structure where it
fits a Persian, right-to-left screen; cite what you followed in the CHANGELOG entry.

Nasim has two consumers: the apps of this workspace (`workspace:*`) and Seamless, which keeps a pinned
copy (README «In a Vite app: Seamless»). A part Seamless needs is built here like any other, merged, and
then synced there.

## Mechanical checks for a review

```bash
changed() { git diff --name-only --diff-filter=d origin/main...HEAD -- '*.ts' '*.tsx'; }
changed | grep -v '^libs/nasim/' | xargs -r rg -n "from ['\"](@heroui/|react-aria)"   # rule 1 (check.ts too)
changed | grep -v '^libs/nasim/' | xargs -r rg -n "#[0-9a-fA-F]{3,8}\b|\bdark:"       # rule 3
changed | xargs -r rg -n "\b(ml|mr|pl|pr)-[0-9]|\b(left|right)-[0-9]|text-(left|right)" # rule 4
changed | xargs -r rg -n "aria-label=\"|placeholder=\"|title=\"|alt=\""                # rule 2
changed | xargs -r rg -n "<form\b|type=\"submit\""                                       # a form not on FormRoot
```

A hit is a lead, not a finding: open the line.

## Verify

`bun run check` (Nasim's and the app's tests), then the screen itself at 390 and 1280 px, light and
dark, with its empty, loading and error states; a Telegram Mini App screen at 390 px inside the
Mini App frame too. Browser scripts stay out of the repository.
