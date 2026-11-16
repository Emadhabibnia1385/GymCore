'use client';

import { Checkbox, type Selection, Table } from '@heroui/react';
import type { ReactNode, SyntheticEvent } from 'react';
import { t } from '../strings';
import { DataCards } from './DataCards';
import { EmptyState } from './EmptyState';
import { ErrorState } from './ErrorState';
import { TableSkeleton } from './Skeletons';
import {
  type DataPagination,
  hasPagination,
  TablePagination,
} from './TablePagination';
import { useIsNarrow } from './useIsNarrow';

/** The column a list is ordered by and the direction; the same value serves headers and a sort menu. */
export type SortDescriptor = {
  column: string;
  direction: 'ascending' | 'descending';
};

export type DataColumn<T> = {
  id: string;
  /** A sortable column's header is a string: a screen reader hears it when the sort changes. */
  header: ReactNode;
  cell: (row: T) => ReactNode;
  /** Figures and amounts line up at the end. */
  align?: 'start' | 'end';
  /** Exactly one column should name the row for a screen reader. */
  isRowHeader?: boolean;
  /** The header becomes a sort control; the screen orders the rows (see `sortDescriptor`). */
  allowsSorting?: boolean;
  className?: string;
  /** The row's buttons. On a card they sit in the footer instead of being a label and value pair. */
  isActions?: boolean;
  /** Leave the column out of a card (it is still a column of the table). */
  hideOnCard?: boolean;
};

type DataTableProps<T> = {
  /** Names the table: its visible heading is a good choice. */
  ariaLabel: string;
  columns: readonly DataColumn<T>[];
  rows: readonly T[] | undefined;
  getRowId: (row: T) => string;
  /** loading shows skeleton rows, error the error state with a retry, ready the rows or the empty state. */
  status: 'loading' | 'error' | 'ready';
  onRetry?: () => void;
  /** Replaces the default error state, for a screen that words its own errors. */
  errorState?: ReactNode;
  /** The empty state's explanation. */
  empty?: ReactNode;
  /** A short heading above it («هنوز فاکتوری ندارید»). */
  emptyTitle?: string;
  emptyIcon?: ReactNode;
  /** The next step, as an element (a button or a link). */
  emptyAction?: ReactNode;
  /**
   * `{ page, pageCount, onPageChange }` adds previous and next under the rows. With `total` and
   * `pageSize` (and `pageSizes`, `onPageSizeChange` for a choice of size) it is numbered pages, a
   * summary of the rows shown and the page size select.
   */
  pagination?: DataPagination;
  /** The ordering the rows already have, as `{ column, direction }`; none while the list is unordered. */
  sortDescriptor?: SortDescriptor;
  /** A header was pressed: the first press on a column sorts ascending, the next flips it. */
  onSortChange?: (descriptor: SortDescriptor) => void;
  /**
   * A CSS length («32rem», «70dvh»): the rows scroll inside a region that tall and the header stays in
   * view. Without it the table is as tall as its rows. Cards never scroll inside themselves.
   */
  maxHeight?: string;
  /**
   * A row opens its detail: a press on it, or Enter on it, reports its id (on a card, a press on its
   * title). A button inside a cell keeps its own press. While rows are chosen a press on a row
   * chooses it instead, as in React Aria.
   */
  onRowAction?: (id: string) => void;
  /**
   * The chosen row ids. Selection is on when `onSelectionChange` is given: a checkbox per row, a
   * select-all in the header (a select-all above the list on cards), and the chosen set is always
   * ids, never "all".
   */
  selectedKeys?: ReadonlySet<string>;
  onSelectionChange?: (keys: Set<string>) => void;
  /**
   * A row that cannot be chosen (a twin of another receipt): its checkbox is drawn disabled and
   * select-all leaves it out. It still opens through `onRowAction`. Rows are choosable by default.
   */
  isRowSelectable?: (row: T) => boolean;
  /**
   * Below this breakpoint each row is a card (the row header as its title, the other columns as
   * labelled values, the `isActions` columns in its footer) so nothing scrolls sideways on a phone.
   */
  cards?: 'sm' | 'md';
  className?: string;
};

