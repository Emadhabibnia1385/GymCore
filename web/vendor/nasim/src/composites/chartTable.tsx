import type { ReactNode } from 'react';
import { tv } from 'tailwind-variants';

export type ChartTable = {
  /** Words of the disclosure that opens the table. */
  showLabel: string;
  /** Names the table and the region that scrolls it. */
  label: string;
  columns: readonly ReactNode[];
  /** One cell per column; the first cell of a row is its header. */
  rows: readonly { key: string; cells: readonly ReactNode[] }[];
};

const disclosure = tv({
  slots: {
    root: 'rounded-md border border-border text-sm',
    summary: 'min-h-11 cursor-pointer px-3 py-2.5 font-medium',
  },
});

const slots = disclosure();

// The exact values of a chart as a table behind a disclosure: no number is only a picture.
export function ChartTableDisclosure({
  table,
  'data-testid': testId,
}: {
  table: ChartTable;
  'data-testid'?: string;
}) {
  return (
    <details className={slots.root()}>
      <summary className={slots.summary()}>{table.showLabel}</summary>
      <div
        className="max-h-80 overflow-auto"
        tabIndex={0}
        role="region"
        aria-label={table.label}
      >
        <table className="w-full text-sm" data-testid={testId}>
          <caption className="sr-only">{table.label}</caption>
          <thead>
            <tr className="border-b border-border text-muted">
              {table.columns.map((header, index) => (
                <th
                  key={index}
                  scope="col"
                  className={`px-3 py-2 font-medium ${index === 0 ? 'text-start' : 'text-end'}`}
                >
                  {header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {table.rows.map((row) => (
              <tr
                key={row.key}
                className="border-b border-border last:border-0"
              >
                {row.cells.map((cell, index) =>
                  index === 0 ? (
                    <th
                      key={index}
                      scope="row"
                      className="px-3 py-1.5 text-start font-normal"
                    >
                      {cell}
                    </th>
                  ) : (
                    <td
                      key={index}
                      className="px-3 py-1.5 text-end tabular-nums"
                    >
                      {cell}
                    </td>
                  ),
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </details>
  );
}
