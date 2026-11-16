'use client';

import { Separator, Toolbar } from '@heroui/react';
import { type ReactNode, useRef, useState } from 'react';
import { tv } from 'tailwind-variants';
import { CloseIcon } from '../icons';
import { Button } from '../primitives';
import { useRegisterOverlay } from '../providers/overlays';
import { t } from '../strings';

const actionBar = tv({
  slots: {
    // Fixed at the bottom centre, clear of the home indicator, Telegram's bars and a host's tab bar (as
    // the toasts are); it lets the page's presses through around the pill. Closed it is invisible, and
    // `inert` takes it out of the tab order. Only opacity and translate move, and not at all under
    // reduced motion.
    frame:
      'pointer-events-none fixed inset-x-0 bottom-[calc(1rem+max(var(--nasim-safe-bottom),var(--nasim-bottom-bar,0px)))] z-40 flex justify-center px-page transition-[opacity,translate,visibility] duration-200 ease-out motion-reduce:transition-none',
    pill: 'pointer-events-auto max-w-full overflow-x-auto',
    count:
      'whitespace-nowrap rounded-full bg-default px-2.5 py-1 text-xs font-medium text-default-foreground tabular-nums',
    action: 'pointer-coarse:h-11 pointer-coarse:min-w-11 whitespace-nowrap',
  },
  variants: {
    isOpen: {
      true: { frame: 'visible translate-y-0 opacity-100' },
      false: { frame: 'invisible translate-y-3 opacity-0' },
    },
    // With an icon the words give way to it under 640px; the button keeps a 44px width.
    hasIcon: {
      true: { action: 'max-sm:min-w-11 max-sm:px-0' },
    },
  },
});

type ActionBarProps = {
  /** How many rows are selected: the bar shows while it is above zero. */
  count: number;
  /** The count in words, from the screen's strings («۳ کاربر انتخاب شد»). */
  label: string;
  /** Clears the selection: the clear button, Escape inside the bar and the host's Back button call it. */
  onClear: () => void;
  /** The actions, `ActionBar.Action` or any buttons; the destructive one goes last. */
  children?: ReactNode;
};

type ActionProps = {
  label: string;
  /** Drawn before the words; under 640px it is all that shows. */
  icon?: ReactNode;
  /** `"danger"` tints the button. */
  tone?: 'danger';
  isDisabled?: boolean;
  onPress: () => void;
};

function ActionBarAction({
  label,
  icon,
  tone,
  isDisabled,
  onPress,
}: ActionProps) {
  const slots = actionBar({ hasIcon: icon !== undefined });
  return (
    <Button
      size="sm"
      variant={tone === 'danger' ? 'danger-soft' : 'ghost'}
      className={slots.action()}
      isDisabled={isDisabled}
      onPress={onPress}
    >
      {icon ? (
        <span aria-hidden className="inline-flex">
          {icon}
        </span>
      ) : null}
      <span className={icon ? 'max-sm:sr-only' : undefined}>{label}</span>
    </Button>
  );
}

/**
 * A pill at the bottom centre while rows are selected: the count in words, the actions, a button that
 * clears the selection. It is a layer, so the host's Back button clears the selection too.
 */
export function ActionBar({ count, label, onClear, children }: ActionBarProps) {
  const isOpen = count > 0;
  // The words stay while the bar leaves, instead of turning into «۰ مورد» on the way out.
  const [shown, setShown] = useState(label);
  if (isOpen && label !== shown) setShown(label);
  const before = useRef<HTMLElement | null>(null);
  const slots = actionBar({ isOpen });
  // Focus that was in the bar goes back to where it came from, not to the top of the page.
  const clear = () => {
    onClear();
    if (before.current?.isConnected) before.current.focus();
  };
  useRegisterOverlay(isOpen, clear);
  return (
    <>
      <span role="status" className="sr-only">
        {isOpen ? label : ''}
      </span>
      <div
        data-slot="action-bar"
        className={slots.frame()}
        aria-hidden={isOpen ? undefined : true}
        inert={!isOpen}
        onFocus={(event) => {
          if (!event.currentTarget.contains(event.relatedTarget as Node | null))
            before.current = event.relatedTarget as HTMLElement | null;
        }}
        onKeyDown={(event) => {
          if (event.key === 'Escape') clear();
        }}
      >
        <Toolbar
          isAttached
          aria-label={t.actionBar.label}
          className={slots.pill()}
        >
          <span aria-hidden className={slots.count()}>
            {shown}
          </span>
          {children ? (
            <>
              <Separator />
              {children}
            </>
          ) : null}
          <Separator />
          <Button
            isIconOnly
            size="sm"
            variant="ghost"
            aria-label={t.actionBar.clear}
            onPress={clear}
          >
            <CloseIcon />
          </Button>
        </Toolbar>
      </div>
    </>
  );
}

ActionBar.Action = ActionBarAction;
