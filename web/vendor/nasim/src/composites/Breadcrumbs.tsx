'use client';

import { Breadcrumbs as HeroBreadcrumbs } from '@heroui/react';
import type { ReactNode } from 'react';
import { t } from '../strings';

export type BreadcrumbItem = {
  id: string;
  label: ReactNode;
  /** Where the step goes; the last step is the current page and needs none. */
  href?: string;
};

type BreadcrumbsProps = {
  /** The trail from the root to the current page; the last one is the current page. */
  items: readonly BreadcrumbItem[];
  /** Names the landmark; defaults to «مسیر صفحه». */
  label?: string;
  className?: string;
};

// The trail to the current page. The steps read from the start (right) to the end, the chevron between
// them is turned for a right-to-left page by HeroUI's own rule, and the last step is the page itself.
export function Breadcrumbs({ items, label, className }: BreadcrumbsProps) {
  return (
    <nav aria-label={label ?? t.breadcrumbs.label} className={className}>
      <HeroBreadcrumbs aria-label={undefined} className="flex-wrap">
        {items.map((item, index) => (
          <HeroBreadcrumbs.Item
            key={item.id}
            href={index === items.length - 1 ? undefined : item.href}
            className={
              index === items.length - 1 ? undefined : 'pointer-coarse:min-h-11'
            }
          >
            {item.label}
          </HeroBreadcrumbs.Item>
        ))}
      </HeroBreadcrumbs>
    </nav>
  );
}
