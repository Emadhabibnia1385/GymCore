'use client';

import { Dropdown } from '@heroui/react';
import { MoreIcon } from '../icons';
import { Button } from '../primitives';
import { t } from '../strings';
import { type MenuAction, MenuItems } from './MenuItems';

type RowAction = Omit<MenuAction, 'href'>;

type RowActionsProps = {
  /** Names the button after its row («اقدام‌های sara»): a table has one of them in every row. */
  label?: string;
  items: readonly RowAction[];
  onAction: (id: string) => void;
};

// The kebab of a row: a menu of what can be done to it, the dangerous ones last behind a separator.
export function RowActions({
  label = t.rowActions.more,
  items,
  onAction,
}: RowActionsProps) {
  return (
    <Dropdown>
      <Button isIconOnly aria-label={label} size="sm" variant="ghost">
        <MoreIcon />
      </Button>
      <Dropdown.Popover placement="bottom end">
        <Dropdown.Menu onAction={(key) => onAction(String(key))}>
          <MenuItems items={items} />
        </Dropdown.Menu>
      </Dropdown.Popover>
    </Dropdown>
  );
}