const SELECT_COLUMN = '__select';

const PRESSABLE =
  'a,button,input,select,textarea,label,summary,[role=button],[role=link],[role=checkbox],[role=switch],[role=menuitem]';

// A row that opens or is chosen by a press would take the press of a plain link or button in its cell
// too (React Aria's own buttons already keep theirs): the cell stops what its pressable parts begin.
function keepOwnPress(event: SyntheticEvent) {
  const hit = (event.target as Element).closest(PRESSABLE);
  if (hit && event.currentTarget.contains(hit)) event.stopPropagation();
}

// React Aria's grid hands a focus that lands on a control inside a cell over to a row (the first one when
// the grid had none), so a keyboard could never rest on a button there. Focus that comes to a pressable
// part stays with it.
function keepOwnFocus(event: SyntheticEvent) {
  if ((event.target as Element).closest(PRESSABLE)) event.stopPropagation();
}

function OwnPress({ children }: { children: ReactNode }) {
  return (
    <span
      className="contents"
      onPointerDown={keepOwnPress}
      onMouseDown={keepOwnPress}
      onClick={keepOwnPress}
      onKeyDown={keepOwnPress}
      onKeyUp={keepOwnPress}
      onFocus={keepOwnFocus}
    >
      {children}
    </span>
  );
}

function EmptyView({
  empty,
  emptyTitle,
  emptyIcon,
  emptyAction,
}: Pick<
  DataTableProps<unknown>,
  'empty' | 'emptyTitle' | 'emptyIcon' | 'emptyAction'
>) {
  return (
    <div className="p-4">
      <EmptyState
        title={
          emptyTitle ?? (typeof empty === 'string' ? empty : t.state.emptyTable)
        }
        description={
          emptyTitle && typeof empty === 'string' ? empty : undefined
        }
        icon={emptyIcon}
      />
      {emptyAction ? (
        <div className="flex justify-center pb-4">{emptyAction}</div>
      ) : null}
    </div>
  );
}

