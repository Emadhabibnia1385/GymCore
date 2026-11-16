# «نسیم» (Nasim) design system

Version 0.10.0 (see [CHANGELOG.md](./CHANGELOG.md)).

`@nyxon/nasim` is one set of building blocks for every NYXON dashboard (PAYNYX's web dashboard and
Telegram Mini App first): Persian first, right to left, light and dark, with the Telegram safe areas
and a tenant accent. It is a thin layer over HeroUI 3.2.7 (React Aria Components + Tailwind v4),
written for the Next.js App Router. The demo page (see [Setup](#setup)) shows every piece in both
themes.

## Rules

1. Import from `@nyxon/nasim`. Only this package imports `@heroui/react` or `react-aria-components`
   (`tools/check.ts` enforces it); an app lists `@heroui/styles` for its stylesheet only (see Setup).
2. Nasim's own words (what a close button or a retry button says) live in `src/strings/`. Every
   screen passes its own copy to the components as props, from its own strings module. No Latin text
   in JSX and no literal `aria-label`, `placeholder`, `title` or `alt` in a screen.
3. Colours, radii and fonts come from tokens (`bg-surface`, `text-muted`, `border-border`,
   `bg-accent`, `rounded-field`). No hex values in feature code, and no `dark:` utilities: the
   tokens already switch with the theme.
4. Logical properties for layout (`ms-*`, `pe-*`, `text-start`, `inset-inline-*`). The exception is
   the safe-area insets, which are physical (a notch is on the left or the right of the screen, not
   at the start or the end): use `px-safe`, `px-page` or `pl-*`/`pr-*`, never `ps-*`/`pe-*`.
   Direction-bound icons get `rtl:rotate-180`. Technical values (ids, links, addresses) get
   `dir="ltr"` and `font-mono`.
5. One theme controller: the one in `NasimProvider`. Never call HeroUI's own `useTheme`.
6. Variants are written with `tv()` from `tailwind-variants`, never as long class strings in a
   screen.

## Setup

In a Next.js App Router app (webpack, like the other NYXON apps). The package exports TypeScript
source, so there is no build step, but the app compiles it:

```ts
// next.config.ts
const nextConfig: NextConfig = {
  transpilePackages: ['@nyxon/nasim'],
};
```

The app lists `@nyxon/nasim` (`workspace:*`), `@heroui/styles` (the same version as Nasim's, 3.2.7),
`tailwindcss` and `@tailwindcss/postcss` in its own `package.json`. `@heroui/styles` is there only
because a stylesheet `@import` is resolved from the app's own `node_modules`; the app never imports
`@heroui/react`.

The tree must hold one copy each of `react-aria`, `react-stately` and `react-aria-components`: HeroUI
reads its hooks from the first and Nasim's `I18nProvider` comes from the third, and every copy has its own
locale context, so with two the date picker's month and year button and its year list would ignore the
Persian locale. Bun installs a package once per peer set and lets the copies drift apart, so this
workspace pins them in the root `package.json` `overrides` to the set Nasim's own `react-aria-components`
pin brings (`react-aria` 3.53.1, `react-stately` 3.51.0, `react-aria-components` 1.22.1, the set HeroUI 3.2.7
asks for). This set was refused once with HeroUI 3.2.6: a modal closed by a finished request stayed on screen in
the e2e suite. With 3.2.7 the onboarding journey and the team screen pass, and so does the rest of the PAYNYX web e2e
suite but its first-load budget for `/pay`, which `main` was already over. Move all three together and run the e2e suite; `calendarLocale.test.tsx` fails when they split.

The stylesheet loads the system in this order. Tailwind v4 skips `node_modules`, and the workspace
link to Nasim lives there, so `@source` points at the real folder (the path is relative to this
file; this one is `apps/paynyx/web/src/app/globals.css`):

```css
@import 'tailwindcss';
@import '@heroui/styles';
@import '@nyxon/nasim/tokens.css';
@import '@nyxon/nasim/fonts.css';
@source '../../../../../libs/nasim/src';
```

`<html>` is `lang="fa" dir="rtl"` and carries the font variable (see
[Digits and fonts](#digits-and-fonts)); it also needs `suppressHydrationWarning`, because the theme
controller sets its class and `data-theme` after hydration:

```tsx
// app/layout.tsx
<html lang="fa" dir="rtl" className={vazirmatn.variable} suppressHydrationWarning>
  <body>
    <Providers>{children}</Providers>
  </body>
</html>
```

Wrap the app once, in a client component, and hand the provider the router's `push` and `replace`.
The functions must be stable (`useCallback`): React Aria rebuilds every link when they change.

```tsx
// app/providers.tsx
'use client';

import { NasimProvider, type NasimNavigateOptions } from '@nyxon/nasim';
import { useRouter } from 'next/navigation';
import { type ReactNode, useCallback } from 'react';

export function Providers({ children }: { children: ReactNode }) {
  const router = useRouter();
  const navigate = useCallback((href: string, options?: NasimNavigateOptions) => (options?.replace ? router.replace(href, { scroll: options.scroll }) : router.push(href, { scroll: options?.scroll })), [router]);
  return (
    <NasimProvider navigate={navigate} defaultMode={inTelegram ? 'telegram' : 'system'} accent={tenant.accent}>
      {children}
    </NasimProvider>
  );
}
```

The demo page is two lines; keep it out of production:

```tsx
// app/nasim/page.tsx
import { NasimDemo } from '@nyxon/nasim/demo';
import { notFound } from 'next/navigation';

export default function Page() {
  if (process.env.NODE_ENV === 'production') notFound();
  return <NasimDemo />;
}
```

### In a Vite app: Seamless

Seamless (`Emadhabibnia1385/Seamless_bot`, a Vite SPA, a separate repository) keeps an unedited copy of
this package in `web_frontend/vendor/nasim`, a Bun workspace named `@nyxon/nasim`, taken from a commit of
this repository by its `bun run nasim:sync <nyxon checkout>` and proved by `bun run check:nasim` (the
tree hash and the pins in `vendor/nasim.lock.json`). So a change Seamless needs is made here, with its
test, README section and CHANGELOG entry, merged, then synced there; never in the copy. What a Vite app
does instead of the Next setup above: no `transpilePackages`, `@source` pointing at the vendored `src`,
its own `@font-face` rules, and `navigate`/`useHref` built from its router. `'use client'` is ignored.

### Server and client

Every module that holds state, effects, context or an event handler starts with `'use client'`, and
nothing reads `window`, `document` or `localStorage` while a component renders. A Server Component
may import from `@nyxon/nasim` and render the presentational parts with plain props: `KeyValueList`,
`Stepper`, `Cover`, `LoadingState`, `EmptyState` (with an `href` action), `StatusChip`, `TrendChip`, `StatCard`,
`Sparkline`, `Kbd`, `SectionCard`, `Collapsible`, `StaticTable`, `ColumnChart`, `BarTable` and the skeletons, the colour helpers
(`readableAccents`, `accentRatios`, `parseHex`, `toHex`, `oklchToRgb`, `contrastRatio`, `SCHEMES`,
`MIN_UI`, `MIN_TEXT`), the palette helpers (`paletteCss`, `checkPalette`, `paletteSchemes`) and the
theme cookie helpers (`THEME_COOKIE`, `parseThemeMode`). Everything else is a client component: render it from a Server Component with props
that serialize (no functions), or inside a client component. A Server Component cannot dot into a
client module, so compound primitives (`Card.Header`, `Select.Trigger`) belong in client components.

On the server React Aria cannot reach the Persian dictionary described below (it reads it from
`window`), so the labels it words itself are English in the server HTML, and React does not patch an
attribute that differs on hydration. Nasim names the ones its own components own (the number field's
steppers, the search box's clear button, the select placeholder, spinners, close buttons and the toast
region) with its Persian strings, so they are Persian from the first byte. A primitive that has such a label of its own
(`ColorPicker`'s colour name) needs an explicit `aria-label`, or a client-only render.

The theme is applied to `<html>` after hydration, so with Nasim's own `tokens.css` alone a dark device
in the `"system"` mode paints the first frame light. A product that hands over a `palette` does not have
this: the stylesheet it renders carries a `prefers-color-scheme: dark` rule, and a saved light or dark
choice is on `<html>` from the server's first byte (see [A product's own palette](#a-products-own-palette)
and [The saved choice, for the server](#the-saved-choice-for-the-server)).

`NasimProvider` gives you, in one place:

- `I18nProvider locale="fa-IR"`: Persian numerals, Jalali calendars, RTL.
- React Aria's own strings in Persian ("Close", "Loading", "Dismiss" and the rest). React Aria has
  no override API, so the strings are installed through its global dictionary when this module
  loads (in the browser only), built from the complete en-US dictionary with the Persian keys laid
  over it. A test fails if the install breaks.
- `navigate`: with the host router's push, `LinkButton`, `Link` and menu items navigate without a
  page load. Without it they are plain links. An address with a scheme or a `//host` (Telegram, a
  phone number) is never handed to the router.
- The theme controller, the tenant accent and font, and the toast region.

Its props are typed as `NasimProviderProps`; `NasimNavigate` and `NasimNavigateOptions`
(`{ replace?: boolean; scroll?: boolean }`, what `routerOptions` on a `Link` or `LinkButton` carries) are
exported too:

| Prop            | Type                                          | Notes                                                                                                                                                         |
| --------------- | --------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `palette`       | `Palette`                                     | The product's own colours and radius, rendered as a stylesheet on the server too (see [A product's own palette](#a-products-own-palette)).                    |
| `initialMode`   | `ThemeMode`                                   | The saved choice as the server read it from the cookie; `parseThemeMode` makes it (see [The saved choice, for the server](#the-saved-choice-for-the-server)). |
| `navigate`      | `NasimNavigate`                               | Optional. `(href, options?) => void`: the host router's push or replace. Enables in-app link navigation. Keep it stable.                                      |
| `useHref`       | `(href: string) => string`                    | Optional. The address a link shows, for a router with a base path; may be a hook. It is called for every link and ignored for an external address.            |
| `defaultMode`   | `"system" \| "light" \| "dark" \| "telegram"` | Used until the person picks one. Default `"system"`.                                                                                                          |
| `nativeBack`    | `boolean`                                     | The host app has its own back button (Telegram's BackButton): `PageHeader` then draws no back arrow. Default `false`.                                         |
| `persist`       | `boolean`                                     | Save the choice in `localStorage` (default `true`). `false` inside Telegram, where the website's saved choice must not win.                                   |
| `initialScheme` | `"light" \| "dark"`                           | The external scheme when it is known at the first render (Telegram's launch theme), so the first paint and the first colours sent to the host are right.      |
| `accent`        | `string` (`#rrggbb`)                          | The reseller's brand colour. Optional.                                                                                                                        |
| `font`          | `string`                                      | The reseller's font: an id with a rule in `fonts.css`. Optional; none (or `vazirmatn`) leaves the page in Vazirmatn.                                          |

### `useTheme`, `ThemeMode`, `ColorScheme`

```tsx
const { mode, setMode, scheme, setScheme } = useTheme();
```

| Field             | Meaning                                                                                                                                                                     |
| ----------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `mode`            | `ThemeMode`: `"system"`, `"light"`, `"dark"` or `"telegram"`.                                                                                                               |
| `setMode`         | Changes the mode and, unless `persist` is off, remembers it in `localStorage` and in the cookie `nasim-theme`; choosing the `defaultMode` forgets the saved choice instead. |
| `scheme`          | `ColorScheme` (`"light"` or `"dark"`): what is applied to `<html>` right now.                                                                                               |
| `setScheme`       | Feeds the external scheme that `"telegram"` mode follows. Ignored in other modes.                                                                                           |
| `automatic`       | The mode that follows the host: `"telegram"` where the app starts in it, else `"system"`.                                                                                   |
| `automaticScheme` | The scheme `automatic` shows right now: Telegram's fed scheme or the device's.                                                                                              |

The controller writes `class` and `data-theme` on `<html>` and nothing else. It does not import
Telegram: the app feeds `setScheme` from the one place that talks to the Mini Apps SDK. In
`"telegram"` mode with nothing fed yet it follows the device. The saved choice is read after
hydration, so the first client render agrees with the server's.

```tsx
import { useTelegramColorScheme } from '@/lib/telegram';

function TelegramTheme() {
  const { setScheme } = useTheme();
  const scheme = useTelegramColorScheme(); // follows Telegram's theme live, null outside it
  useLayoutEffect(() => {
    if (scheme) setScheme(scheme); // before the first paint, so there is no flash
  }, [scheme, setScheme]);
  return null;
}
```

Render `TelegramTheme` inside `NasimProvider` and start with `defaultMode="telegram"`,
`persist={false}` and `initialScheme` set to the same Telegram scheme (it is known synchronously at
launch), so the first render is already in it. A theme picker is three or four buttons calling `setMode` (see the demo).

### `useOverlayStack`, `useRegisterOverlay`

Open dialogs and sheets form a stack, so something outside them can close "the top layer" without
knowing which screen opened what: Telegram's BackButton closes the top sheet before it navigates
back. `BottomSheet` and `ConfirmDialog` register themselves while they are open (a dialog whose
action is still running ignores the request, as it does for Escape).

```tsx
const { count, closeTop } = useOverlayStack(); // count of open layers; closeTop() is false when none

useRegisterOverlay(isOpen, () => setOpen(false)); // for a layer of your own
```

### `usePageHeading`

The title of the page on screen, announced by its `PageHeader` (the h1 one) and `undefined` when
the page has none. A bar above the page uses it to avoid saying the same thing twice.

```tsx
const named = usePageHeading() === screenName; // the page already says it: leave the bar's title out
```

### `useNativeBack`

`true` when `NasimProvider` was given `nativeBack`: the host shows a back button, so a page draws
none. `PageHeader` reads it for you; use it only for a back control you draw yourself.

### `useBottomBar`

A bar your app draws at the bottom of the screen (a tab bar) would hide toasts, which sit just
above the safe area. Put the returned ref on the bar: its height, safe-area padding included, is
published as `--nasim-bottom-bar` and toasts rise above it.

```tsx
const bar = useBottomBar<HTMLElement>();
return (
  <nav ref={bar} className="px-safe pb-(--nasim-safe-bottom)">
    ...
  </nav>
);
```

### Tenant accent

`accent="#0b5cad"` sets the brand colour for both themes (its maths is a chunk of its own, downloaded only
when an `accent` is passed). One colour cannot serve both: a deep red
that reads on white vanishes on a dark surface, and a bright yellow does the opposite. So for each
theme the colour keeps its hue and chroma and moves in lightness only as far as it must, until

- the accent has at least 3:1 against that theme's page, surface and secondary surface, so
  buttons, switch tracks and spinners stay visible;
- text on the accent, and on its hover shade, has at least 4.5:1 (light or dark text is chosen);
- `--accent-soft-foreground` has at least 4.5:1 on the soft tint that chips and alerts use and on
  the secondary button's fill.

The two results are set on `<html>` as `--nasim-accent-light` and `--nasim-accent-dark`, each with
a `-foreground` partner, and `tokens.css` maps `--accent` to the one for the active theme. They
must be on `<html>`, not on a wrapper: HeroUI derives hover and soft tones there with
`color-mix()`. A value that is not a hex colour is ignored. The defaults in `tokens.css` obey the
same rules, and `tokens.test.ts` and `accent.test.ts` measure them for black, white, yellow, blue,
green and red and for every hue and lightness in between.

A screen that lets an admin pick the colour can show what the shop will really use. `readableAccents`
returns the accent and its text colour for each theme, or `null` for a value that is not a colour;
`accentRatios` measures them against the page of a theme in `SCHEMES`, with `MIN_UI` and `MIN_TEXT` as the
limits. `parseHex`, `toHex` and `oklchToRgb` turn a colour between hex and the maths, and `contrastRatio`
measures two of them (WCAG 2, 1 to 21).

### A product's own palette

`accent` fits one brand colour into Nasim's grey surfaces. A product that has its whole palette (PAYNYX:
green on navy) hands it over instead: surfaces, text, the accent and the four statuses, in light and
dark, as `#rrggbb`. Nasim writes it as a stylesheet, checks it against the same contrast rules as its
own tokens, and every component follows it. Nothing else in the app names a colour.

```tsx
// src/theme/palette.ts
import type { Palette } from '@nyxon/nasim';

export const palette: Palette = {
  radius: '0.625rem',
  light: {
    background: '#f5f8f7',
    foreground: '#121f30',
    surface: '#ffffff',
    surfaceSecondary: '#eaf2ee',
    surfaceTertiary: '#e1ece6',
    overlay: '#ffffff',
    muted: '#526477',
    border: '#d7e3dd',
    fieldBorder: '#6a7e8e',
    accent: { fill: '#07744a', onFill: '#ffffff' },
    success: { fill: '#08784d', onFill: '#ffffff', tint: '#e2f3ea', text: '#08784d' },
    warning: { fill: '#8a5700', onFill: '#ffffff' },
    danger: { fill: '#b42338', onFill: '#ffffff' },
    info: { fill: '#245baa', onFill: '#ffffff' },
  },
  dark: {
    // the same keys again
  },
};

// app/layout.tsx and providers.tsx
<NasimProvider palette={palette}>{children}</NasimProvider>;
```

What each key means, and the number it must hold (`checkPalette` measures all of them):

| Key                                                                   | Is                                                                            | Holds                                                |
| --------------------------------------------------------------------- | ----------------------------------------------------------------------------- | ---------------------------------------------------- |
| `background`, `surface`, `surfaceSecondary`                           | The page and the cards on it (`surfaceTertiary` is also HeroUI's `--default`) | `foreground` and `muted` at 4.5:1 on each            |
| `surfaceTertiary`, `overlay`                                          | Hovered rows and neutral chips; menus, popovers and dialogs                   | the same                                             |
| `fieldBorder`                                                         | The boundary of a field, a checkbox, an off switch                            | 3:1 on every surface                                 |
| `border`                                                              | Dividers and card edges (decoration only)                                     | nothing                                              |
| `accent.fill`, `accent.onFill`                                        | The brand: buttons, links, the active tab                                     | fill 3:1 on every surface; text on it 4.5:1, hovered |
| `success`, `warning`, `danger`, `info` (`fill/onFill`)                | The four statuses, solid                                                      | text on the fill 4.5:1, hovered too                  |
| `danger.fill`                                                         | Also error text                                                               | 4.5:1 on every surface                               |
| `<role>.tint`, `<role>.text`                                          | The soft pair of a chip or alert                                              | text 4.5:1 on the tint over every surface            |
| `focus`                                                               | The focus ring (default: the accent mixed into the text)                      | 3:1 on every surface                                 |
| `shadow`, `overlayShadow`, `backdrop`, `fieldBackground`, `separator` | Optional; the theme's own when left out                                       | `fieldBackground` carries the field rules            |

A role without `tint` and `text` gets its fill at 15% (12% in dark) as the tint and its fill mixed with
the page text as the text, so a tenant `accent` keeps working over a palette: it is fitted against
the palette's surfaces (`paletteSchemes`) instead of Nasim's. An explicit `tint` on the accent
switches that off for the accent's soft pair.

Test the palette where the product keeps it, so a change that breaks a rule fails the build:

```ts
import { checkPalette } from '@nyxon/nasim/palette';

it('keeps every contrast', () => expect(checkPalette(palette)).toEqual([]));
```

`@nyxon/nasim/palette` holds the types, `checkPalette`, `paletteCss` and `paletteSchemes` without any component,
and the colour maths (`parseHex`, `contrastRatio`, `luminance`), for a test or a server module.

`checkPalette` returns `{ scheme, pair, ratio, min }` for every pair that fails (an empty list when the
palette is sound) and throws on a value that is not `#rrggbb`: a colour is written into a stylesheet,
so nothing else gets through. `paletteCss` is the stylesheet itself. It is qualified with `html`, so
it wins over `tokens.css` whatever loads last, and it holds a `prefers-color-scheme: dark` rule for a
page with no saved choice, so with a palette a dark device paints dark from the first byte (without one,
see [Server and client](#server-and-client)). The `info` status
(`bg-info-soft text-info-soft-foreground`) exists in Nasim's own tokens too, for informational
messages that are neither good nor bad news.

### The saved choice, for the server

The theme controller keeps the choice in `localStorage` and in the cookie `THEME_COOKIE`
(`nasim-theme`). A server layout reads the cookie, renders the explicit choice on `<html>` and hands
it to the provider, so the first byte, the server render and the first client render agree and
nothing flashes:

```tsx
// app/layout.tsx (a Server Component)
const mode = parseThemeMode((await cookies()).get(THEME_COOKIE)?.value);
const explicit = mode === 'light' || mode === 'dark' ? mode : undefined;

<html lang="fa" dir="rtl" data-theme={explicit} suppressHydrationWarning>
  <body>
    <Providers initialMode={mode}>{children}</Providers>
  </body>
</html>;
```

`parseThemeMode` returns the mode a saved value stands for, or `undefined` for anything else, so a
stale or foreign cookie is ignored. `persist={false}` writes neither the storage nor the cookie. The cookie is
`nasim-theme=<mode>; Path=/; Max-Age=31536000; SameSite=Lax`, plus `; Secure` on https; going back to the
default mode removes it (`Max-Age=0`, same `Path` and `SameSite`).

## Tokens (`tokens.css`)

Semantic names over HeroUI's variables, defined once for light and dark.

| Group    | Tokens                                                                                                                          |
| -------- | ------------------------------------------------------------------------------------------------------------------------------- |
| Surfaces | `background`, `foreground`, `surface`, `surface-secondary`, `surface-tertiary`, `overlay`                                       |
| Text     | `foreground`, `muted` and `danger` (4.5:1 or more on every surface), and each status's `*-soft-foreground` on its `*-soft` tint |
| Fills    | `accent` (3:1 or more on the page and surfaces), `success`, `warning`, `danger`, `info`, with `*-foreground` for text on them   |
| Lines    | `border`, `separator`                                                                                                           |
| Fields   | `--field-background`, `--field-border`, `--field-border-hover`, `--field-border-focus`, `--field-border-width` (1px)            |
| Focus    | `--focus`                                                                                                                       |
| Geometry | `--radius`, `--field-radius`, `--nasim-page-gutter`, `--nasim-tap-target` (44px)                                                |
| Cards    | `--card-<tone>-from`, `--card-<tone>-to`, `--card-foreground`, `--card-foreground-muted` (`BankCard`)                           |
| Viewer   | `--viewer-background`, `--viewer-foreground`, `--viewer-muted` (`ImageViewer`, dark in both themes)                             |

Do not write text in `accent`, `success` or `warning`. As plain colours they are fills and edges:
`success` and `warning` measure about 2:1 on a light surface, and a tenant's accent is only
guaranteed 3:1. Coloured text uses the soft pair: `text-accent-soft-foreground` on `bg-accent-soft`
(chips and alerts already do; the secondary button puts it on `default`, which the accent rules
cover too), 4.5:1 or more in both themes.

Fields are bordered in both themes (in dark mode a field and its card share a fill) and an invalid
field shows it in the border. `tokens.test.ts` asserts the contrast of every text, fill and border
pair, and of every soft pair on the page and both surfaces, in both themes. An off switch's track is
the field border (hovered, it mixes towards the text), so it holds the same 3:1.

### Safe areas

`--nasim-safe-top`, `--nasim-safe-right`, `--nasim-safe-bottom`, `--nasim-safe-left` hold the room
a screen must leave for the device and for Telegram. Each is the larger of the device's
`env(safe-area-inset-*)` and Telegram's safe-area plus content-safe-area insets, read from
`--tg-safe-area-inset-*` and `--tg-content-safe-area-inset-*` (the names Telegram's own script
uses; the app binds them from the SDK's state and keeps them current on `safe_area_changed`) or,
failing those, the SDK's longer `--tg-viewport-*` names. Outside Telegram they are the device
insets. To force a value, set the variable on `<html>`. The Mini App shell also reads
`--tg-viewport-stable-height` for its own height.

`PageHeader placement="top"` and `BottomSheet` respect them. Your own fixed bars should too. The
left and right insets are physical, so they have their own utilities: `px-safe` pads by the insets
alone, `px-page` by the page gutter or the inset, whichever is larger, and `p-page` does that on
all four sides.

```tsx
<nav className="fixed inset-x-0 bottom-0 px-safe pb-(--nasim-safe-bottom)">...</nav>
```

### Touch targets

Primary actions on a phone are at least 44px: use `size="lg"` (44px on phones, 40px on desktop)
for the main button of a screen. `SubmitButton`, `EmptyState`, `ErrorState`, `ConfirmDialog` and
the `PageHeader` back button already do. Under `(pointer: coarse)` icon-only buttons, close
buttons, a tag's remove button and the number-field steppers keep their look but get a 44px hit area. Text fields,
selects and switch rows are at least 44px tall.

### Left-to-right values

Technical values (ids, links, codes, phone numbers) keep `dir="ltr"` so Latin text and digits read
correctly, and they sit on the RTL start edge, the right: `TextField dir="ltr"` and `CopyField`
right-align their text, and so does a `ltr` value in a `stacked` `KeyValueList`. In a two-column
`KeyValueList` row the value cell is at the row's end, so a `ltr` value aligns left there.

### Digits and fonts

Nasim chooses the font; the app loads it. `fonts.css` holds one `[data-font="<id>"]` rule per font
(its family and its digit feature) and the default rule for `:root`; it has no `@font-face`. A rule
takes the family from `--font-<id>` when the app exposes one (`next/font` with `variable:
'--font-vazirmatn'`, which brings its own fallback list) and otherwise names the family, which the
app then declares with its own `@font-face`. A font the app does not load is a font the page cannot
use, so a tenant's `font` id must be one the app ships. The default is Vazirmatn, `--font-vazirmatn`,
and it must be the cut that has Latin letters and digits (the `vazirmatn` package's
`Vazirmatn[wght].woff2`); the non-Latin cut in `@nyxon/ui` needs a Latin face in front of it, or Latin
silently falls back to Tahoma. `font="estedad"` on `NasimProvider` puts `data-font` on `<html>`, so the
whole page follows; on any element `data-font` with `font-sans` previews that font. `html` takes its
`font-feature-settings` from the font: `"ss01"` in Vazirmatn and `"ss20"` in Estedad draw ASCII digits as
Persian digits while the text stays ASCII (copied numbers still scan); the other builds have Persian digits
built in. `font-mono` ignores the feature, so technical values keep Latin digits. Use `tabular-nums` only
where numbers must line up (balances, prices, countdowns). To add a font: the app loads it and its
license, and `fonts.css` gets a rule with its id and digit feature.

## Composites

Each is one idea in one file (a part splits when it stops being one idea, not at a line count), takes
copy as props and uses Nasim's strings for its own words. The
examples read their copy from `t`, the app's own strings module, as screens must: `t.services.title`
and the like stand for keys you add there.

### `PageHeader`

A page or section heading with an optional back link and actions.

```tsx
<PageHeader title={t.services.title} description={t.services.subtitle} backHref="/" actions={<Button size="sm">{t.shop.buy}</Button>} />
```

`as` (`"h1"` default, `"h2"`, `"h3"`), `size` (`"page"`, `"section"`), `placement` (`"content"`
default; `"top"` when the header is the first thing on screen and must clear the safe areas).
`description` may be a node, `meta` is a small line under it (a status chip, the last update) and the
actions wrap under the title on a narrow screen.

### `Breadcrumbs`

The trail to the current page. `items` run from the root to the page (`BreadcrumbItem`: `{ id, label, href? }`):
every step but the last is a link (in-app through `NasimProvider`'s `navigate`, like every `Link`) and the last
is the current page, marked `aria-current="page"` and not a link, whatever `href` it carries. The steps read
from the start (right) to the end, with a chevron between them that HeroUI turns for a right-to-left page and
hides from a screen reader; a long trail wraps instead of scrolling the page. It is a navigation landmark named
«مسیر صفحه» (`t.breadcrumbs`), or by `label`. Links keep a 44px target on a coarse pointer.

```tsx
<Breadcrumbs
  items={[
    { id: 'home', label: t.nav.home, href: '/' },
    { id: 'services', label: t.nav.services, href: '/services' },
    { id: 'one', label: service.name },
  ]}
/>
```

### `SubmitButton`

The form's submit button: `type="submit"`, large, full width. Inside `FormRoot` it shows the
spinner while the form submits. While it runs the button is disabled, so clicks and Enter cannot
submit twice; it is deliberately not React Aria's `isPending`, whose announcement points at the
button's own id and dangles (axe `role-img-alt`) when a form closes or is replaced on success.
Outside a form, pass `isPending` yourself.

```tsx
<SubmitButton>{t.common.confirm}</SubmitButton>
```

### `ThemeToggle`

A round icon button that flips light and dark. It shows the other theme's icon and is named for the press
(`lightLabel`, `darkLabel`: the app's words). It stores the other theme, except when that is what the host
already shows (the device, or Telegram): then it hands the choice back (`automatic`), so a person who
flips twice is on «follow my device» again. Disabled until hydration, because the server does not know
the device's scheme.

```tsx
<ThemeToggle lightLabel={t.theme.light} darkLabel={t.theme.dark} />
```

### `Kbd`

A keyboard shortcut in HeroUI's key caps: `keys` in order (`["ctrl", "K"]`). A key Nasim knows (`KbdKey`: the
modifiers, enter, escape, tab, space, delete, the arrows, page and line keys) is drawn as its cap, in the Latin
letters of the keyboard («Ctrl», «Esc», an arrow for an arrow; HeroUI's own Mac symbols read as «^» and a stray
icon in a Persian font), with its Persian name («کنترل») on hover and, as hidden text, for a screen reader; any
other string is drawn as it is. The group is left to right whatever the page direction. `variant` is `"default"`
or `"light"` (no fill, for a key on a tinted ground). A Server Component may render it.

```tsx
<Kbd keys={['ctrl', 'K']} />
```

### `LoadingState`

```tsx
<LoadingState />
<LoadingState size="inline" label={t.orders.checkingPayment} />
```

The default fills a page (centred, tall); `size="inline"` fits inside a card or list. It is an
`<output>` (a polite live region), so the label is announced.

### `EmptyState`

```tsx
<EmptyState title={t.services.emptyTitle} description={t.services.emptyHint} action={{ label: t.shop.browse, href: '/shop' }} />
```

`action` is `{ label, href }` or `{ label, onPress }`, or your own element when the next step needs
more than a button (two buttons, a button that is only there for some people). `description` may be a
node. An empty screen should always offer the next step. `icon` replaces the default. The title is an `h2`; pass `as="h1"` when the state is the
whole page. When a screen swaps a state in (a request failed, a wait ended), pass `titleRef` and
focus it: the title becomes focusable, so the keyboard is where the news is and a screen reader
hears it.

### `ErrorState`

```tsx
<ErrorState onRetry={refetch} supportHref={supportUrl} requestId={error.requestId} />
```

Defaults to a generic title and a connection hint; pass `title` and `message` for specific cases.
`requestId` is shown as a tracking code in a left-to-right monospace span. The title is an `h2`;
pass `as="h1"` when the state is the whole page, and `titleRef` to move focus to it like `EmptyState`.
`retryIn` (seconds) keeps the retry button disabled, counting down, for a server that said when to come back.
Children are detail under the message, announced with it (the fields a server refused).

### `ConfirmDialog`

An alert dialog for destructive or money-moving actions. `tone="danger"` for irreversible ones.

```tsx
<ConfirmDialog isOpen={open} onOpenChange={setOpen} tone="danger" title={t.services.deleteTitle} description={t.services.deleteWarning} confirmLabel={t.services.delete} onConfirm={() => removeService.mutateAsync(id)} />
```

`onConfirm` may return a promise: the button shows the spinner, Escape and the backdrop are
disabled meanwhile, and the dialog closes when it resolves. If it rejects the dialog stays open;
report the error yourself (toast, mutation `onError`). Escape and the cancel button close it.

When the caller already knows that the action is running (a mutation's `isPending`), pass `isPending`:
the dialog then only shows it, calls `onConfirm` without waiting and does not close itself; close it
when the action succeeds. `description` may be a node, or put a body of several paragraphs in the children.
`isConfirmDisabled` draws the confirm button disabled while the action is not yet allowed (a reason still to
be written); the cancel button stays live.

### `BottomSheet`

A sheet from the bottom edge for choices and short forms.

```tsx
<BottomSheet
  isOpen={open}
  onOpenChange={setOpen}
  title={t.checkout.paymentMethod}
  footer={
    <Button size="lg" onPress={pay}>
      {t.checkout.pay}
    </Button>
  }
>
  {methods}
</BottomSheet>
```

Closes with Escape, a backdrop tap, a drag down or the close button. A press on the backdrop is
ignored for half a second after the content changes height (the button the tap was meant for has
moved, and the tap would land beside the sheet) and while `isBusy` is set, which a flow passes while
its request runs. A sheet that moves money passes `isDismissable={false}`: the backdrop and a drag
down close nothing, and only its own buttons, Escape and the host's Back close it. It keeps clear of
the safe areas, and inside Telegram its height follows `--tg-viewport-stable-height`. Footer buttons
fill the width on phones.

### `SidePanel`

The detail and the edit form of a row: a row of a list opens its side panel. On a desktop (`sm` and up) it is a
drawer from the inline-end edge, the left in a right-to-left page; on a phone it is the bottom sheet, with its
drag handle and its safe areas. The edge is read from the document direction, so a page with `dir="ltr"` opens
it from the right.

```tsx
<SidePanel
  isOpen={open}
  onOpenChange={setOpen}
  title={t.services.detailTitle}
  description={t.services.detailHint}
  size="md"
  footer={
    <>
      <Button variant="tertiary" onPress={() => setOpen(false)}>
        {t.common.close}
      </Button>
      <Button onPress={renew}>{t.services.renew}</Button>
    </>
  }
>
  {details}
</SidePanel>
```

`title`, optional `description` (also its accessible description), `children` (the body, which scrolls), `footer`
(the actions: the cancel first, the main action last; it stays under the body, so it is always in reach, and a
panel without one draws none) and `size` (`"sm"` 420 px, `"md"` 480 px, `"lg"` 560 px; a narrower screen takes
what it has). Controlled only: `isOpen` and `onOpenChange`.

It behaves like `Modal`. `isDismissable={false}` is for a form with unsaved input: the backdrop, a drag and
Escape close nothing, and only its own buttons (the close button, the footer) and the host's Back close it.
`isBusy` does the same while a request runs, and Back is ignored too, until it is over. It registers as a layer
(`useRegisterOverlay`), so Telegram's Back button closes it as the top layer. A body that scrolls is a named,
focusable region, scrolling stays inside it (`overscroll-behavior: contain`) and the page behind does not move.

It is built on HeroUI's `Drawer`, as `BottomSheet` is, so both bottom sheets drag alike. Motion is a slide on `transform` and a fade on `opacity` of the backdrop, nothing else. Under
`prefers-reduced-motion: reduce` it fades in and out without travelling (`tokens.css`).

A good detail panel, read from the top: an identity block (who or what it is), small muted section labels over
the groups, a two-by-two grid of `StatCard` tiles for the figures, a labelled `UsageBar` for a quota, then the fields as a `KeyValueList` with a `CopyText` beside every id. The demo
page shows it.

### `KeyValueList`

```tsx
<KeyValueList
  items={[
    { label: t.wallet.balance, value: formatToman(balance), numeric: true },
    { label: t.services.id, value: serviceId, ltr: true },
  ]}
  layout="split"
/>
```

`layout` is `"split"` (label at the start, value at the end; a long value wraps under its label),
`"stacked"` (value under label, for long values) or `"grid"` (pairs in two columns from `sm` up, label
above value: the details of one record). `label` may be a node. `ltr` marks technical values; `numeric`
aligns digits. A row that exists only sometimes is `cond && { label, value }`: `false`, `null` and
`undefined` are skipped. `className` lands on the `<dl>`. Server-renderable.

### `Cover`

A 16:9 picture box that keeps its shape with or without the picture: no `src` (none yet, or none at
all) shows an accent-tinted placeholder with the `icon` of the kind of thing it stands for, so every
card in a grid is the same height.

```tsx
<Cover src={category.image_url} icon={<CategoryIcon />} />
```

### `CopyField`

A read-only value in a field that copies when pressed anywhere; always left to right. A long value is
cut in the middle, so its last eight characters stay visible and nothing overflows.

```tsx
<CopyField label={t.services.subscriptionLink} value={subscriptionUrl} />
```

On success it shows a toast and «کپی شد»; if the clipboard is blocked it selects the text and tells
the person to copy it by hand. `children` sit under the field (a QR button, a pager of several values).

`multiline` shows a value of several lines (a WireGuard profile) whole, in a box of its own, and
copies it whole.

### `MessageBar`

A chat's compact composer: one rounded row with an attach button (`leading`), a text box that grows up
to five lines and a round send button. Enter sends, Shift+Enter breaks the line. The text is yours
(`value`, `onValueChange`); `attachment` and `notice` sit above the row.

```tsx
<MessageBar
	label={t.tickets.composer.message}
	sendLabel={t.tickets.composer.send}
	value={text}
	onValueChange={setText}
	onSubmit={send}
	canSend={text.trim() !== ""}
	leading={attachButton}
/>
<MessageBar closedNote={t.tickets.thread.closedNotice} />
```

`closedNote` replaces the whole bar with that note when the conversation is over. Put it at the bottom
of a screen that fills the window.

### `SearchBox`

A search field for filtering a list (outside a form). The label names it for a screen reader; there is
no visible one. It reports every keystroke, so wait before searching on each of them yourself.

```tsx
<SearchBox label={t.services.search} value={query} onChange={setQuery} />
```

The clear button and Escape empty it. HeroUI labels its clear button "Close"; ours says
«پاک کردن جست‌وجو».

### `FilterChips`

One of a few filters, always one chosen: a radio group drawn as chips that wrap on a narrow screen.
Arrow keys move between the chips and Space chooses.

```tsx
<FilterChips label={t.services.statusFilter} value={status} onChange={setStatus} options={[{ value: 'all', label: t.services.filters.all }]} />
```

### `OptionCards`

One of a few choices that need more than a word each (a package with its price, a payment method with
its fee): a radio group whose radios are tappable cards. `meta` is said at the end of the card.

```tsx
<OptionCards label={t.payments.method} value={method} onChange={setMethod} options={[{ value: 'wallet', title: t.payments.wallet, description: t.payments.walletHint, meta: price }]} />
```

`hideLabel` names the group for a screen reader only, when the screen has a heading for it; `isInvalid`
and a per-option `icon` and `isDisabled` exist too. A `description` may be a node (a sample drawn in a
font), and `className` lays the cards out some other way (`grid grid-cols-2`). In a `FormRoot` it takes a
`name` instead of `value` and `onChange`, like the other fields, and shows the form's message under the cards:

```tsx
<OptionCards name="plan" label={t.plan.label} options={plans} />
```

### `SortableList`

A short list (2 to 30 rows: the shop's payment gateways, the start-menu buttons) that a person puts in order
by dragging. It is controlled: it draws `items` in the order given and calls `onReorder` with every id in
the new order; it keeps no order of its own, so the owner saves the order and passes it back.

```tsx
<SortableList label={t.gateways.order} items={gateways} onReorder={saveOrder} />
```

`items` is `{ id, label, description? }[]`, `label` names the list for a screen reader, and `isDisabled`
(while saving) turns off dragging and the buttons. Four props, no more.

- **Drag.** A mouse or a finger drags a row by anywhere on it; the grip at its start is the drag handle for a
  keyboard and a screen reader (Enter to pick up, arrow keys or Tab to a place, Enter to drop, Escape to
  cancel). A line in the accent colour shows where the row will land.
- **Without dragging.** Every row has «بردن به بالا» and «بردن به پایین» buttons (WCAG 2.2, 2.5.7 Dragging
  Movements): the first row's up and the last row's down are disabled. Each button is named with its row
  («بردن زرین‌پال به بالا»), a polite line says where the row went, and focus stays on the pressed button
  (on the other one when the row reached the top or the bottom).
- **Targets and direction.** Every control is 44px (`size-11`); the layout is logical, so the grip sits at
  the start (the right) in Persian. The colours are tokens, and the focus ring is Nasim's.

What it follows in React Aria (`react-aria-components` 1.21.1 when it was written, read from `dist/private/`, and the skill's
`references/guides/dnd.md` «Reordering items» and `components/GridList.md` «Drag and drop»):

- `GridList` takes `dragAndDropHooks` from `useDragAndDrop`; the row is `GridListItem` with a `textValue`.
  `GridList.mjs` warns when a draggable item has no `<Button slot="drag">` and gives that button the
  keyboard and screen-reader drag (it sets `pointer-events: none` on it, so the row itself is the mouse and
  touch source). The list has no selection, so a press on a row never fights a drag.
- `useDragAndDrop` options used: `getItems` (what is dragged; a private type, so a drop in a text box or from
  another page does nothing), `acceptedDragTypes`, `onReorder` (React Aria's «between items only» drop:
  `e.keys` and `e.target.key` with `dropPosition` `before` or `after`), `renderDropIndicator` with
  `DropIndicator`, and `isDisabled`, which empties the row's drag props and disables the handle.
- React Aria's drag-and-drop announcements and the handle's name («کشیدن زرین‌پال») are English in
  `@react-aria/dnd`; the Persian ones are in `t.reactAria['@react-aria/dnd']`.

### `ScrollRegion`

Wraps content that can be wider than the screen, such as a table. It scrolls sideways, and only while
it does it becomes a focus stop with a name, because a keyboard can scroll only what it can focus.

```tsx
<ScrollRegion label={t.content.tariff.table(name)}>
  <table>…</table>
</ScrollRegion>
```

### `Stepper`

Where the person is in a flow of a few steps (a renewal: options, method, confirm): a bar for the eye
and the same in words, «مرحله ۲ از ۴: روش پرداخت». The bar is decoration; the words are what a screen
reader gets. Move focus to the new step's heading yourself when the step changes.

```tsx
<Stepper steps={[t.renew.options, t.renew.method, t.renew.confirm]} current={1} />
```

### `StatusChip`

A status as an icon and words on a soft tint: `tone` is `"success"`, `"warning"`, `"danger"`, `"info"` or
`"neutral"`, `label` is the status in words (the chip is never colour alone), `size` is `"sm"`, `"md"` or
`"lg"`. `icon` replaces the tone's icon (a clock for «waiting», an hourglass for «expired»). Plain markup, so
a Server Component can render it.

```tsx
<StatusChip tone="success" label={t.invoice.paid} />
<StatusChip tone="neutral" label={t.invoice.expired} icon={<HourglassIcon />} size="sm" />
```

### `Notice`

An inline message (HeroUI's alert with its icon): `tone` is `"info"` (default), `"success"`, `"warning"`,
`"danger"` or `"neutral"`, with an optional `title`. Pass `role="alert"` for a failure that appears in answer
to an action and `role="status"` for good news.

```tsx
<Notice tone="warning" title={t.limits.title} role="status">
  {t.limits.body}
</Notice>
```

### `SectionCard`

A card with a titled header and a body: a `<section>` named by its own heading (`level` 2 by default, 3
inside another section), with `description`, `actions` at the far end of the header and a decorative
`icon`. A card with no header is `Card`. Server-renderable.

```tsx
<SectionCard title={t.destinations.title} description={t.destinations.hint} actions={<Button size="sm">{t.destinations.add}</Button>}>
  {rows}
</SectionCard>
```

### `StatCard`

A key figure: `label`, a tabular `value` (a number or an amount with its unit), a `hint` for its scope, a decorative
`icon` at the end of the label's line and a `footer` (anything else under it). Two optional slots make it a
KPI: `trend` (a `TrendChip`) sits at the end of the figure's line and drops under it when the figure is wide, and
`sparkline` (a `Sparkline`) is under the hint. A card without them is drawn as it always was. `as="h2"` makes the
label a heading when the tile titles a section. Server-renderable.

```tsx
<StatCard label={t.sales.title} value={formatToman(total)} hint={t.sales.period} />
<StatCard label={t.sales.title} value={formatToman(total)} hint={t.sales.period} trend={<TrendChip change={0.12} suffix={t.sales.vsLastMonth} />} sparkline={<Sparkline data={daily} summary={t.sales.sparkline} />} />
```

### `TrendChip`

The change against the previous period as a chip: an arrow, a sign and the percent («+۱۲٪», «−۳٫۴٪»), so colour is
never the only word, and a screen reader hears «افزایش ۱۲٪» or «کاهش ۳٫۴٪». `change` is a fraction (`0.12` is
+12%). Up is good by default (green, a rise); `isInverse` is for a metric where down is good (refunds, errors,
churn), which swaps the colours and keeps the arrow and the sign. A change that rounds to zero at one decimal is
flat (neutral, a dash, no sign), and so is one that cannot be computed (`NaN`, a previous period of zero), which
says «بدون مقایسه». `suffix` names what it is compared with, in the app's words, after the chip; `size` is `"sm"`
(default) or `"md"`. The signed number is left to right so the sign stays on the digits. The tints are
`StatusChip`'s, already held at 4.5:1. HeroUI Pro's TrendChip (direction, percent, a custom prefix and suffix)
was the layout. Server-renderable.

```tsx
<TrendChip change={(total - previous) / previous} suffix={t.sales.vsLastMonth} />
<TrendChip change={refundRate - lastRate} isInverse />
```

### `Sparkline`

A tiny line of a series, with no axes and no text: the shape only, beside the figure that carries the number.
`data` is the series, oldest first, and a `null` is a gap (no observation), drawn as a break in the line, never
as a zero; a point with no neighbour is a dot. `summary` is what a screen reader hears for the picture (the range
and the latest figure, in words): the SVG is a named image. `tone` is `"accent"`, `"success"` or `"info"`,
`variant` is `"area"` (default, a tint under the line) or `"line"`, and `className` sizes it (it is `h-10` and as
wide as its box, drawn with `preserveAspectRatio="none"` and strokes that keep their width). The latest value
has a dot. As in `ColumnChart` time runs from the left to the right whatever the page direction. With no value it
draws a baseline. Server-renderable.

```tsx
<Sparkline data={days.map((day) => (day.hasData ? day.count : null))} summary={t.sales.sparkline(min, max, last)} tone="success" />
```

### `SkeletonRows`, `TableSkeleton`, `PageSkeleton`

Loading shapes that keep the layout still while data arrives: list rows (`dense` for plain bars), a table
with a header and `rows` body rows, and a whole screen (`header`, `stats` tiles, `rows`). Each is one
`role="status"` with a visually hidden `label` (default «در حال بارگذاری»); the shapes are decoration.

```tsx
<PageSkeleton stats={3} rows={4} label={t.dashboard.loading} />
```

### `OfflineBanner`, `useOnline`

A polite strip (`role="status"`) above the page while the connection is down and nothing while it is up;
its words are Nasim's, or pass your own as the child. `useOnline()` is the same fact as a boolean (the
server says `true`).

```tsx
<OfflineBanner />
```

### `CopyButton`

A button that copies `value` (its canonical form: Latin digits, no separators) and says so: its label
turns into `doneLabel` («کپی شد») for a moment and a polite live region announces it. Where the clipboard
API is refused (a Telegram WebView) it falls back to the older copy command. If that fails too, the button
shows a danger icon and a line under it, in words and as the live region, says «کپی نشد؛ مقدار را دستی
انتخاب و کپی کنید.»: the button selects nothing, so the value must be on the page beside it, and the failure
stays until the next press. `CopyField` is the field that shows the value and selects it for you when the
clipboard is refused; this is the button beside a value you show yourself (a card number grouped in fours,
a one-time secret).

```tsx
<CopyButton value={card} label={t.checkout.copyCard} />
```

### `CopyText`

An id, a link or a code with a small copy button beside it, in place of a separate «کپی آیدی» button: the value
is shown inline and the button, an icon, is named from `label` («کپی شناسه سرویس»). The feedback stays where the
press was: the icon becomes a check, the name does not change, and a polite live region says «کپی شد» (`doneLabel`
replaces it). Where the clipboard API is refused it uses the older copy command as `CopyButton` does; if that fails
too the button shows a danger icon and a line under the value says, in words and as the live region, that the value
must be selected and copied by hand, until the next press.

```tsx
<CopyText value={service.id} label={t.services.id} isLtr />
<CopyText value={service.link} label={t.services.link} isLtr>
  {shortLink}
</CopyText>
```

`isLtr` is for ids, links and codes: the value is `dir="ltr"`, monospace and not translated by a browser. Without
it the value takes the page direction. `children` is what is shown when that is not the value itself (a shortened
id); `value` is always what is copied. It is inline, so it sits in a `KeyValueList` cell, a table cell or a line
of text, and a press on its button never reaches the row around it: it is safe in a row that opens a `SidePanel`
on a press. `CopyField` is the whole field for a value to hand over; `CopyButton` is a labelled button beside a
value you draw yourself.

### `BankCard`

A card number drawn as a bank card, for a card-to-card payment method: the digits in four left-to-right groups
(real spaces between them, so a selection reads as a number), the holder, the bank's name and a tone to match,
and a button that copies the digits without separators. It validates nothing; it only draws.

```tsx
<BankCard number={method.cardNumber} holder={method.holder} />
<BankCard number={method.cardNumber} isMasked />
<BankCard number={method.cardNumber} size="compact" />
```

`number` is the card number in any digit script (Persian and Arabic digits are read, spaces, dashes and
zero-width joiners are ignored); a length other than 16 is grouped by fours all the same. The bank comes from
the first six digits (a table of Iranian BINs, public Shetab data, merged banks under their historic prefixes)
and its name is Nasim's own word (`t.bank`); `bank` replaces the name with the app's own, and a prefix not in the
table draws a neutral graphite card named «کارت بانکی». The tone is a loose nod to the bank's colour, not its logo.
`holder` is shown when given.

`isMasked` shows only the last four digits (`•••• •••• •••• 7893`): the other twelve never reach the page, the
group is named «کارت بانک ملی ایران، پایان ۷۸۹۳», and the bullets are hidden from a screen reader. The mask is for
the eyes: the copy button still copies the whole number, because the app handed it over. A number that is not
all digits (`603799******7893`, as an API masks it) is drawn as it is, with a bullet for each star, and has no
copy button, since there is nothing real to copy.

`size="compact"` is for a table cell: one line with a small swatch in the card's tone, the number grouped, and a
copy icon (it is a `CopyText`), with no holder and no face. A press on a copy button never reaches a row that
opens on a press. The copy says «کپی شد» in a live region and, when the clipboard is refused, says in words that
the number must be copied by hand, as `CopyButton` does.

The tones are tokens (`--card-<tone>-from` and `-to` for `blue`, `teal`, `green`, `orange`, `red`, `wine`, `purple`
and `graphite`, light and dark, and `--card-foreground` and `--card-foreground-muted` for the text on them). The
test holds 4.5:1 for both texts over the whole face, the middle and the card's own shine, in both themes.

### `UsageBar`

How much of an allowance is used: data, days, seats, anything metered. A label and the figures on one line over a
thin bar; it is HeroUI's `Meter`, so it is a `meter` for assistive technology (`aria-valuemin`, `aria-valuemax`,
`aria-valuenow`, `aria-valuetext`). The figures are the app's words: it formats bytes or days and passes them as
`valueText`, and that text is the meter's `aria-valuetext` too.

```tsx
<UsageBar label={t.usage.data} used={usedBytes} total={planBytes} valueText={t.usage.of(formatBytes(usedBytes), formatBytes(planBytes))} />
<UsageBar label={t.usage.data} used={usedBytes} total={null} valueText={formatBytes(usedBytes)} size="compact" />
```

`label` names the meter and is on screen (`size="compact"` keeps it for a screen reader only), `used` and `total` are
numbers in the same unit, `valueText`, `warningAt` (default 80) and `dangerAt` (default 100) are percents of the
total. From `warningAt` the bar turns to the warning colour, from `dangerAt` to the danger one, and the value text
gets an icon and, for a screen reader, words after the app's text («، نزدیک به سقف», «، به سقف رسیده»), so the status
is never colour alone. When more is used than there is, the bar is full and `aria-valuenow` stops at the total.

`total={null}` is unlimited: a full bar in a neutral colour, an `∞` after the value text, «، نامحدود» for a screen
reader, and no thresholds. A `total` of `0` is an empty bar until something is used and danger once it is.

`size` is `"regular"` (a label over the bar, the figures at the end of that line) or `"compact"` (one line: a thin
bar with the figures beside it, for a table cell). Every fill colour is a token held at 3:1 on the track and on the
surfaces in both themes, and `tabular-nums` keeps the figures from jumping.

### `ImageViewer`

A viewer for a receipt photo or a PDF, full screen in a `Modal` (`size="full"`): the admin approves a payment from
the picture, so it must be possible to read the small print.

```tsx
<ImageViewer isOpen={open} onOpenChange={setOpen} src={receipt.url} title={t.receipts.title(receipt.id)} downloadHref={receipt.url} downloadName={receipt.fileName} />
<ImageViewer isOpen={open} onOpenChange={setOpen} type="pdf" src={receipt.url} title={t.receipts.title(receipt.id)} onDownload={download} />
```

`title` names the dialog and is its heading, `alt` describes the picture when that says more (it defaults to the
title), `src` is the file's address and `type` is `"image"` (the default) or `"pdf"`. The download is the app's:
`downloadHref` makes the button a link to the file (`download` carries `downloadName`), `onDownload` calls the
app's own function (a signed address it fetches first), and with neither there is no download button.
`isOpen` and `onOpenChange` control it; it registers as a layer, so Telegram's Back and Escape close it.

For a picture, a toolbar has «بزرگ‌نمایی», «کوچک‌نمایی» (with the level, «۱۵۰٪», between them), «چرخاندن»,
«بازنشانی نما» and the download. From the fit (100%) to 500%; zoom out stops at the fit and zoom in at the
largest, and the two buttons say `aria-disabled` instead of being disabled, so the keyboard does not fall out of the
dialog. The same works by

- **Keys** (from the stage or any control, with no control, meta or alt key, and by key code as well as by letter,
  so the Persian layout works): `+` and `-` zoom, `0` resets, `R` rotates a quarter turn, `Escape` closes, and
  the arrow keys pan a zoomed picture from the stage, the keyboard's way to move a drag.
- **The wheel**, towards the pointer (a trackpad pinch arrives as a wheel with the control key), without moving the
  page behind.
- **Fingers and the mouse**: a drag pans a zoomed picture, never further than it overflows the stage; two fingers
  pinch (and pan together); a double click zooms in and, when zoomed, back out.

A picture turned on its side is fitted into the stage, and the level shown stays relative to that fit. Reset
turns it upright the short way round. The picture moves on `transform` alone, with a short transition for a
button or a key and none while a finger is on it or under `prefers-reduced-motion`; the stage is
`touch-action: none` and `overscroll-behavior: contain`. A new `src` starts over.

It says «در حال بارگذاری» (a status) until the picture is there, with the controls held, and, if the file cannot be
shown, «نمایش فایل انجام نشد» with a retry (an alert); the download and the close button still work then, so the
file can be had. With `type="pdf"` the document is an `<object>` in the browser's own viewer, with no zoom or
rotate of ours, and where the browser cannot show a PDF the object's fallback says so and links the file (the
app's `downloadHref`, or `src`). The stage and its bar are dark in both themes (`--viewer-background`,
`--viewer-foreground`, `--viewer-muted`, held at 4.5:1), since a receipt reads best on dark.

### `Collapsible`

Advanced or rarely used options in a native `<details>`: the `title` says what is inside before it opens,
`description` is one line under it, `defaultOpen` starts it open. Keyboard and screen readers work with no
client JavaScript. Server-renderable.

```tsx
<Collapsible title={t.limits.advanced} description={t.limits.advancedHint}>
  {fields}
</Collapsible>
```

### `AppShell`

The frame of a dashboard: a sidebar from `lg` up (240px, quiet: a tint for the current page and a small bar at
its start), a sticky bar with a menu button that opens the same navigation in a drawer below it, `banner` above
the page and the page itself in `<main id="main">`. The app knows the route, so each nav item carries its own
`isCurrent` (Nasim imports no router); links navigate through `NasimProvider`. The bar and the page clear the
safe areas, so the same shell serves the Telegram Mini App.

```tsx
<AppShell brand={<Logo />} navLabel={t.nav.label} nav={items.map((item) => ({ href: item.href, label: item.label, icon: <item.Icon />, isCurrent: item.href === current }))} topbar={<ThemeToggle lightLabel={t.theme.light} darkLabel={t.theme.dark} />} sidebarFooter={<Attribution />} banner={<OfflineBanner />}>
  {children}
</AppShell>
```

`nav` is a flat list or a list of groups, `{ id, label, items }`: each group is a labelled list (a `group` named
by its label, the label a small muted line above it) and a group with no items is left out, label and all. A
flat list draws as before.

`badge` on an item is the number of things waiting there: a pill at the item's end, `۹۹+` above 99, nothing for
zero or for no number. The pill is hidden from a screen reader and the link keeps its plain name (so the name
holds the text a sighted person reads, WCAG 2.5.3); `badgeLabel(count)`, the phrase the app passes (the count
arrives in Persian digits) or Nasim's «۳ مورد در انتظار», is the link's description, read after the name, so the
number is never only a shape.

`header` is the start of the bar, next to the menu button: a `Breadcrumbs` trail or a title. It takes the room
there is and shrinks (`min-w-0`) before it pushes `topbar`, the bar's end (page actions), off the screen. Without
`header` the bar shows the brand on a phone, as before; with it, the brand stays in the sidebar and the drawer.
The bar sticks to the top, grows by the top inset and pads by the side insets (`px-page`), and publishes its
height as `--nasim-header-height` on `<html>`, which `tokens.css` turns into `scroll-padding-top`: a focused
element, an anchor, a scrolled-to row stops below the bar instead of under it.

`contentWidth` is `"contained"` (default: the page is capped at `max-w-7xl` and centred) or `"full"`: the page
takes the whole width beside the sidebar, for tables and lists on a wide screen. Pages may still cap
themselves.

```tsx
<AppShell
  brand={<Logo />}
  navLabel={t.nav.label}
  nav={[
    {
      id: 'daily',
      label: t.nav.daily,
      items: [
        { href: '/', label: t.nav.home, isCurrent: true },
        { href: '/review', label: t.nav.review, badge: waiting },
      ],
    },
    { id: 'system', label: t.nav.system, items: [{ href: '/settings', label: t.nav.settings }] },
  ]}
  header={
    <Breadcrumbs
      items={[
        { id: 'home', label: t.nav.home, href: '/' },
        { id: 'review', label: t.nav.review },
      ]}
    />
  }
  topbar={<ThemeToggle lightLabel={t.theme.light} darkLabel={t.theme.dark} />}
  sidebarFooter={<AccountMenu name={me.name} description={t.role.owner} items={accountItems} onAction={onAccountAction} />}
  contentWidth="full"
>
  {children}
</AppShell>
```

### `AccountMenu`

The signed-in person as one button: a photo or the first letter of the name (`avatarSrc` loads the photo; the
letter stands in until it has, and without one), the `name` and a line under it (`description`: a role, an
email) that shrink with an ellipsis, and a chevron. It opens a menu of `items`, each `{ id, label, href?, icon?,
tone? }`: an item with `href` is a link that goes through `NasimProvider`'s router, one without it calls
`onAction(id)`; `tone: 'danger'` tints an item and moves it to the end behind a separator, whatever its place in
the list. The menu is named after the button, so the screen reader hears the person and then «منو». It fills the
width it is given and opens above (`placement` is React Aria's: `"top start"` by default, `"bottom end"` for a
bar), the width of the button at least. It is meant for `AppShell`'s `sidebarFooter`, which the phone's drawer
shows too.

```tsx
<AccountMenu
  name={me.name}
  description={t.role.owner}
  avatarSrc={me.photoUrl}
  items={[
    { id: 'security', label: t.account.security, href: '/security', icon: <LockIcon /> },
    { id: 'logout', label: t.account.logout, tone: 'danger' },
  ]}
  onAction={(id) => id === 'logout' && logout()}
/>
```

### `StaticTable`

Read-only rows for a page that is text, not a tool (a bank list, a comparison of methods): plain markup in
HeroUI's table skin, so a Server Component draws it with no client JavaScript. `caption` names the table and
the region that scrolls it (the region takes focus, so a keyboard user can scroll a wide table), `columns`
are the headings, and each of `rows` is `{ id, cells }` with one cell per column; the first cell of a row is
its header. `className` lands on the `<table>` (a `min-w-[36rem]` keeps a wide table from squeezing). A list a
person works through is `DataTable`.

```tsx
<StaticTable caption={t.banks.caption} columns={[t.banks.bank, t.banks.status]} rows={banks.map((bank) => ({ id: bank.code, cells: [bank.name, <StatusChip tone="info" label={bank.status} />] }))} className="min-w-[22rem]" />
```

### `ColumnChart`, `BarTable`

Charts in plain SVG and HTML, no chart library, written so that no number is only a picture. `ColumnChart`
draws one bar per `points` entry (`{ key, label, value, tooltip }`): `value` is only the bar's height, the
exact figure is `tooltip` (SVG `<title>`) and a data table behind a disclosure (`table`: `showLabel`, `label`,
`columns`, `rows` whose first cell is the row header). `summary` is what a screen reader hears for the
picture (the range, the busy days, the peak); `showSummary` writes it under the title, `note` explains the
scaling, `tone` is `"accent"`, `"success"` or `"info"`, and `empty` replaces the plot when no value is above
zero. The plot is left to right whatever the page direction, with the first and last label at its ends.
`BarTable` is a table that is also a chart: each row of `rows` (`{ key, label, value, cells }`) has its label,
a bar in proportion to `value` and its exact `cells`; `hideTitle` keeps the title for screen readers only,
`barFrom="sm"` drops the bars on a phone, `regionLabel` names the scrolling region. Both are
server-renderable and take `data-testid` (the chart's table and summary add `-table` and `-summary`).

```tsx
<ColumnChart data-testid="daily" title={t.sales.daily} summary={summaryText} points={days.map((day) => ({ key: day.id, label: day.short, value: day.count, tooltip: `${day.full}: ${day.count}` }))} empty={t.sales.noData} table={{ showLabel: t.sales.showTable, label: t.sales.tableLabel, columns: [t.sales.day, t.sales.count], rows: days.map((day) => ({ key: day.id, cells: [day.full, day.count] })) }} />
<BarTable title={t.sales.byCard} labelHeader={t.sales.card} valueHeaders={[t.sales.count, t.sales.amount]} rows={cards.map((card) => ({ key: card.id, label: card.name, value: card.rial, cells: [card.count, card.amount] }))} empty={t.sales.noData} />
```

### `AreaChart`

A time series in plain SVG and HTML, one or two series, with no chart library and no number that is only a
picture. `title` captions it and `summary` is what a screen reader hears for the plot (the range, the peak, the
latest figure; `showSummary` writes it under the title too). `ticks` are the steps of time, oldest first, each
`{ key, label, title }`: `label` is the short word on the axis (an empty one leaves that step unlabelled, so the
screen picks which days to name and none collide) and `title` is the step in full, the tooltip's heading and the
table's row header. `series` is one `{ key, label, points, tone? }` or two, each point `{ value, text }`: `value` is
only the height (a `null` is a gap, never a zero) and `text` the exact figure («۱٬۲۰۰٬۰۰۰ تومان»), so the figures
are the screen's own words and no formatter function crosses the server boundary. The second series is drawn
dashed and in the neutral tone (the previous period), and two series get a legend, so they differ by more than
colour. `yTicks` (`{ value, label }`) draw gridlines and their labels in the app's units; zero is always the
baseline, so the chart starts at zero. `empty` replaces the plot when no value is above zero, `note` explains the
scaling, `size` is `"md"` or `"lg"`.

The latest point of every series wears a dot. The plot is one focus stop: hover or touch picks the nearest step,
and the arrow keys, Home and End move between steps (Escape closes), showing a tooltip with the step's title and
the exact figures and a cursor line. A keyboard move is also announced politely, and the plot is described by a
hint of the keys. `table` (`showLabel`, `label`, `stepHeader`) is required: every figure is also a table behind a
disclosure, built from `ticks` and `series`. As in `ColumnChart` the plot is left to right whatever the page
direction (the arrow keys follow the picture), with the first label at the left end. Layout after HeroUI Pro's
Area Chart and the analytics dashboard (gridlines and a muted axis, a dashed hover cursor, a legend at the top).
A client component.

```tsx
<AreaChart
  data-testid="daily"
  title={t.sales.daily}
  summary={summaryText}
  showSummary
  ticks={days.map((day) => ({ key: day.id, label: day.axis, title: day.full }))}
  series={[
    { key: 'now', label: t.sales.thisMonth, points: days.map((day) => ({ value: day.total, text: formatToman(day.total) })) },
    { key: 'before', label: t.sales.lastMonth, points: before.map((day) => ({ value: day.total, text: formatToman(day.total) })) },
  ]}
  yTicks={[0, 2e6, 4e6].map((value) => ({ value, label: axisLabel(value) }))}
  empty={t.sales.noData}
  table={{ showLabel: t.sales.showTable, label: t.sales.tableLabel, stepHeader: t.sales.day }}
/>
```

### `DataTable`, `Pager`

A table on React Aria's grid (keyboard navigation, right to left), written for a list a person pages through.
`columns` are `{ id, header, cell, align?, isRowHeader?, allowsSorting?, className? }` (`align: "end"` for
amounts; exactly one column is the `isRowHeader`), `rows` and `getRowId` give the rows, and `status` is
`"loading"` (skeleton rows), `"error"` (the error state with `onRetry`, or your own `errorState`) or `"ready"`
(the rows, or the empty state made from `emptyTitle`, `empty`, `emptyIcon` and `emptyAction`). `ariaLabel`
names it. A wide table scrolls sideways in its own region. `pagination` adds a pager under it.

On a phone a table is hard to read, so `cards="sm"` or `cards="md"` turns every row into a card below that
breakpoint: the `isRowHeader` column is the title, the other columns are labelled values, each on one line with
its label at the start and its value at the end (a long value drops under its label; leave a column out with
`hideOnCard: true`), and the columns marked `isActions: true` are what can be done to the row. A `RowActions`
kebab is one small control, so it sits in the card's header at the end, beside the title and the checkbox; real
buttons go in a footer under a rule (a card whose action cells all render nothing has no footer at all, not an
empty bar). Only one layout is
in the DOM at a time (the server and the first client render draw the table), so text and roles are never
duplicated; the cards are a list named by `ariaLabel` with `data-testid="data-cards"`. `useIsNarrow` takes
`"sm"` or `"md"` and is the same media query as a hook, for a screen that swaps its own layout (a filter bar
that collapses); the server and the first client render say no.

```tsx
<DataTable ariaLabel={t.invoices.title} columns={columns} rows={rows} getRowId={(row) => row.id} status={status} onRetry={refetch} emptyTitle={t.invoices.emptyTitle} empty={t.invoices.empty} />
```

A list a person works on, as in an admin panel, adds the props below; each is optional and a table without
them is the one above.

**Choosing rows.** `selectedKeys` (a `ReadonlySet<string>` of row ids) and `onSelectionChange(keys)` turn
selection on: a checkbox in every row and a select-all in the header, which is indeterminate while only part
of the page is chosen and works from the keyboard (Space on a row chooses it). A chosen row is tinted. The set
holds ids and never `"all"`: select all hands over the ids of the rows on the page. On cards each card has
its checkbox, named after the card, and a select-all stands above the list. Show a bulk bar with `ActionBar`.
`isRowSelectable={(row) => boolean}` leaves a row out (a twin of another receipt): its checkbox is drawn
disabled, select-all passes over it, and it still opens with `onRowAction`. A button or a link inside a cell
(a copy button) keeps keyboard focus when it takes it; the grid does not hand it to a row.

**Ordering.** Mark a column `allowsSorting: true` (its `header` is a string: it is what a screen reader hears
when the order changes) and pass `sortDescriptor` (`{ column, direction }`, the type `SortDescriptor`, with
`direction` `"ascending"` or `"descending"`) and `onSortChange`. The first press on a header sorts
ascending and the next flips it; the header says so with `aria-sort`, a chevron and a live announcement. The
table never sorts the rows: the screen (or the server) does. Cards have no headers, so a screen offers
`ListToolbar.Sort` with the same descriptor.

**Opening a row.** `onRowAction(id)` is called for a press on a row or Enter on it (on a card, a press on
its title, which is a button). A button or a link inside a cell keeps its own press and opens nothing, and
while rows are chosen a press on a row chooses it instead, as in React Aria.

**A fixed height.** `maxHeight` (a CSS length such as `"32rem"`) makes the rows scroll inside a region that
tall while the header stays in view, and the footer stays under it. Cards ignore it: the page scrolls.

**Pages.** `pagination` is `{ page, pageCount, onPageChange }` for a list that knows its page count, which
draws `Pager` under the rows when there is more than one page. With `{ page, total, pageSize, onPageChange }`
the table knows the rows it holds in all and draws a summary in words («۱ تا ۲۰ از ۳۲۰», polite live), numbered
pages with ellipses (the number of buttons stays the same wherever the page is, and a phone gets fewer so
44px buttons fit) and, with `pageSizes` (`[10, 20, 50]`) and `onPageSizeChange(size)`, a select labelled
«تعداد در صفحه». The screen resets the page to 1 when the size changes. The type is `DataPagination`.

```tsx
const [sort, setSort] = useState<SortDescriptor>({ column: 'createdAt', direction: 'descending' });
const [selected, setSelected] = useState<ReadonlySet<string>>(new Set());

<DataTable ariaLabel={t.users.title} columns={columns} rows={users} getRowId={(user) => user.id} status={status} cards="md" maxHeight="70dvh" sortDescriptor={sort} onSortChange={setSort} selectedKeys={selected} onSelectionChange={setSelected} onRowAction={(id) => router.push(`/users/${id}`)} pagination={{ page, total, pageSize, pageSizes: [10, 20, 50], onPageChange: setPage, onPageSizeChange: changeSize }} />;
```

`Pager` is the previous and next buttons with the page in words, «صفحه ۲ از ۵»: pass `pageCount`, or
`hasNext` for a cursor-paged list that does not know its end, and `isFetching` to say it is refreshing.

```tsx
<Pager page={page} hasNext={Boolean(nextCursor)} onPrevious={back} onNext={forward} />
```

### `RowActions`

The kebab of a row: one icon button that opens a menu of what can be done to that row. `label` names the button
after the row (the table has one in every row, so a screen reader needs the row in it; without it the name is
«اقدام‌های بیشتر»), `items` are `{ id, label, icon?, tone? }` and `onAction(id)` receives the id chosen, after
which the menu closes. An item with `tone: "danger"` is tinted and goes last, after a separator, whatever its
place in `items`. It sits in a cell of the actions column (`isActions: true`), where it opens no row.

```tsx
<RowActions
  label={t.users.actionsOf(user.name)}
  items={[
    { id: 'edit', label: t.users.edit, icon: <PencilIcon /> },
    { id: 'delete', label: t.users.delete, tone: 'danger' },
  ]}
  onAction={(id) => run(id, user)}
/>
```

### `ListToolbar`

The bar above a list, made of parts the screen picks: a search, status tabs with counts, facet buttons that wear
their chosen value, a sort menu, a column menu, a refresh button with auto-refresh and the primary action at the
end. `ListToolbar` is the frame, a named group (`label`) that is one row on a desktop and wraps on a phone, where
the search takes a row of its own; each part is a member and the screen uses only the ones it needs, in the order it
wants them. `isDisabled` on the frame switches off every part at once (through context, not by hand), except the
`Actions`, which are the screen's own buttons.

- `ListToolbar.Search`: `label`, `value`, `onChange`, `placeholder?` (a `SearchBox`).
- `ListToolbar.Tabs`: `label`, `items` (`{ id, label, count? }`, the count in Persian digits after the name:
  «فعال ۱٬۲۰۰»), `value`, `onChange(id)`. Controlled.
- `ListToolbar.Facet`: `label` (the facet's name), `options` (`{ id, label }`), `value`, `onChange`. The button
  shows the chosen value instead of the name («سرور» becomes «آلمان ۱», its name for a screen reader
  «سرور: آلمان ۱») and is tinted while a value is on, with a clear button beside it. The menu starts with «همه»
  (`allLabel` words it), which clears the facet. One value is `value: string | null`; `selectionMode="multiple"`
  makes it `value: string[]`, shown as the first value and a count of the rest.
- `ListToolbar.Sort`: `options`, `value` (a `SortDescriptor`, the same one `DataTable` takes, so a header and the
  menu drive one state: a card list has no headers), `onChange`, `label?`. The menu lists the columns and then the
  two directions; a column picked keeps the direction.
- `ListToolbar.Columns`: `options`, `value` (the ids shown), `onChange(ids)`, `label?`. The screen passes the
  shown columns to `DataTable`; at least one stays on.
- `ListToolbar.Refresh`: `onRefresh`, `isRefreshing?` (the button says «در حال به‌روزرسانی», a polite status
  says it too and a press is ignored), and with `interval` (seconds, 0 off) and `onIntervalChange(seconds)` a menu
  of off, 15, 30 and 60 seconds. The screen owns the timer. Under 640px the button keeps only its icon.
- `ListToolbar.Actions`: the end slot; whatever it holds is pushed to the end.

```tsx
const [seconds, setSeconds] = useState(0);
useEffect(() => {
  if (!seconds) return;
  const timer = setInterval(refetch, seconds * 1000);
  return () => clearInterval(timer);
}, [seconds, refetch]);

<ListToolbar label={t.users.filters} isDisabled={status === 'loading'}>
  <ListToolbar.Search label={t.users.search} value={query} onChange={setQuery} />
  <ListToolbar.Tabs label={t.users.statuses} items={statusTabs} value={statusTab} onChange={setStatusTab} />
  <ListToolbar.Facet label={t.users.server} options={servers} value={server} onChange={setServer} />
  <ListToolbar.Facet label={t.users.protocol} options={protocols} selectionMode="multiple" value={chosenProtocols} onChange={setChosenProtocols} />
  <ListToolbar.Sort options={sortable} value={sort} onChange={setSort} />
  <ListToolbar.Columns options={allColumns} value={shownColumns} onChange={setShownColumns} />
  <ListToolbar.Refresh onRefresh={refetch} isRefreshing={isFetching} interval={seconds} onIntervalChange={setSeconds} />
  <ListToolbar.Actions>
    <Button onPress={create}>{t.users.create}</Button>
  </ListToolbar.Actions>
</ListToolbar>;
```

### `ActionBar`

A pill at the bottom centre of the screen while rows are selected: the count in words, the actions on them and a
button that clears the selection. `count` (rows selected) decides whether it shows, `label` is the count in words
from the screen's strings, `onClear` clears the selection, and the children are the actions: `ActionBar.Action`
(`label`, `icon?`, `tone?: "danger"`, `isDisabled?`, `onPress`) or any button. Put the destructive action
last; `tone="danger"` tints it. Under 640px an action that has an icon shows only the icon (its words stay for a
screen reader), so a row of them fits a phone; every control is 44px under a coarse pointer.

It is a toolbar, named «اقدام‌های گروهی», so the arrow keys move along its buttons. It sits above the home
indicator, Telegram's bars and a bar of the host (`useBottomBar`), like the toasts, and lets presses through
around the pill. It appears with a short rise and fade (opacity and translate only, none under reduced motion);
closed it is invisible and out of the tab order. The count is said in a polite status. It registers as a layer
(`useRegisterOverlay`), so the host's Back button calls `onClear`; so do Escape inside the bar and its button,
and focus goes back to where it was before it entered the bar. Pair it with `DataTable` selection:

```tsx
<DataTable ariaLabel={t.users.title} columns={columns} rows={users} getRowId={(user) => user.id} status={status} selectedKeys={selected} onSelectionChange={setSelected} />
<ActionBar count={selected.size} label={t.users.selected(selected.size)} onClear={() => setSelected(new Set())}>
  <ActionBar.Action label={t.users.disable} icon={<PauseIcon />} onPress={disable} />
  <ActionBar.Action label={t.users.delete} icon={<TrashIcon />} tone="danger" onPress={askToDelete} />
</ActionBar>
```

### `Modal`

A centred dialog for a form or a detail; `BottomSheet` is the phone's. `title`, `children`, `footer` (the
cancel first, the main action last), `size` (`"xs"` to `"lg"`). `isDismissable={false}` for a form with
unsaved input: the backdrop and Escape close nothing; `isBusy` does the same while a request runs. It
registers as a layer, so Telegram's Back button closes it. Its corner button is named «بستن پنجره», so a
«بستن» in the footer is the only button of that name.

```tsx
<Modal isOpen={open} onOpenChange={setOpen} title={t.team.invite} footer={<Button onPress={send}>{t.team.send}</Button>}>
  {fields}
</Modal>
```

### `Tabs`

Tabs on React Aria: `label` names the list, `items` are `{ id, label, content?, isDisabled? }`, and the
selection is controlled with `selectedKey` and `onSelectionChange(id)` or left to `defaultSelectedKey`.
Leave `content` out when the page shows what the tab selects (route tabs). HeroUI's buttons that scroll a
long list are named in Persian here, not in its English.

```tsx
<Tabs label={t.settings.sections} items={sections} selectedKey={section} onSelectionChange={setSection} />
```

### `NavTabs`

Sibling pages that share one menu entry (invoices, payment links and the sales report under «فروش»),
switched with a tab-looking bar. Each tab is a link to a page of its own inside a `<nav>` named by
`label`, and `isCurrent` (the app knows the route) marks the page on screen with `aria-current`; `Tabs` is
for panels on one page. Links navigate through `NasimProvider`.

```tsx
<NavTabs label={t.sales.sections} items={sections.map((tab) => ({ href: tab.href, label: tab.label, isCurrent: tab.href === pathname }))} />
```

## Forms

React Hook Form + Zod. Fields read the form from context, validate with `validationBehavior="aria"`
(the resolver owns the rules) and show the resolver's message under the field. Loading `FormRoot` also
sets Zod's Persian locale as a fallback (a page without a form does not ship Zod); a schema should still
pass its own messages.

React Hook Form belongs to `FormRoot` alone. A field given a `name` reads its value through the form, and
a field given `value` and `onChange` does not, so a page whose fields are all controlled never downloads
React Hook Form. A field with a `name` and no `FormRoot` around it throws an error that says so.

Every field works in one of two ways, told by its props:

- **In a form**: pass `name`, the key in the form values. The field reads and writes the value itself.
- **Controlled**: pass `value` and `onChange` (and `errorMessage` for the text under the field). For a
  filter bar, a dialog, a flow that keeps its own state, where a form library would only be in the
  way. The field draws the same, validates nothing itself, and is invalid exactly while
  `errorMessage` is set.

```tsx
<TextField label={t.filters.search} value={query} onChange={setQuery} />
<SelectField label={t.filters.status} value={status} onChange={setStatus} options={statuses} />
```

Every field also takes `className` and `data-testid` for its root element.

Help for a field is its `description`, never a paragraph beside it and never an `aria-describedby` passed
to the field (a field takes neither: it would be dropped). The description is tied to the control for a
screen reader, also when it appears after the field did (the hint of the option just chosen is
`description={hints[choice]}`).

### `FormRoot`

```tsx
const form = useForm<Values>({ resolver: zodResolver(schema) });

<FormRoot form={form} onSubmit={(values) => mutate(values)} className="flex flex-col gap-4">
  <TextField name="email" type="email" dir="ltr" label={t.account.email} isRequired />
  <SubmitButton>{t.common.confirm}</SubmitButton>
</FormRoot>;
```

`onSubmit` receives validated values. A submit while one is still running is ignored (this also
covers a single-field form, where Enter submits implicitly). Handle failures inside `onSubmit`
(call `mutate`, not `mutateAsync`).

### `FormFields`

The fields of a form whose submit is not a button inside it: Telegram's MainButton, a sheet's footer.
Fields bind by `name` exactly as in `FormRoot`, but no `<form>` is drawn, so Enter in a field submits
nothing, and a small form of its own (a discount code with its own apply button) may sit inside. The
owner submits with `form.handleSubmit(...)` and guards a second press itself.

```tsx
<BottomSheet footer={<Button onPress={() => void submit()}>{t.checkout.pay}</Button>}>
  <FormFields form={form}>
    <CodeField />
    <SwitchField name="useWallet" label={t.checkout.useWallet} />
  </FormFields>
</BottomSheet>
```

### `TextField`

`label`, `description`, `isRequired`, `isDisabled`, plus `type`, `placeholder`, `autoComplete`,
`inputMode`, `maxLength`, `minLength`, `autoFocus`, `spellCheck`. `dir="ltr"` for emails, usernames and
phone numbers (Latin text types and aligns correctly). The label may be a node (a visually hidden one,
when the screen already names the field).

### `SecretField`

A key, a token or a password the server keeps and never shows again: an API key of a payment gateway, a bot
token. It is write-only. The field never receives the stored value, only `isSet` (the server has one) and
`maskedHint` (what the server chooses to show of it, `••••1234`); there is no prop for the secret itself.

```tsx
<SecretField name="apiKey" label={t.gateway.apiKey} description={t.gateway.apiKeyHint} isSet={gateway.hasApiKey} maskedHint={gateway.apiKeyHint} />
```

It has three states, each a different thing to see:

- **Not set** (`isSet={false}`): an input, with an eye button that shows what is typed.
- **Set**: a «ثبت شده» chip and the masked hint, with «جایگزینی» and «پاک کردن». No input is in the page at all.
- **Replacing**: «جایگزینی» opens an empty input (never pre-filled) with the eye button and an «انصراف» that
  returns to the set state. Pressing «پاک کردن» marks the secret as to be cleared («پس از ذخیره پاک می‌شود»)
  with a «بازگرداندن» that undoes it, until the form is saved.

The input is a password input, `dir="ltr"` and monospace, with `autocomplete="new-password"` so the browser does
not fill in a password it saved for the site, and no spell check. The eye is named «نمایش مقدار» or «پنهان کردن
مقدار» and the text is hidden again whenever the field is left in the stored state. The two actions are named
with the field (`aria-labelledby` the button and the label: «جایگزینی کلید API»), so several of them on a page
are told apart. `isRequired` applies while nothing is stored.

What the form holds, and so sends, is one of three things:

| Value        | Means                            | A schema                                                 |
| ------------ | -------------------------------- | -------------------------------------------------------- |
| `undefined`  | Unchanged: send nothing          | `.optional()`                                            |
| `'some-key'` | The new text replaces the secret | `z.string().min(8)`                                      |
| `''`         | Clear the secret                 | `z.union([z.literal(''), z.string().min(8)]).optional()` |

An empty box is `undefined`, never `''`: only the clear button writes an empty string, so an `''` in the values
is always a person's decision. The owner of a form turns it into its request (`''` to `null`, `undefined` left
out). After a save, give the field its new `isSet` and `maskedHint` and reset the form: a new hint ends
«replacing». Controlled, the same three values go through `value` and `onChange`, with `errorMessage` shown in
every state.

### `NumberField`

```tsx
<NumberField name="seats" label={t.plan.seats} minValue={1} maxValue={10} />
```

The value is a `number`, or `undefined` while the box is empty. Also `step` and `formatOptions`.
`hideSteppers` drops the − and + buttons for a number that is an identifier, not a quantity.
React Aria reports a number when the box is left or Enter is pressed; `reportWhileTyping` reports it on every
keystroke (Persian and Arabic digits read as numbers, an emptied box as `undefined`, a half-typed minus not at
all), for a price or a filter that follows what is typed.

### `SelectField`

```tsx
<SelectField name="plan" label={t.plan.label} options={[{ value: '30', label: t.plan.days30 }]} />
```

In a form the value is the chosen option's `value` string, or `undefined`; controlled, it is that string
or `null`. An option may be `isDisabled`. `placeholder` defaults to the Persian one.

### `TextAreaField`

A multi-line `TextField` for notes and messages: `name`, `label`, `description`, `isRequired`,
`isDisabled`, `rows` (4), `placeholder`, `maxLength`, `autoFocus`. The value is the text as typed,
line breaks included.

```tsx
<TextAreaField name="note" label={t.services.note} rows={3} />
```

### `SwitchField`

```tsx
<SwitchField name="renew" label={t.plan.autoRenew} description={t.plan.autoRenewHint} />
```

### `RadioGroupField`, `CheckboxGroupField`, `CheckboxField`

One of a few choices, any of a few, and one yes or no. Options are `{ value, label, description?,
isDisabled? }`: the label names the option and the description is read with it. The radio value is the
chosen `value`, the checkbox group's is the list of chosen values, and `CheckboxField`'s is a boolean; its
label is its children. A few words each: a choice that needs a price or a long line is `OptionCards`.

```tsx
<RadioGroupField name="mode" label={t.link.mode} options={[{ value: 'live', label: t.link.live }]} />
<CheckboxGroupField name="scopes" label={t.team.scopes} options={scopes} />
<CheckboxField name="agree">{t.terms.agree}</CheckboxField>
```

### `DateTimeField`

A date and a 24-hour time in the Persian calendar with Persian digits (HeroUI's date picker under
`fa-IR-u-ca-persian`). The value stays the Gregorian local `YYYY-MM-DDTHH:mm` a form validates and
converts, or an empty string for no date; a clear button empties it. The three names are the app's words:
`calendarLabel` (the popover), `timeLabel` (the time box in it) and `clearLabel`.

```tsx
<DateTimeField name="expiresAt" label={t.link.expiry} calendarLabel={t.link.calendar} timeLabel={t.link.time} clearLabel={t.link.clear} />
```

### `DateRangeField`

A range of days in the Persian calendar with Persian digits (HeroUI's date range picker and range calendar under
`fa-IR-u-ca-persian`), wrapped as `DateTimeField` is. The value is `DateRangeValue`, `{ start, end }` as Gregorian
`YYYY-MM-DD`, or `{ start: '', end: '' }` for none, which is what a form validates and converts; the field
shows the same days in the Persian calendar. It works in a form (`name`, the value is the object) or controlled
(`value`, `onChange`, `errorMessage`), like every field. The words are the app's: `calendarLabel` (the popover),
`clearLabel` (the button that empties it, shown while there is a range); the calendar's month buttons, year
button and the names of the two ends come from Nasim's Persian dictionary. The month buttons are Nasim's own
chevrons, turned in a right-to-left page.

`presets` are the app's quick choices under the field as a segmented group (`DateRangePreset`: `{ id, label, start,
end }`, so the app works out «امروز», «۷ روز», «این ماه» from its own date and its own words); `presetsLabel` names
the group (a radio group: arrow keys move between them). The preset whose days are the field's value is
chosen; pressing it again changes nothing, and picking other days in the calendar leaves none chosen. The
presets share the field's `isDisabled` and keep a 44px target on a coarse pointer. HeroUI Pro's Segment, a time
range control above the analytics page (7D, 30D, 90D), was the model; the group is the free
`ToggleButtonGroup`.

```tsx
const presets: DateRangePreset[] = [
  { id: 'today', label: t.range.today, start: iso(today), end: iso(today) },
  { id: 'week', label: t.range.week, start: iso(daysAgo(6)), end: iso(today) },
];

<DateRangeField label={t.report.period} value={period} onChange={setPeriod} calendarLabel={t.report.calendar} clearLabel={t.report.clear} presets={presets} presetsLabel={t.report.presets} />;
```

### `MultiSelect`

Several of a list's options, for facet-like choices such as the panels a service may use: a combo box that searches
as the person types and keeps choosing (HeroUI's `ComboBox` with `selectionMode="multiple"`, its list marking what
is chosen and a «موردی پیدا نشد.» when nothing matches), and what is chosen below it as tags (`TagGroup`), each
with its own remove button and one «پاک کردن همه». `options` are `{ value, label, isDisabled? }`; the value is the
array of the chosen `value`s in the order they were chosen (in a form by `name`, or controlled with `value`,
`onChange` and `errorMessage`; undefined counts as none). Remove buttons are named «حذف» followed by the tag (HeroUI's
own is English), Delete and Backspace remove the focused tag, `placeholder` defaults to «جست‌وجو و انتخاب»,
`isDisabled` disables the box, the tags and the clear button together, and under a coarse pointer a remove
button keeps its look but has a 44px hit area (`tokens.css`). The words are `t.multiSelect`.
While the list is open the page behind it is hidden from a screen reader, as with any popover.

```tsx
<MultiSelect name="panels" label={t.service.panels} description={t.service.panelsHint} options={panels.map((panel) => ({ value: panel.id, label: panel.name }))} />
<MultiSelect label={t.filters.panels} value={panelIds} onChange={setPanelIds} options={panelOptions} placeholder={t.filters.searchPanels} />
```

### `HexColorPicker`

A swatch button that opens a colour area, a hue slider and a row of ready-made colours, and reports an
upper-case `#RRGGBB`. Controlled only: `value`, `onChange`, `presets`, `fallback` (what it opens on when
`value` is not a colour) and the three names `label`, `hueLabel` and `presetsLabel`.

```tsx
<HexColorPicker value={brand} onChange={setBrand} label={t.brand.pick} hueLabel={t.brand.hue} presetsLabel={t.brand.presets} presets={PRESETS} fallback="#0b905d" />
```

## Primitives

Straight re-exports from HeroUI unless marked. Use them with HeroUI's compound anatomy; the
HeroUI docs for 3.2.7 apply, except where a note says otherwise.

Wrapped, with Persian defaults or fixes:

| Export        | What the wrapper adds                                                                                                                     |
| ------------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| `Spinner`     | `aria-label` in Persian. Inside a button: `<Spinner color="current" size="sm" />`.                                                        |
| `CloseButton` | `aria-label` in Persian.                                                                                                                  |
| `Select`      | Persian placeholder. Parts: `Select.Trigger`, `.Value`, `.Indicator`, `.ClearButton`, `.Popover`.                                         |
| `LinkButton`  | A router-aware link styled as a button: `variant`, `size`, `fullWidth`, `isIconOnly`; `target="_blank"` adds `rel="noopener noreferrer"`. |

Re-exported:

| Export                                                                | Notes                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| --------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `Button`                                                              | `variant`, `size`, `isPending` (pass a render function child to show a `Spinner`)                                                                                                                                                                                                                                                                                                                                                                                                    |
| `ButtonGroup`                                                         | Joins buttons.                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| `Alert`                                                               | `Alert.Indicator`, `.Content`, `.Title`, `.Description`. No close part.                                                                                                                                                                                                                                                                                                                                                                                                              |
| `Avatar`, `Badge`                                                     | `Badge.Anchor` places a badge on an avatar.                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| `Card`                                                                | `Card.Header`, `.Title`, `.Description`, `.Content`, `.Footer`.                                                                                                                                                                                                                                                                                                                                                                                                                      |
| `Chip`                                                                | `color`, `variant="soft"`.                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| `Checkbox`, `Input`, `TextArea`, `Label`, `Description`, `FieldError` | Field parts; use `TextField` and friends for forms.                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| `ColorPicker`, `ColorArea`, `ColorSlider`, `ColorSwatch`              | A colour chosen by eye: `ColorPicker` (`value` as `#rrggbb` or a `Color`, `onChange(color)`) holds `.Trigger` (a `ColorSwatch` of its colour) and `.Popover` with a `ColorArea` (`colorSpace="hsb"`, `xChannel="saturation"`, `yChannel="brightness"`, `.Thumb`) and a hue `ColorSlider` (`.Track`, `.Thumb`). Name the trigger, the area and the slider with `aria-label`. `color.toString("hex")` is upper case. React Aria's colour names and labels are Persian (`t.reactAria`). |
| `Disclosure`, `DisclosureGroup`                                       | Expandable sections.                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| `Dropdown`, `ListBox`, `Popover`                                      | Menus and lists; `ListBox.Item` takes `id` and `textValue`.                                                                                                                                                                                                                                                                                                                                                                                                                          |
| `Link`                                                                | Text link; navigates in-app through `NasimProvider`'s `navigate`.                                                                                                                                                                                                                                                                                                                                                                                                                    |
| `Meter`, `ProgressBar`                                                | Usage and progress bars.                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| `Separator`, `Skeleton`, `Surface`                                    | Layout and loading shapes.                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| `Switch`                                                              | An on/off setting that acts at once (auto-renew). In a form use `SwitchField`.                                                                                                                                                                                                                                                                                                                                                                                                       |
| `Tooltip`                                                             | Put the trigger directly inside: `<Tooltip><Button>…</Button><Tooltip.Content>…</Tooltip.Content></Tooltip>`.                                                                                                                                                                                                                                                                                                                                                                        |
| `toast`                                                               | `toast("…")`, `toast.success`, `toast.danger`. An action button does not close its toast: call `toast.close(id)` in `onPress`.                                                                                                                                                                                                                                                                                                                                                       |
| `useMediaQuery`, `useOverlayState`                                    | Hooks. Types `ButtonProps` and `Key` are exported too.                                                                                                                                                                                                                                                                                                                                                                                                                               |

### Not exported yet

HeroUI words some labels itself, in English. Three of those are named in Persian inside a Nasim part, and
HeroUI's own components stay behind it: `Tabs` (its scroll buttons; use Nasim's `Tabs`), the calendar (its year
button and month buttons, named and turned inside Nasim; use `DateTimeField` or `DateRangeField`) and `Tag`
(its remove button says «Remove tag»; use `MultiSelect`, which names it in Persian), so HeroUI's `Tabs`,
`Calendar`, `RangeCalendar`, `DatePicker`, `DateRangePicker`, `TimeField`, `ComboBox`, `TagGroup` and `Tag` are
not exported. These still wait for a Persian wrapper before first use: `Pagination` (`DataTable`'s numbered
pages are built on it, named in Persian there, and `Pager` is the simple control) and `Autocomplete`. When you
add one, check it with the language switched to Persian and with axe.

## Strings

`src/strings/` holds only the words Nasim itself shows: `t.common` (close, cancel, retry, copy and the
like), `t.state` (the error state), `t.stepper`, `t.sortableList`, `t.secret` (the secret field's chip, actions and eye),
`t.trend` (a change in words), `t.areaChart` (the chart's keyboard hint and «بدون داده»), `t.breadcrumbs` and `t.kbd` (the landmark's name and the key names), `t.multiSelect` (the placeholder, the remove and clear buttons and the empty list), `t.bank` and `t.bankCard` (the bank names and the card's labels), `t.usageBar` (the bar's status words), `t.viewer` (the viewer's controls and states), `t.toast`, and `t.reactAria` (React Aria's dictionary).
A screen's own copy is the app's: it reaches a component as a prop, and the screen reads it from its own
strings module. A theme picker, for one, says «روشن» and «تیره» in the app's words.

Keep Persian copy short, friendly and actionable (what happened, what to do next), and keep
zero-width non-joiners where the script needs them («می‌شود», «پیش‌فرض»).

## Adding a component

1. Read HeroUI's page and demos for it. Wrap it in `primitives/` only to add a Persian default or
   a fix; otherwise re-export it from `primitives/index.ts`.
2. A composite goes in `composites/`, a form field in `forms/`: one idea per file (split it when it
   stops being one, not at a line count), variants with `tv`, copy from `t`.
3. Export it from `index.ts`, document it here, add its strings, and note it in `CHANGELOG.md`.
4. Test it in `__tests__/`: render in light and dark with `renderNasim` and check
   `expectNoViolations`; add keyboard and Persian-label assertions where they apply.
5. `bunx nx run-many -t typecheck test -p @nyxon/nasim` and `bunx prettier --check libs/nasim`. A comment
   is one line of at most 100 characters that says why.
6. A module that holds state, effects, context or an event handler starts with `'use client'`; one that
   only draws from its props does not, so a Server Component can render it (see Setup).
