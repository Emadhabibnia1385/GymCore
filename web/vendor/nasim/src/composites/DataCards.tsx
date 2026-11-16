'use client';

import { Checkbox, Label } from '@heroui/react';
import { isValidElement, type ReactNode, useId } from 'react';
import { tv } from 'tailwind-variants';
import { t } from '../strings';
import type { DataColumn } from './DataTable';
import { RowActions } from './RowActions';

const cardStyles = tv({
  slots: {
    list: 'flex flex-col gap-3',
    card: 'relative flex flex-col gap-2.5 rounded-lg border border-border bg-surface p-3.5',
    head: 'flex items-start gap-3',
    title: 'min-w-0 flex-1 break-words font-medium',
    // The kebab is 32px tall beside a 24px title line: the negative margin keeps the card's padding even.
    kebab: 'relative z-10 -my-1 shrink-0',
    // A press anywhere on the card opens it: the title's button is stretched over the card, and what
    // else is pressable (the checkbox, the actions) sits above it.
    open: 'absolute inset-0 rounded-sm focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-(--focus)',
    raised: 'relative z-10',
    fields: 'flex flex-col gap-1.5 text-sm',
    // The label at the start and the value at the end of one line; a long value drops under its label.
    field:
      'flex min-w-0 flex-wrap items-baseline justify-between gap-x-3 gap-y-0.5',
    label: 'shrink-0 text-xs text-muted',
    value: 'min-w-0 break-words',
    actions: 'relative z-10 flex flex-wrap gap-2 border-t border-border pt-3',
    // 44px on a coarse pointer: the box stays small, its label is the hit area.
    box: 'pointer-coarse:min-h-11 pointer-coarse:min-w-11 items-center justify-center',
    selectAll: 'flex items-center px-1 pb-2',
  },
  variants: {
    isSelected: {
      true: { card: 'border-accent bg-accent-soft' },
    },
  },
});

const slots = cardStyles();

// Keep every control accepted by DataTable above the card's stretched action.
const pressables =
  '[&_a]:relative [&_a]:z-10 [&_button]:relative [&_button]:z-10 [&_input]:relative [&_input]:z-10 [&_select]:relative [&_select]:z-10 [&_textarea]:relative [&_textarea]:z-10 [&_label]:relative [&_label]:z-10 [&_summary]:relative [&_summary]:z-10 [&_[role=button]]:relative [&_[role=button]]:z-10 [&_[role=link]]:relative [&_[role=link]]:z-10 [&_[role=checkbox]]:relative [&_[role=checkbox]]:z-10 [&_[role=switch]]:relative [&_[role=switch]]:z-10 [&_[role=menuitem]]:relative [&_[role=menuitem]]:z-10';

type CardsProps<T> = {
  ariaLabel: string;
  columns: readonly DataColumn<T>[];
  rows: readonly T[];
  getRowId: (row: T) => string;
  selectedKeys?: ReadonlySet<string>;
  onSelectionChange?: (keys: Set<string>) => void;
  isRowSelectable?: (row: T) => boolean;
  onRowAction?: (id: string) => void;
};

type Cell = { id: string; cell: ReactNode };

// What a row can do, split by weight: the kebab of `RowActions` is one small control and rides in the
// card's header; anything else is a real button and keeps the footer.
function actionCells<T>(columns: readonly DataColumn<T>[], row: T) {
  const cells: Cell[] = columns
    .map((column) => ({ id: column.id, cell: column.cell(row) }))
    .filter(
      ({ cell }) => cell !== null && cell !== undefined && cell !== false,
    );
  return {
    compact: cells.filter(
      ({ cell }) => isValidElement(cell) && cell.type === RowActions,
    ),
    buttons: cells.filter(
      ({ cell }) => !(isValidElement(cell) && cell.type === RowActions),
    ),
  };
}

// The footer of a card: a row with nothing to do (a revoked key) gets no empty bar with a rule above it.
function CardFooter({ cells }: { cells: readonly Cell[] }) {
  if (!cells.length) return null;
  return (
    <div data-slot="card-footer" className={slots.actions()}>
      {cells.map(({ id, cell }) => (
        <span key={id} className="contents">
          {cell}
        </span>
      ))}
    </div>
  );
}

