'use client';

import {
  Dropdown,
  Header,
  Label,
  Separator,
  type Selection,
} from '@heroui/react';
import { tv } from 'tailwind-variants';
import { CloseIcon, ColumnsIcon, FilterIcon, SortIcon } from '../icons';
import { Button } from '../primitives';
import { formatNumber, t } from '../strings';
import type { SortDescriptor } from './DataTable';
import { useToolbar } from './toolbarContext';

type MenuOption = { id: string; label: string };

const menus = tv({
  slots: {
    // 44px on a coarse pointer; a value that is long is cut, not wrapped over a second line.
    trigger: 'max-w-56 pointer-coarse:h-11',
    label: 'truncate',
    pair: 'inline-flex items-center gap-1',
    popover: 'min-w-48',
  },
  variants: {
    isActive: {
      // The filter is on: the button wears the accent's soft tint, its text the soft pair.
      true: {
        trigger:
          '[--button-bg:var(--accent-soft)] [--button-bg-hover:color-mix(in_oklab,var(--accent)_22%,transparent)] text-accent-soft-foreground',
      },
    },
  },
});

const ALL = '__all__';

type FacetBase = {
  /** What the facet filters by («وضعیت»): the button's name until a value is chosen, and the clear button's. */
  label: string;
  options: readonly MenuOption[];
  /** The first item, which clears the facet; defaults to «همه». */
  allLabel?: string;
};

type FacetOne = FacetBase & {
  selectionMode?: 'single';
  value: string | null;
  onChange: (value: string | null) => void;
};

type FacetMany = FacetBase & {
  selectionMode: 'multiple';
  value: readonly string[];
  onChange: (value: string[]) => void;
};

type FacetProps = FacetOne | FacetMany;

// A filter button that takes the chosen value as its label (Pro's CRM toolbar does, so the bar says what
// is filtered at a glance), with a clear button beside it while something is chosen.
export function Facet(props: FacetProps) {
  const { isDisabled } = useToolbar();
  const { label, options, allLabel = t.toolbar.all } = props;
  const multiple = props.selectionMode === 'multiple';
  const chosen: string[] = multiple
    ? [...props.value]
    : props.value === null
      ? []
      : [props.value];
  const words = chosen.map(
    (id) => options.find((option) => option.id === id)?.label ?? id,
  );
  const shown =
    words.length > 1
      ? t.toolbar.moreSelected(words[0]!, formatNumber(words.length - 1))
      : words[0];
  const slots = menus({ isActive: chosen.length > 0 });
  const select = (keys: Selection) => {
    const next = keys === 'all' ? [] : [...keys].map(String);
    if (props.selectionMode === 'multiple') {
      // «همه» pressed while values are chosen empties the list; a value pressed leaves «همه»
      const cleared = next.includes(ALL) && chosen.length > 0;
      props.onChange(cleared ? [] : next.filter((id) => id !== ALL));
    } else if (next[0] !== undefined) {
      props.onChange(next[0] === ALL ? null : next[0]);
    }
  };
  const clear = () =>
    props.selectionMode === 'multiple'
      ? props.onChange([])
      : props.onChange(null);
  return (
    <span className={slots.pair()}>
      <Dropdown>
        <Button
          variant="secondary"
          isDisabled={isDisabled}
          className={slots.trigger()}
          aria-label={shown === undefined ? undefined : `${label}: ${shown}`}
        >
          <FilterIcon />
          <span className={slots.label()}>{shown ?? label}</span>
        </Button>
        <Dropdown.Popover placement="bottom start" className={slots.popover()}>
          <Dropdown.Menu
            selectionMode={multiple ? 'multiple' : 'single'}
            selectedKeys={chosen.length ? chosen : [ALL]}
            disallowEmptySelection={!multiple}
            onSelectionChange={select}
          >
            <Dropdown.Item id={ALL} textValue={allLabel}>
              <Dropdown.ItemIndicator />
              <Label>{allLabel}</Label>
            </Dropdown.Item>
            {options.map((option) => (
              <Dropdown.Item
                key={option.id}
                id={option.id}
                textValue={option.label}
              >
                <Dropdown.ItemIndicator />
                <Label>{option.label}</Label>
              </Dropdown.Item>
            ))}
          </Dropdown.Menu>
        </Dropdown.Popover>
      </Dropdown>
      {chosen.length ? (
        <Button
          isIconOnly
          variant="secondary"
          aria-label={t.toolbar.clearFacet(label)}
          isDisabled={isDisabled}
          onPress={clear}
        >
          <CloseIcon />
        </Button>
      ) : null}
    </span>
  );
}