// A data table on React Aria's grid: keyboard navigation, RTL aware. A wide table scrolls sideways
// inside its own region, its cells never wrap digit by digit.
export function DataTable<T>({
  ariaLabel,
  columns,
  rows,
  getRowId,
  status,
  onRetry,
  errorState,
  empty,
  emptyTitle,
  emptyIcon,
  emptyAction,
  pagination,
  selectedKeys,
  onSelectionChange,
  isRowSelectable,
  sortDescriptor,
  onSortChange,
  onRowAction,
  maxHeight,
  cards,
  className,
}: DataTableProps<T>) {
  const narrow = useIsNarrow(cards);
  if (status === 'error') return errorState ?? <ErrorState onRetry={onRetry} />;
  if (status === 'loading') return <TableSkeleton rows={5} />;
  const list = rows ?? [];
  const emptyView = (
    <EmptyView
      empty={empty}
      emptyTitle={emptyTitle}
      emptyIcon={emptyIcon}
      emptyAction={emptyAction}
    />
  );
  if (narrow) {
    return (
      <div className={className}>
        {list.length ? (
          <DataCards
            ariaLabel={ariaLabel}
            columns={columns}
            rows={list}
            getRowId={getRowId}
            selectedKeys={selectedKeys}
            onSelectionChange={onSelectionChange}
            isRowSelectable={isRowSelectable}
            onRowAction={onRowAction}
          />
        ) : (
          emptyView
        )}
        {pagination && hasPagination(pagination) ? (
          <TablePagination pagination={pagination} className="mt-4" />
        ) : null}
      </div>
    );
  }
  const items = list.map((row) => ({ key: getRowId(row), row }));
  const selectable = onSelectionChange !== undefined;
  const unselectable = items
    .filter((item) => isRowSelectable?.(item.row) === false)
    .map((item) => item.key);
  // React Aria answers "all" for select all: a screen only ever hears the ids of the page.
  const select = (keys: Selection) =>
    onSelectionChange?.(
      keys === 'all'
        ? new Set(
            items
              .map((item) => item.key)
              .filter((key) => !unselectable.includes(key)),
          )
        : new Set([...keys].map(String)),
    );
  return (
    <Table className={['w-full', className].filter(Boolean).join(' ')}>
      <Table.ScrollContainer
        style={maxHeight ? { maxHeight } : undefined}
        className={maxHeight ? 'scroll-pt-12 overflow-y-auto' : undefined}
      >
        <Table.Content
          aria-label={ariaLabel}
          className="min-w-full [&_td]:whitespace-nowrap [&_th]:whitespace-nowrap"
          selectionMode={selectable ? 'multiple' : 'none'}
          selectedKeys={selectedKeys}
          disabledKeys={unselectable}
          disabledBehavior="selection"
          onSelectionChange={select}
          onRowAction={
            onRowAction ? (key) => onRowAction(String(key)) : undefined
          }
          sortDescriptor={sortDescriptor}
          onSortChange={(next) =>
            onSortChange?.({
              column: String(next.column),
              direction: next.direction,
            })
          }
        >
          <Table.Header className={maxHeight ? 'sticky top-0 z-10' : undefined}>
            {selectable ? (
              <Table.Column id={SELECT_COLUMN} className="w-11 pe-0">
                <Checkbox aria-label={t.table.selectAll} slot="selection">
                  <Checkbox.Content>
                    <Checkbox.Control>
                      <Checkbox.Indicator />
                    </Checkbox.Control>
                  </Checkbox.Content>
                </Checkbox>
              </Table.Column>
            ) : null}
            {columns.map((column) => (
              <Table.Column
                key={column.id}
                id={column.id}
                isRowHeader={column.isRowHeader}
                allowsSorting={column.allowsSorting}
                textValue={
                  typeof column.header === 'string' ? column.header : undefined
                }
                className={[
                  column.align === 'end' && 'text-end',
                  column.className,
                ]
                  .filter(Boolean)
                  .join(' ')}
              >
                {column.allowsSorting
                  ? ({ sortDirection }) => (
                      <Table.SortableColumnHeader
                        sortDirection={sortDirection}
                        className={
                          column.align === 'end' ? 'justify-end gap-1' : 'gap-1'
                        }
                      >
                        {column.header}
                      </Table.SortableColumnHeader>
                    )
                  : column.header}
              </Table.Column>
            ))}
          </Table.Header>
          {/* React Aria keeps a row it drew for the same item: a column that changes must redraw them. */}
          <Table.Body
            items={items}
            dependencies={[columns, selectable, Boolean(onRowAction)]}
            renderEmptyState={() => emptyView}
          >
            {(item) => (
              <Table.Row
                id={item.key}
                className={onRowAction ? 'cursor-pointer' : undefined}
              >
                {selectable ? (
                  <Table.Cell className="pe-0">
                    <Checkbox
                      aria-label={t.table.selectRow}
                      slot="selection"
                      variant="secondary"
                    >
                      <Checkbox.Content>
                        <Checkbox.Control>
                          <Checkbox.Indicator />
                        </Checkbox.Control>
                      </Checkbox.Content>
                    </Checkbox>
                  </Table.Cell>
                ) : null}
                {columns.map((column) => (
                  <Table.Cell
                    key={column.id}
                    className={[
                      column.align === 'end' && 'text-end',
                      column.className,
                    ]
                      .filter(Boolean)
                      .join(' ')}
                  >
                    {selectable || onRowAction ? (
                      <OwnPress>{column.cell(item.row)}</OwnPress>
                    ) : (
                      column.cell(item.row)
                    )}
                  </Table.Cell>
                ))}
              </Table.Row>
            )}
          </Table.Body>
        </Table.Content>
      </Table.ScrollContainer>
      {pagination && hasPagination(pagination) ? (
        <Table.Footer>
          <TablePagination pagination={pagination} />
        </Table.Footer>
      ) : null}
    </Table>
  );
}
