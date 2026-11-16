'use client';

import { Avatar, Dropdown } from '@heroui/react';
import type { ComponentProps } from 'react';
import { ChevronDownIcon } from '../icons';
import { Button } from '../primitives';
import { type MenuAction, MenuItems } from './MenuItems';

export type AccountMenuItem = MenuAction;

type AccountMenuProps = {
  /** The signed-in person's name. */
  name: string;
  /** The line under the name: a role, an email. */
  description?: string;
  /** A photo; the first letter of the name stands in until it loads, or without one. */
  avatarSrc?: string;
  items: readonly AccountMenuItem[];
  /** An item without an `href` was chosen. */
  onAction?: (id: string) => void;
  /** Where the menu opens from the button; above it suits a sidebar's foot. */
  placement?: ComponentProps<typeof Dropdown.Popover>['placement'];
};

const initial = (name: string) =>
  Array.from(name.replace(/^[@\s]+/, ''))[0] ?? '';

// The signed-in person: a photo or an initial, a name and a line, and a menu of what they can do.
export function AccountMenu({
  name,
  description,
  avatarSrc,
  items,
  onAction,
  placement = 'top start',
}: AccountMenuProps) {
  return (
    <Dropdown>
      <Button
        variant="ghost"
        className="h-auto min-h-12 w-full justify-start gap-3 px-2 py-2 text-start font-normal"
      >
        <Avatar size="sm" aria-hidden>
          {avatarSrc ? <Avatar.Image src={avatarSrc} alt="" /> : null}
          <Avatar.Fallback>{initial(name)}</Avatar.Fallback>
        </Avatar>
        <span className="flex min-w-0 flex-1 flex-col">
          <span className="truncate text-sm font-medium">
            <bdi>{name}</bdi>
          </span>
          {description ? (
            <span className="truncate text-xs text-muted">{description}</span>
          ) : null}
        </span>
        <ChevronDownIcon
          className={`shrink-0 text-muted${placement.startsWith('top') ? ' rotate-180' : ''}`}
        />
      </Button>
      <Dropdown.Popover
        placement={placement}
        className="min-w-(--trigger-width)"
      >
        <Dropdown.Menu
          onAction={(key) => {
            const item = items.find((entry) => entry.id === String(key));
            if (item && !item.href) onAction?.(item.id);
          }}
        >
          <MenuItems items={items} />
        </Dropdown.Menu>
      </Dropdown.Popover>
    </Dropdown>
  );
}
