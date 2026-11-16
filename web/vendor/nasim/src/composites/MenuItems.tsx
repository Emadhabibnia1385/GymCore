'use client';

import { Dropdown, Label, Separator } from '@heroui/react';
import type { ReactNode } from 'react';
import { tv } from 'tailwind-variants';

export type MenuAction = {
  id: string;
  label: string;
  /** An address makes the item a link; the host router takes it. */
  href?: string;
  /** Drawn before the words; hidden from a screen reader, which hears the label. */
  icon?: ReactNode;
  /** `"danger"` tints the item and moves it to the end, after a separator. */
  tone?: 'danger';
};

const menuItem = tv({
  slots: {
    icon: 'inline-flex size-4 shrink-0 items-center justify-center text-muted',
  },
  variants: {
    tone: {
      danger: { icon: 'text-danger' },
    },
  },
});

function Item({ item }: { item: MenuAction }) {
  const slots = menuItem({ tone: item.tone });
  return (
    <Dropdown.Item
      id={item.id}
      href={item.href}
      textValue={item.label}
      variant={item.tone === 'danger' ? 'danger' : 'default'}
    >
      {item.icon ? (
        <span aria-hidden className={slots.icon()}>
          {item.icon}
        </span>
      ) : null}
      <Label>{item.label}</Label>
    </Dropdown.Item>
  );
}

// The items of a dropdown menu, the dangerous ones last behind a separator.
export function MenuItems({ items }: { items: readonly MenuAction[] }) {
  const safe = items.filter((item) => item.tone !== 'danger');
  const danger = items.filter((item) => item.tone === 'danger');
  return (
    <>
      {safe.map((item) => (
        <Item key={item.id} item={item} />
      ))}
      {safe.length && danger.length ? <Separator /> : null}
      {danger.map((item) => (
        <Item key={item.id} item={item} />
      ))}
    </>
  );
}