function SelectAll({
  total,
  chosen,
  onChange,
}: {
  total: number;
  chosen: number;
  onChange: (isSelected: boolean) => void;
}) {
  return (
    <div className={slots.selectAll()}>
      <Checkbox
        isSelected={total > 0 && chosen === total}
        isIndeterminate={chosen > 0 && chosen < total}
        isDisabled={total === 0}
        onChange={onChange}
      >
        <Checkbox.Content>
          <Checkbox.Control>
            <Checkbox.Indicator />
          </Checkbox.Control>
          <Label>{t.table.selectAll}</Label>
        </Checkbox.Content>
      </Checkbox>
    </div>
  );
}

function Card<T>({
  columns,
  row,
  isSelected,
  isLocked,
  onToggle,
  onOpen,
}: {
  columns: readonly DataColumn<T>[];
  row: T;
  isSelected: boolean;
  /** Cannot be chosen: the checkbox is drawn disabled. */
  isLocked: boolean;
  onToggle?: (isSelected: boolean) => void;
  onOpen?: () => void;
}) {
  const titleId = useId();
  const boxId = useId();
  const title = columns.find((column) => column.isRowHeader) ?? columns[0];
  const { compact, buttons } = actionCells(
    columns.filter((column) => column.isActions),
    row,
  );
  const fields = columns.filter(
    (column) => column !== title && !column.isActions && !column.hideOnCard,
  );
  return (
    <li
      data-selected={isSelected || undefined}
      className={slots.card({ isSelected })}
    >
      {title || onToggle || compact.length ? (
        <div data-slot="card-header" className={slots.head()}>
          {onToggle ? (
            <Checkbox
              aria-label={t.table.selectRow}
              aria-labelledby={`${boxId} ${titleId}`}
              id={boxId}
              isSelected={isSelected}
              isDisabled={isLocked}
              onChange={onToggle}
              className={slots.box({ className: slots.raised() })}
            >
              <Checkbox.Content>
                <Checkbox.Control>
                  <Checkbox.Indicator />
                </Checkbox.Control>
              </Checkbox.Content>
            </Checkbox>
          ) : null}
          {title ? (
            <div id={titleId} className={slots.title()}>
              <div className={pressables}>{title.cell(row)}</div>
              {onOpen ? (
                <button
                  type="button"
                  aria-labelledby={titleId}
                  className={slots.open()}
                  onClick={onOpen}
                />
              ) : null}
            </div>
          ) : null}
          {compact.map(({ id, cell }) => (
            <div
              key={id}
              className={slots.kebab({ className: title ? '' : 'ms-auto' })}
            >
              {cell}
            </div>
          ))}
        </div>
      ) : null}
      {fields.length ? (
        <dl className={slots.fields()}>
          {fields.map((column) => (
            <div key={column.id} className={slots.field()}>
              <dt className={slots.label()}>{column.header}</dt>
              <dd className={slots.value({ className: pressables })}>
                {column.cell(row)}
              </dd>
            </div>
          ))}
        </dl>
      ) : null}
      <CardFooter cells={buttons} />
    </li>
  );
}

export function DataCards<T>({
  ariaLabel,
  columns,
  rows,
  getRowId,
  selectedKeys,
  onSelectionChange,
  isRowSelectable,
  onRowAction,
}: CardsProps<T>) {
  const ids = rows.map(getRowId);
  const locked = rows.map((row) => isRowSelectable?.(row) === false);
  const choosable = ids.filter((_, index) => !locked[index]);
  const chosen = choosable.filter((id) => selectedKeys?.has(id)).length;
  const change = (id: string, isSelected: boolean) => {
    const next = new Set(selectedKeys);
    if (isSelected) next.add(id);
    else next.delete(id);
    onSelectionChange?.(next);
  };
  return (
    <>
      {onSelectionChange ? (
        <SelectAll
          total={choosable.length}
          chosen={chosen}
          onChange={(isSelected) =>
            onSelectionChange(new Set(isSelected ? choosable : []))
          }
        />
      ) : null}
      <ul
        aria-label={ariaLabel}
        className={slots.list()}
        data-testid="data-cards"
      >
        {rows.map((row, index) => (
          <Card
            key={ids[index]}
            columns={columns}
            row={row}
            isSelected={Boolean(selectedKeys?.has(ids[index]!))}
            isLocked={locked[index]!}
            onToggle={
              onSelectionChange
                ? (isSelected) => change(ids[index]!, isSelected)
                : undefined
            }
            onOpen={
              onRowAction
                ? () => {
                    const id = ids[index]!;
                    if (
                      onSelectionChange &&
                      selectedKeys?.size &&
                      !locked[index]
                    )
                      change(id, !selectedKeys.has(id));
                    else onRowAction(id);
                  }
                : undefined
            }
          />
        ))}
      </ul>
    </>
  );
}
