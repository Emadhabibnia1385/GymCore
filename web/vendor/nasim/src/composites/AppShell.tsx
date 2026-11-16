'use client';

import { Drawer } from '@heroui/react';
import { type ReactNode, useEffect, useId, useRef, useState } from 'react';
import { Link } from 'react-aria-components';
import { tv } from 'tailwind-variants';
import { MenuIcon } from '../icons';
import { Button, Tooltip } from '../primitives';
import { useRegisterOverlay } from '../providers/overlays';
import { formatNumber, t } from '../strings';

const BADGE_CAP = 99;

const shell = tv({
  slots: {
    root: 'flex min-h-dvh bg-background text-foreground',
    aside:
      'sticky top-0 hidden h-dvh w-60 shrink-0 flex-col border-e border-border bg-surface lg:flex',
    brand: 'flex min-h-16 items-center px-4',
    nav: 'flex-1 overflow-y-auto px-3 py-2',
    footer: 'border-t border-border p-3',
    column: 'flex min-w-0 flex-1 flex-col',
    // Under Telegram's own bar or a notch the header grows by the inset instead of sliding under it.
    header:
      'sticky top-0 z-20 flex min-h-14 items-center gap-2 border-b border-border bg-surface px-page pt-(--nasim-safe-top) sm:min-h-16 sm:gap-3 sm:pl-[max(1.5rem,var(--nasim-safe-left))] sm:pr-[max(1.5rem,var(--nasim-safe-right))]',
    lead: 'flex min-w-0 flex-1 items-center',
    topbar:
      'ms-auto flex min-w-0 flex-wrap items-center justify-end gap-2 py-1.5',
    main: 'mx-auto w-full flex-1 px-page pt-6 pb-[calc(1.5rem+var(--nasim-safe-bottom))] focus:outline-none sm:pl-[max(1.5rem,var(--nasim-safe-left))] sm:pr-[max(1.5rem,var(--nasim-safe-right))]',
    groups: 'flex flex-col gap-3',
    groupLabel: 'px-3 pb-1 text-xs font-medium text-muted',
    list: 'flex flex-col gap-0.5',
    link: 'relative flex min-h-9 items-center gap-3 rounded-md px-3 py-1.5 text-sm font-medium no-underline outline-none transition-colors pointer-coarse:min-h-11 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus',
    mark: 'absolute inset-y-2.5 start-1 w-1 rounded-full bg-accent',
    badge:
      'ms-auto inline-flex h-5 min-w-5 shrink-0 items-center justify-center rounded-full bg-accent px-1.5 text-xs font-semibold text-accent-foreground tabular-nums',
  },
  variants: {
    current: {
      true: { link: 'bg-surface-tertiary text-foreground' },
      false: {
        link: 'text-muted hover:bg-surface-secondary hover:text-foreground',
      },
    },
    width: {
      contained: { main: 'max-w-7xl' },
      full: { main: 'max-w-none' },
    },
  },
  defaultVariants: { width: 'contained' },
});

type NavItem = {
  href: string;
  label: string;
  /** Decorative; the label is the name. */
  icon?: ReactNode;
  /** The app knows the route: the item of the page on screen. */
  isCurrent?: boolean;
  /** How many things wait here: a pill at the item's end; nothing for zero or none. */
  badge?: number;
};

type NavGroup = {
  id: string;
  /** Names the group on screen and for a screen reader. */
  label: string;
  items: NavItem[];
};

type AppShellProps = {
  /** The mark or wordmark: at the top of the sidebar and in the phone's bar. */
  brand: ReactNode;
  /** Names the navigation landmark. */
  navLabel: string;
  /** A flat list, or groups under their labels (a group with no items is left out). */
  nav: NavItem[] | NavGroup[];
  /** Reads a badge to a screen reader, given the count in Persian digits; defaults to «۳ مورد در انتظار». */
  badgeLabel?: (count: string) => string;
  /** The bar's start: a breadcrumb trail or a title. It replaces the brand in the phone's bar. */
  header?: ReactNode;
  /** The page's width: capped and centred by default, or the whole width beside the sidebar. */
  contentWidth?: 'contained' | 'full';
  /** The bar's end: page actions, a merchant switcher, an environment badge. */
  topbar?: ReactNode;
  /** Under the navigation: the person's menu, the attribution. */
  sidebarFooter?: ReactNode;
  /** Above the page: an offline notice, a sandbox warning. */
  banner?: ReactNode;
  children: ReactNode;
};

const isGrouped = (nav: NavItem[] | NavGroup[]): nav is NavGroup[] =>
  nav.length > 0 && 'items' in nav[0]!;

