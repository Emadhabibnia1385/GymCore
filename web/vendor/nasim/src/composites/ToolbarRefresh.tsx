'use client';

import { Dropdown, Header, Label } from '@heroui/react';
import { tv } from 'tailwind-variants';
import { ChevronDownIcon, RefreshIcon } from '../icons';
import { Button, Spinner } from '../primitives';
import { formatNumber, t } from '../strings';
import { useToolbar } from './toolbarContext';

type RefreshProps = {
  onRefresh: () => void;
  /** The list is being fetched: the button says so, and a press is ignored until it is over. */
  isRefreshing?: boolean;
  /**
   * Seconds between automatic refreshes; 0 is off. Give it with `onIntervalChange` to offer the menu.
   * The screen owns the timer: this part only asks which interval a person wants.
   */
  interval?: number;
  onIntervalChange?: (seconds: number) => void;
};

const INTERVALS = [0, 15, 30, 60] as const;

const refresh = tv({
  slots: {
    pair: 'inline-flex items-center gap-1',
    button: 'pointer-coarse:h-11',
    // Under 640px the words give way to the icon; the name stays for a screen reader.
    label: 'max-sm:sr-only',
    // A dot that shows the timer is on without saying how often: the menu's name does that.
    dot: 'absolute end-1.5 top-1.5 size-1.5 rounded-full bg-accent',
  },
});

const slots = refresh();

function intervalLabel(seconds: number) {
  return seconds === 0
    ? t.toolbar.autoRefreshOff
    : t.toolbar.everySeconds(formatNumber(seconds));
}

// A refresh button that says it is refreshing, and an optional menu of automatic refresh intervals.
export function Refresh({
  onRefresh,
  isRefreshing = false,
  interval,
  onIntervalChange,
}: RefreshProps) {
  const { isDisabled } = useToolbar();
  const timed = interval !== undefined && onIntervalChange !== undefined;
  return (
    <span className={slots.pair()}>
      <Button
        variant="secondary"
        className={slots.button()}
        isDisabled={isDisabled}
        isPending={isRefreshing}
        onPress={onRefresh}
      >
        {isRefreshing ? (
          <Spinner aria-hidden color="current" size="sm" />
        ) : (
          <RefreshIcon />
        )}
        <span className={slots.label()}>
          {isRefreshing ? t.toolbar.refreshing : t.toolbar.refresh}
        </span>
      </Button>
      {timed ? (
        <Dropdown>
          <Button
            isIconOnly
            variant="secondary"
            className="relative"
            aria-label={`${t.toolbar.autoRefresh}: ${intervalLabel(interval)}`}
            isDisabled={isDisabled}
          >
            <ChevronDownIcon />
            {interval > 0 ? <span aria-hidden className={slots.dot()} /> : null}
          </Button>
          <Dropdown.Popover placement="bottom end">
            <Dropdown.Menu
              selectionMode="single"
              disallowEmptySelection
              selectedKeys={[String(interval)]}
              onSelectionChange={(keys) => {
                const [seconds] = keys === 'all' ? [] : [...keys];
                if (seconds !== undefined) onIntervalChange(Number(seconds));
              }}
            >
              <Dropdown.Section>
                <Header>{t.toolbar.autoRefresh}</Header>
                {INTERVALS.map((seconds) => (
                  <Dropdown.Item
                    key={seconds}
                    id={String(seconds)}
                    textValue={intervalLabel(seconds)}
                  >
                    <Dropdown.ItemIndicator type="dot" />
                    <Label>{intervalLabel(seconds)}</Label>
                  </Dropdown.Item>
                ))}
              </Dropdown.Section>
            </Dropdown.Menu>
          </Dropdown.Popover>
        </Dropdown>
      ) : null}
      <span role="status" className="sr-only">
        {isRefreshing ? t.toolbar.refreshing : ''}
      </span>
    </span>
  );
}
