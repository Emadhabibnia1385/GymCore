'use client';

import { CheckIcon, CopyIcon, DangerIcon } from '../icons';
import { Button, type ButtonProps } from '../primitives';
import { t } from '../strings';
import { useClipboardCopy } from './clipboard';

type CopyButtonProps = {
  /** What is copied, in its canonical form (Latin digits, no separators). */
  value: string;
  /** Names the button («کپی شماره کارت»). */
  label: string;
  /** Replaces the label for a moment after a copy. Defaults to «کپی شد». */
  doneLabel?: string;
  variant?: ButtonProps['variant'];
  size?: ButtonProps['size'];
  className?: string;
  'data-testid'?: string;
};

// Copies `value` and says so in words, to the eye and to a screen reader (a polite live region). When
// nothing could be copied it says that too, on screen: the person copies the shown value by hand. The
// failure stays until the next press; a success fades after a moment.
export function CopyButton({
  value,
  label,
  doneLabel = t.common.copied,
  variant = 'secondary',
  size = 'sm',
  className,
  'data-testid': testId,
}: CopyButtonProps) {
  const { state, copy } = useClipboardCopy(value);

  return (
    <>
      <Button
        variant={variant}
        size={size}
        className={className}
        data-testid={testId}
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
        {state === 'done' ? doneLabel : label}
      </Button>
      {/* The one live region: a success is heard, a failure is also read, on its own line. */}
      <span
        role="status"
        aria-live="polite"
        className={
          state === 'failed'
            ? 'block w-full text-sm leading-6 text-danger'
            : 'sr-only'
        }
      >
        {state === 'done'
          ? doneLabel
          : state === 'failed'
            ? t.common.copyFailedByHand
            : ''}
      </span>
    </>
  );
}