function ItemList({
  items,
  badgeLabel,
  onNavigate,
}: {
  items: NavItem[];
  badgeLabel: (count: string) => string;
  onNavigate?: () => void;
}) {
  const id = useId();
  return (
    <ul className={shell().list()}>
      {items.map((item, index) => {
        const slots = shell({ current: Boolean(item.isCurrent) });
        const count = item.badge && item.badge > 0 ? item.badge : 0;
        const shown = formatNumber(Math.min(count, BADGE_CAP));
        const note = `${id}-${index}`;
        return (
          <li key={item.href}>
            <Link
              href={item.href}
              onPress={onNavigate}
              aria-current={item.isCurrent ? 'page' : undefined}
              aria-describedby={count ? note : undefined}
              className={slots.link()}
            >
              {item.icon ? (
                <span aria-hidden className="shrink-0">
                  {item.icon}
                </span>
              ) : null}
              <span className="line-clamp-2 min-w-0 leading-snug">
                {item.label}
              </span>
              {count ? (
                <span aria-hidden className={slots.badge()}>
                  {count > BADGE_CAP ? `${shown}+` : shown}
                </span>
              ) : null}
              {item.isCurrent ? (
                <span aria-hidden className={slots.mark()} />
              ) : null}
            </Link>
            {count ? (
              <span id={note} className="sr-only">
                {badgeLabel(formatNumber(count))}
              </span>
            ) : null}
          </li>
        );
      })}
    </ul>
  );
}

function NavList({
  nav,
  badgeLabel,
  onNavigate,
}: {
  nav: NavItem[] | NavGroup[];
  badgeLabel: (count: string) => string;
  onNavigate?: () => void;
}) {
  const id = useId();
  const slots = shell();
  if (!isGrouped(nav)) {
    return (
      <ItemList items={nav} badgeLabel={badgeLabel} onNavigate={onNavigate} />
    );
  }
  return (
    <div className={slots.groups()}>
      {nav
        .filter((group) => group.items.length > 0)
        .map((group) => (
          <div
            key={group.id}
            role="group"
            aria-labelledby={`${id}-${group.id}`}
          >
            <p id={`${id}-${group.id}`} className={slots.groupLabel()}>
              {group.label}
            </p>
            <ItemList
              items={group.items}
              badgeLabel={badgeLabel}
              onNavigate={onNavigate}
            />
          </div>
        ))}
    </div>
  );
}

// The bar's height, for `scroll-padding-top` (tokens.css): a focused element never ends up under it.
function usePublishedHeight() {
  const ref = useRef<HTMLElement>(null);
  useEffect(() => {
    const bar = ref.current;
    if (!bar) return;
    const root = document.documentElement;
    const publish = () =>
      root.style.setProperty(
        '--nasim-header-height',
        `${Math.ceil(bar.getBoundingClientRect().height)}px`,
      );
    publish();
    const observer = new ResizeObserver(publish);
    observer.observe(bar);
    return () => {
      observer.disconnect();
      root.style.removeProperty('--nasim-header-height');
    };
  }, []);
  return ref;
}

// The frame of a dashboard: the sidebar from `lg` up, a sticky bar with a menu button that opens the
// same navigation in a drawer below it, and the page in the <main id="main"> landmark.
export function AppShell({
  brand,
  navLabel,
  nav,
  badgeLabel = t.shell.badge,
  header,
  contentWidth,
  topbar,
  sidebarFooter,
  banner,
  children,
}: AppShellProps) {
  const [open, setOpen] = useState(false);
  useRegisterOverlay(open, () => setOpen(false));
  const bar = usePublishedHeight();
  const slots = shell({ width: contentWidth });
  return (
    <div className={slots.root()}>
      <aside className={slots.aside()}>
        <div className={slots.brand()}>{brand}</div>
        <nav aria-label={navLabel} className={slots.nav()}>
          <NavList nav={nav} badgeLabel={badgeLabel} />
        </nav>
        {sidebarFooter ? (
          <div className={slots.footer()}>{sidebarFooter}</div>
        ) : null}
      </aside>

      <div className={slots.column()}>
        <header ref={bar} className={slots.header()}>
          <Tooltip>
            <Button
              isIconOnly
              variant="ghost"
              className="size-11 min-h-11 min-w-11 shrink-0 lg:hidden"
              aria-label={t.shell.openMenu}
              aria-expanded={open}
              onPress={() => setOpen(true)}
            >
              <MenuIcon />
            </Button>
            <Tooltip.Content placement="bottom">
              {t.shell.openMenu}
            </Tooltip.Content>
          </Tooltip>
          {header ? (
            <div className={slots.lead()}>{header}</div>
          ) : (
            <div className="lg:hidden">{brand}</div>
          )}
          {topbar ? <div className={slots.topbar()}>{topbar}</div> : null}
        </header>
        {banner}
        <main id="main" tabIndex={-1} className={slots.main()}>
          {children}
        </main>
      </div>

      <Drawer.Backdrop isOpen={open} onOpenChange={setOpen}>
        <Drawer.Content placement="right">
          <Drawer.Dialog aria-label={navLabel}>
            <Tooltip>
              <Drawer.CloseTrigger aria-label={t.shell.closeMenu} />
              <Tooltip.Content placement="bottom">
                {t.shell.closeMenu}
              </Tooltip.Content>
            </Tooltip>
            <Drawer.Header>
              <Drawer.Heading>{brand}</Drawer.Heading>
            </Drawer.Header>
            <Drawer.Body>
              <nav aria-label={navLabel}>
                <NavList
                  nav={nav}
                  badgeLabel={badgeLabel}
                  onNavigate={() => setOpen(false)}
                />
              </nav>
            </Drawer.Body>
            {sidebarFooter ? (
              <Drawer.Footer className="flex-col items-stretch justify-start border-t border-border pt-3">
                {sidebarFooter}
              </Drawer.Footer>
            ) : null}
          </Drawer.Dialog>
        </Drawer.Content>
      </Drawer.Backdrop>
    </div>
  );
}
