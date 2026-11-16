'use client';

import { Label, ListBox, Pagination } from '@heroui/react';
import { tv } from 'tailwind-variants';
import { Select } from '../primitives';
import { formatNumber, t } from '../strings';
import { Pager } from './Pager';
import { useIsNarrow } from './useIsNarrow';

/** The previous and next buttons with the page in words, for a list that knows its page count. */
type PageCount = {
  page: number;
  pageCount: number;
  onPageChange: (page: number) => void;
};

/** Numbered pages, a summary of the rows shown and, with `pageSizes`, a choice of how many. */
type PageTotal = {
  page: number;
  /** How many rows there are in all, across the pages. */
  total: number;
  pageSize: number;
  /** The sizes offered (`[10, 20, 50]`); leave out for a fixed size. */
  pageSizes?: readonly number[];
  onPageChange: (page: number) => void;
  /** The screen goes back to page 1 itself: the page chosen may not exist at the new size. */
  onPageSizeChange?: (size: number) => void;
};

export type DataPagination = PageCount | PageTotal;

const footer = tv({
  slots: {
    root: 'flex-wrap gap-y-3',
    start:
      'flex flex-wrap items-center gap-x-4 gap-y-2 self-start sm:self-center',
    size: 'flex-row items-center gap-2',
    sizeLabel: 'text-sm text-muted',
    sizeTrigger: 'min-w-20',
    // 44px on a coarse pointer, as every other control (a page link is 36px or 32px by default).
    item: 'pointer-coarse:size-11',
    nav: 'pointer-coarse:size-auto pointer-coarse:min-h-11 pointer-coarse:min-w-11',
    label: 'max-sm:sr-only',
    // HeroUI draws its chevrons for left-to-right text: turned here too, so previous points to the
    // start (right) and next to the end (left) without relying on its stylesheet.
    chevron: 'rtl:rotate-180',
  },
});

const slots = footer();

const SLOTS_PER_SIBLING = 2;

// The numbers to draw, the ellipsis as null. The count of slots stays the same wherever the page is
// (first, last, the page and its neighbours, two gaps), so the row does not jump while paging.
function pageItems(page: number, count: number, siblings: number) {
  const slotCount = siblings * SLOTS_PER_SIBLING + 5;
  const range = (from: number, to: number) =>
    Array.from({ length: to - from + 1 }, (_, index) => from + index);
  if (count <= slotCount) return range(1, count);
  const left = Math.max(page - siblings, 1);
  const right = Math.min(page + siblings, count);
  const gapLeft = left > 3;
  const gapRight = right < count - 2;
  const edge = 3 + siblings * SLOTS_PER_SIBLING;
  if (!gapLeft && gapRight) return [...range(1, edge), null, count];
  if (gapLeft && !gapRight) return [1, null, ...range(count - edge + 1, count)];
  return [1, null, ...range(left, right), null, count];
}

function PageNumbers({
  page,
  pageCount,
  onPageChange,
}: {
  page: number;
  pageCount: number;
  onPageChange: (page: number) => void;
}) {
  const narrow = useIsNarrow('sm');
  const items = pageItems(page, pageCount, narrow ? 0 : 1);
  return (
    <Pagination.Content>
      <Pagination.Item>
        <Pagination.Previous
          className={slots.nav()}
          isDisabled={page <= 1}
          onPress={() => onPageChange(page - 1)}
        >
          <Pagination.PreviousIcon className={slots.chevron()} />
          <span className={slots.label()}>{t.pager.previous}</span>
        </Pagination.Previous>
      </Pagination.Item>
      {items.map((item, index) =>
        item === null ? (
          <Pagination.Item key={`gap-${index}`}>
            <Pagination.Ellipsis className={slots.item()} />
          </Pagination.Item>
        ) : (
          <Pagination.Item key={item}>
            <Pagination.Link
              className={slots.item()}
              aria-label={t.pager.page(formatNumber(item))}
              isActive={item === page}
              onPress={() => onPageChange(item)}
            >
              {formatNumber(item)}
            </Pagination.Link>
          </Pagination.Item>
        ),
      )}
      <Pagination.Item>
        <Pagination.Next
          className={slots.nav()}
          isDisabled={page >= pageCount}
          onPress={() => onPageChange(page + 1)}
        >
          <span className={slots.label()}>{t.pager.next}</span>
          <Pagination.NextIcon className={slots.chevron()} />
        </Pagination.Next>
      </Pagination.Item>
    </Pagination.Content>
  );
}

function PageSize({
  value,
  sizes,
  onChange,
}: {
  value: number;
  sizes: readonly number[];
  onChange: (size: number) => void;
}) {
  return (
    <Select
      className={slots.size()}
      value={String(value)}
      onChange={(key) => {
        if (key !== null) onChange(Number(key));
      }}
    >
      <Label className={slots.sizeLabel()}>{t.table.pageSize}</Label>
      <Select.Trigger className={slots.sizeTrigger()}>
        <Select.Value />
        <Select.Indicator />
      </Select.Trigger>
      <Select.Popover>
        <ListBox>
          {sizes.map((size) => (
            <ListBox.Item
              key={size}
              id={String(size)}
              textValue={formatNumber(size)}
            >
              {formatNumber(size)}
              <ListBox.ItemIndicator />
            </ListBox.Item>
          ))}
        </ListBox>
      </Select.Popover>
    </Select>
  );
}

function Numbered({
  className,
  page: asked,
  total,
  pageSize,
  pageSizes,
  onPageChange,
  onPageSizeChange,
}: PageTotal & { className?: string }) {
  const pageCount = Math.max(1, Math.ceil(total / pageSize));
  const page = Math.min(Math.max(asked, 1), pageCount);
  const from = (page - 1) * pageSize + 1;
  const to = Math.min(page * pageSize, total);
  return (
    <Pagination
      aria-label={t.pager.label}
      className={slots.root({ className })}
    >
      <div className={slots.start()}>
        {pageSizes && onPageSizeChange ? (
          <PageSize
            value={pageSize}
            sizes={pageSizes}
            onChange={onPageSizeChange}
          />
        ) : null}
        <Pagination.Summary aria-live="polite">
          {t.table.summary(
            formatNumber(from),
            formatNumber(to),
            formatNumber(total),
          )}
        </Pagination.Summary>
      </div>
      {pageCount > 1 ? (
        <PageNumbers
          page={page}
          pageCount={pageCount}
          onPageChange={onPageChange}
        />
      ) : null}
    </Pagination>
  );
}

/** Whether there is anything to draw: previous and next only past one page, numbers once there is a total. */
export function hasPagination(pagination: DataPagination): boolean {
  return 'total' in pagination
    ? pagination.total > 0
    : pagination.pageCount > 1;
}

// Under a table or a list of cards: numbered pages when the list knows its total, else previous and next.
export function TablePagination({
  pagination,
  className,
}: {
  pagination: DataPagination;
  className?: string;
}) {
  if ('total' in pagination)
    return <Numbered {...pagination} className={className} />;
  return (
    <Pager
      page={pagination.page}
      pageCount={pagination.pageCount}
      onPrevious={() => pagination.onPageChange(pagination.page - 1)}
      onNext={() => pagination.onPageChange(pagination.page + 1)}
      className={className}
    />
  );
}