type SortProps = {
  /** The button's name and its first section's heading; defaults to «مرتب‌سازی». */
  label?: string;
  /** The columns that can order the list. */
  options: readonly MenuOption[];
  /** The ordering the list has now, the one `DataTable` takes as `sortDescriptor`. */
  value?: SortDescriptor;
  onChange: (value: SortDescriptor) => void;
};

const DIRECTIONS = [
  { id: 'ascending', label: t.toolbar.ascending },
  { id: 'descending', label: t.toolbar.descending },
] as const;

// The ordering as a menu (a card list has no headers to press): the column, then the direction.
export function Sort({
  label = t.toolbar.sort,
  options,
  value,
  onChange,
}: SortProps) {
  const { isDisabled } = useToolbar();
  const slots = menus();
  const current = options.find((option) => option.id === value?.column);
  const direction = DIRECTIONS.find((item) => item.id === value?.direction);
  return (
    <Dropdown>
      <Button
        variant="secondary"
        isDisabled={isDisabled}
        className={slots.trigger()}
        aria-label={
          current && direction
            ? `${label}: ${current.label}، ${direction.label}`
            : undefined
        }
      >
        <SortIcon />
        <span className={slots.label()}>
          {current ? `${label}: ${current.label}` : label}
        </span>
      </Button>
      <Dropdown.Popover placement="bottom start" className={slots.popover()}>
        <Dropdown.Menu>
          <Dropdown.Section
            selectionMode="single"
            disallowEmptySelection
            selectedKeys={current ? [current.id] : []}
            onSelectionChange={(keys) => {
              const [id] = keys === 'all' ? [] : [...keys].map(String);
              if (id !== undefined)
                onChange({
                  column: id,
                  direction: value?.direction ?? 'ascending',
                });
            }}
          >
            <Header>{label}</Header>
            {options.map((option) => (
              <Dropdown.Item
                key={option.id}
                id={option.id}
                textValue={option.label}
              >
                <Dropdown.ItemIndicator type="dot" />
                <Label>{option.label}</Label>
              </Dropdown.Item>
            ))}
          </Dropdown.Section>
          <Separator />
          <Dropdown.Section
            selectionMode="single"
            disallowEmptySelection
            selectedKeys={direction ? [direction.id] : []}
            onSelectionChange={(keys) => {
              const [id] = keys === 'all' ? [] : [...keys].map(String);
              if (current && (id === 'ascending' || id === 'descending'))
                onChange({ column: current.id, direction: id });
            }}
          >
            <Header>{t.toolbar.sortDirection}</Header>
            {DIRECTIONS.map((item) => (
              <Dropdown.Item
                key={item.id}
                id={item.id}
                textValue={item.label}
                isDisabled={!current}
              >
                <Dropdown.ItemIndicator type="dot" />
                <Label>{item.label}</Label>
              </Dropdown.Item>
            ))}
          </Dropdown.Section>
        </Dropdown.Menu>
      </Dropdown.Popover>
    </Dropdown>
  );
}

type ColumnsProps = {
  /** Defaults to «ستون‌ها». */
  label?: string;
  options: readonly MenuOption[];
  /** The ids of the columns shown. The screen passes only those to `DataTable`. */
  value: readonly string[];
  onChange: (value: string[]) => void;
};

// Which columns the table shows: a menu of checkmarks, at least one stays on.
export function Columns({
  label = t.toolbar.columns,
  options,
  value,
  onChange,
}: ColumnsProps) {
  const { isDisabled } = useToolbar();
  const slots = menus();
  return (
    <Dropdown>
      <Button
        variant="secondary"
        isDisabled={isDisabled}
        className={slots.trigger()}
      >
        <ColumnsIcon />
        <span className={slots.label()}>{label}</span>
      </Button>
      <Dropdown.Popover placement="bottom end" className={slots.popover()}>
        <Dropdown.Menu
          selectionMode="multiple"
          disallowEmptySelection
          selectedKeys={value}
          onSelectionChange={(keys) => {
            const picked =
              keys === 'all' ? null : new Set([...keys].map(String));
            // the order of the options, not of the presses
            onChange(
              options
                .map((option) => option.id)
                .filter((id) => picked === null || picked.has(id)),
            );
          }}
        >
          {options.map((option) => (
            <Dropdown.Item
              key={option.id}
              id={option.id}
              textValue={option.label}
            >
              <Dropdown.ItemIndicator />
              <Label>{option.label}</Label>
            </Dropdown.Item>
          ))}
        </Dropdown.Menu>
      </Dropdown.Popover>
    </Dropdown>
  );
}
