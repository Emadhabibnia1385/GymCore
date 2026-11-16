'use client';

import { Fragment } from 'react';
import { tv } from 'tailwind-variants';
import { CheckIcon, CopyIcon, DangerIcon } from '../icons';
import { Button } from '../primitives';
import { persianDigits, t } from '../strings';
import {
  BANK_TONES,
  type BankTone,
  bankOf,
  cardDigits,
  groupsOf,
} from './bankCards';
import { useClipboardCopy } from './clipboard';
import { CopyText } from './CopyText';

const bankCard = tv({
  slots: {
    root: 'flex min-w-0 flex-col gap-2',
    // 85.6 x 54 mm: the shape of a real card. The container query sizes the digits to the card.
    face: '@container relative isolate flex aspect-[1.586] w-full max-w-sm flex-col justify-between overflow-hidden rounded-2xl p-5 text-(--card-foreground) shadow-surface ring-1 ring-(--card-foreground)/10',
    gradient: 'bg-linear-to-br',
    shine:
      'pointer-events-none absolute -end-12 -top-12 -z-10 size-44 rounded-full bg-(--card-foreground)/10',
    bank: 'min-w-0 truncate text-sm font-semibold',
    chip: 'h-7 w-10 shrink-0 rounded-md border border-(--card-foreground)/40 bg-(--card-foreground)/20',
    number:
      'flex justify-between font-mono text-lg font-medium tabular-nums @xs:text-xl',
    holder: 'min-w-0 truncate text-sm text-(--card-foreground-muted)',
    // The card's own text colour, hover and focus ring: the page's tokens are not made for this ground.
    copy: 'ms-auto shrink-0 text-(--card-foreground) hover:bg-(--card-foreground)/15 data-[hovered=true]:bg-(--card-foreground)/15 data-[focus-visible=true]:outline-(--card-foreground)',
    failure: 'text-sm leading-6 text-danger',
    row: 'inline-flex max-w-full items-center gap-2 align-middle',
    swatch: 'h-5 w-8 shrink-0 rounded-sm ring-1 ring-foreground/15',
  },
  variants: {
    tone: {
      blue: { gradient: 'from-(--card-blue-from) to-(--card-blue-to)' },
      teal: { gradient: 'from-(--card-teal-from) to-(--card-teal-to)' },
      green: { gradient: 'from-(--card-green-from) to-(--card-green-to)' },
      orange: { gradient: 'from-(--card-orange-from) to-(--card-orange-to)' },
      red: { gradient: 'from-(--card-red-from) to-(--card-red-to)' },
      wine: { gradient: 'from-(--card-wine-from) to-(--card-wine-to)' },
      purple: { gradient: 'from-(--card-purple-from) to-(--card-purple-to)' },
      graphite: {
        gradient: 'from-(--card-graphite-from) to-(--card-graphite-to)',
      },
    },
  },
});

type BankCardProps = {
  /** The card number in any digit script, with or without spaces and dashes. Nothing is validated. */
  number: string;
  /** The name printed on the card. */
  holder?: string;
  /** The bank's name in the app's words, when it is not the one the first six digits stand for. */
  bank?: string;
  /** Shows only the last four digits; the rest never reaches the page. The copy button still copies all. */
  isMasked?: boolean;
  /** `"compact"` is one line for a table cell: the tone, the number and a copy button. */
  size?: 'regular' | 'compact';
  className?: string;
  'data-testid'?: string;
};

// What the card shows of a number: the digits, a mask over all but the last four, and what names it.
function read(input: string, isMasked: boolean, bank: string | undefined) {
  const normalized = cardDigits(input);
  const allDigits = /^\d+$/.test(normalized);
  const text = normalized.replace(/\D/g, '•');
  const shown = isMasked
    ? text.slice(0, -4).replace(/./g, '•') + text.slice(-4)
    : text;
  const code = bankOf(normalized);
  const tone: BankTone = code ? BANK_TONES[code] : 'graphite';
  const name = bank ?? (code ? t.bank[code] : undefined);
  const lastFour = /^\d{4}$/.test(normalized.slice(-4))
    ? normalized.slice(-4)
    : undefined;
  return {
    // Only a number made of digits has something real to copy
    copyable: allDigits ? normalized : null,
    groups: groupsOf(shown),
    code,
    tone,
    name,
    // A card whose digits are not all on the page is told by its end
    label: t.bankCard.label(
      name ?? t.bankCard.generic,
      isMasked || !allDigits ? lastFour && persianDigits(lastFour) : undefined,
    ),
    copyName: t.common.copyOf(t.bankCard.numberOf(name)),
  };
}

