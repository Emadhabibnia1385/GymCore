'use client';

import type { ReactNode } from 'react';
import { tv } from 'tailwind-variants';
import { formatNumber } from '../strings';
import { SearchBox } from './SearchBox';
import { Tabs } from './Tabs';
import { ToolbarProvider, useToolbar } from './toolbarContext';
import { Columns, Facet, Sort } from './ToolbarMenus';
import { Refresh } from './ToolbarRefresh';

const toolbar = tv({
  slots: {
    // One row on a desktop, wrapping on a phone; the search takes a row of its own there.
    root: 'flex flex-wrap items-center gap-2',
    search: 'w-full min-w-0 sm:w-64',
    tabs: 'max-w-full',
    count: 'ms-1.5 text-xs text-muted tabular-nums',
    actions: 'ms-auto flex flex-wrap items-center gap-2',
  },
});

const slots = toolbar();

type ListToolbarProps = {
  /** Names the group of controls («فیلتر کاربران»). */
  label: string;
  /** Every control in the toolbar is off (the first load, a failed one); `Actions` are the screen's own. */
  isDisabled?: boolean;
  children: ReactNode;
  className?: string;
};

type SearchProps = {
  /** What is searched: it names the box, which has no visible label. */
  label: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
};

type TabsProps = {
  /** Names the tab list («وضعیت»). */
  label: string;
  /** `count` is how many rows the status holds, said after its name in Persian digits. */
  items: readonly { id: string; label: string; count?: number }[];
  value: string;
  onChange: (id: string) => void;
};

function ToolbarSearch(props: SearchProps) {
  const { isDisabled } = useToolbar();
  return (
    <div className={slots.search()}>
      <SearchBox {...props} isDisabled={isDisabled} />
    </div>
  );
}

function ToolbarTabs({ label, items, value, onChange }: TabsProps) {
  const { isDisabled } = useToolbar();
  return (
    <Tabs
      className={slots.tabs()}
      label={label}
      selectedKey={value}
      onSelectionChange={onChange}
      items={items.map((item) => ({
        id: item.id,
        isDisabled,
        label:
          item.count === undefined ? (
            item.label
          ) : (
            <>
              {item.label}{' '}
              <span className={slots.count()}>{formatNumber(item.count)}</span>
            </>
          ),
      }))}
    />
  );
}

function ToolbarActions({ children }: { children: ReactNode }) {
  return <div className={slots.actions()}>{children}</div>;
}

/**
 * The bar above a list: a search, status tabs with counts, facet buttons that wear their chosen value, a
 * sort menu, a refresh button with auto-refresh, the column menu, and the primary action at the end.
 * Each part is a member (`ListToolbar.Facet`) and is used only if the screen needs it.
 */
export function ListToolbar({
  label,
  isDisabled = false,
  children,
  className,
}: ListToolbarProps) {
  return (
    <ToolbarProvider value={{ isDisabled }}>
      <div
        role="group"
        aria-label={label}
        className={slots.root({ className })}
      >
        {children}
      </div>
    </ToolbarProvider>
  );
}

ListToolbar.Search = ToolbarSearch;
ListToolbar.Tabs = ToolbarTabs;
ListToolbar.Facet = Facet;
ListToolbar.Sort = Sort;
ListToolbar.Columns = Columns;
ListToolbar.Refresh = Refresh;
ListToolbar.Actions = ToolbarActions;
