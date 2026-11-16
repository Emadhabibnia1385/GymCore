'use client';

import type { ReactNode } from 'react';
import { tv } from 'tailwind-variants';
import { CheckIcon, CopyIcon, DangerIcon } from '../icons';
import { Button } from '../primitives';
import { t } from '../strings';
import { useClipboardCopy } from './clipboard';

const copyText = tv({
  slots: {
    root: 'inline-flex max-w-full flex-wrap items-center gap-x-1 gap-y-0.5 align-middle',
    value: 'min-w-0 select-text',
    // Small on the screen; a touch screen gets a 44px hit area from tokens.css.
    button: 'size-7 min-w-0 shrink-0 text-muted',
    failure: 'block basis-full text-sm leading-6 text-danger',
  },
  variants: {
    ltr: {
      true: { value: 'font-mono break-all' },
      false: { value: 'break-words' },
    },
  },
  defaultVariants: { ltr: false },
});

type CopyTextProps = {
  /** What is copied, in its canonical form. */
  value: string;
  /** Names what is copied; the button says «کپی» and this («کپی شناسه سرویس»). */
  label: string;
  /** What is shown when that is not the value itself (a shortened id). Defaults to `value`. */
  children?: ReactNode;
  /** An id, a link, a code: shown left to right in monospace, whatever the page direction. */
  isLtr?: boolean;
  /** Replaces «کپی شد» in the live region. */
  doneLabel?: string;
  className?: string;
  'data-testid'?: string;
};

// A value with a small copy button beside it, for every id, link and code of a detail panel. The
// feedback is in place: the icon becomes a check and a polite live region says so; when nothing could
// be copied it says that in words, as CopyButton does. Safe inside a row that opens on a press.
export function CopyText({
  value,
  label,
  children,
  isLtr = false,
  doneLabel = t.common.copied,
  className,
  'data-testid': testId,
}: CopyTextProps) {
  const { state, copy } = useClipboardCopy(value);
  const slots = copyText({ ltr: isLtr });
  return (
    <span className={slots.root({ className })} data-testid={testId}>
      <span
        className={slots.value()}
        dir={isLtr ? 'ltr' : undefined}
        translate={isLtr ? 'no' : undefined}
      >
        {children ?? value}
      </span>
      {/* React Aria's press stops its click, so a row that opens on a press never sees a copy. */}
      <Button
        isIconOnly
        size="sm"
        variant="ghost"
        aria-label={t.common.copyOf(label)}
        className={slots.button()}
        data-state={state}
        onPress={copy}
      >
        {state === 'done' ? (
          <CheckIcon />
        ) : state === 'failed' ? (
          <DangerIcon />
        ) : (
          <CopyIcon />
        )}
      </Button>
      {/* The one live region: a success is heard, a failure is also read, on its own line. */}
      <span
        role="status"
        aria-live="polite"
        className={state === 'failed' ? slots.failure() : 'sr-only'}
      >
        {state === 'done'
          ? doneLabel
          : state === 'failed'
            ? t.common.copyFailedByHand
            : ''}
      </span>
    </span>
  );
}