function RegularCard({
  number,
  holder,
  bank,
  isMasked,
  className,
  'data-testid': testId,
}: Omit<BankCardProps, 'size'> & { isMasked: boolean }) {
  const card = read(number, isMasked, bank);
  const slots = bankCard({ tone: card.tone });
  const { state, copy } = useClipboardCopy(card.copyable ?? '');
  // The groups before the last four hold only bullets: nothing to read aloud
  const hidden = isMasked ? card.groups.length - 1 : 0;
  return (
    <div className={slots.root({ className })} data-testid={testId}>
      <div
        role="group"
        aria-label={card.label}
        data-slot="card-face"
        data-size="regular"
        data-tone={card.tone}
        data-bank={card.code ?? undefined}
        className={slots.face({ className: slots.gradient() })}
      >
        <span aria-hidden className={slots.shine()} />
        <div className="flex items-start justify-between gap-3">
          <span className={slots.bank()}>{card.name}</span>
          <span aria-hidden className={slots.chip()} />
        </div>
        <div
          dir="ltr"
          translate="no"
          data-slot="card-number"
          className={slots.number()}
        >
          {card.groups.map((group, index) => (
            <Fragment key={index}>
              {index > 0 ? ' ' : null}
              <span
                data-slot="card-group"
                aria-hidden={index < hidden ? true : undefined}
              >
                {group}
              </span>
            </Fragment>
          ))}
        </div>
        <div className="flex min-h-7 items-end justify-between gap-3">
          {holder ? <span className={slots.holder()}>{holder}</span> : null}
          {card.copyable ? (
            <Button
              isIconOnly
              size="sm"
              variant="ghost"
              aria-label={card.copyName}
              className={slots.copy()}
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
          ) : null}
        </div>
      </div>
      {/* The one live region: a success is heard, a failure is read on screen, under the card. */}
      <span
        role="status"
        aria-live="polite"
        className={state === 'failed' ? slots.failure() : 'sr-only'}
      >
        {state === 'done'
          ? t.common.copied
          : state === 'failed'
            ? t.common.copyFailedByHand
            : ''}
      </span>
    </div>
  );
}

function CompactCard({
  number,
  bank,
  isMasked,
  className,
  'data-testid': testId,
}: Omit<BankCardProps, 'size' | 'holder'> & { isMasked: boolean }) {
  const card = read(number, isMasked, bank);
  const slots = bankCard({ tone: card.tone });
  const shown = card.groups.join(' ');
  return (
    <span
      role="group"
      aria-label={card.label}
      data-size="compact"
      data-tone={card.tone}
      data-bank={card.code ?? undefined}
      data-testid={testId}
      className={slots.row({ className })}
    >
      <span aria-hidden className={`${slots.swatch()} ${slots.gradient()}`} />
      {card.copyable ? (
        <CopyText
          value={card.copyable}
          label={t.bankCard.numberOf(card.name)}
          isLtr
          className="flex-nowrap text-sm tabular-nums"
        >
          {shown}
        </CopyText>
      ) : (
        <span dir="ltr" className="font-mono text-sm tabular-nums">
          {shown}
        </span>
      )}
    </span>
  );
}

// A card number drawn as a bank card: four groups of digits, the holder, the bank by the first six digits
// and a tone to match, with a copy button for the digits without separators. It validates nothing.
export function BankCard({
  size = 'regular',
  isMasked = false,
  ...props
}: BankCardProps) {
  return size === 'compact' ? (
    <CompactCard {...props} isMasked={isMasked} />
  ) : (
    <RegularCard {...props} isMasked={isMasked} />
  );
}
