'use client';

import { Drawer } from '@heroui/react';
import { type ReactNode, useId, useRef, useSyncExternalStore } from 'react';
import { tv } from 'tailwind-variants';
import { useRegisterOverlay } from '../providers/overlays';
import { t } from '../strings';
import { bottomSheet, SheetBody } from './BottomSheet';
import { useIsNarrow } from './useIsNarrow';

const sidePanel = tv({
  slots: {
    // The notch is on the docked edge, so only that edge reads its safe-area inset.
    dialog:
      'h-full max-w-[calc(100vw-2rem)] overscroll-contain pt-[max(1.5rem,var(--nasim-safe-top))] pb-[max(1.5rem,var(--nasim-safe-bottom))] data-[placement=left]:pl-[max(1.5rem,var(--nasim-safe-left))] data-[placement=right]:pr-[max(1.5rem,var(--nasim-safe-right))]',
    header: 'gap-1 pe-10',
    description: 'text-sm text-muted text-pretty',
    // The footer sits outside the scrolling body, so the actions stay in reach. On a phone the two
    // buttons share the width; from sm up they keep their own and sit at the end.
    footer:
      'flex-row gap-2 border-t border-separator pt-4 empty:hidden [&>.button]:flex-1 sm:justify-end sm:[&>.button]:flex-none',
  },
  variants: {
    size: {
      sm: { dialog: 'w-[26.25rem]' },
      md: { dialog: 'w-[30rem]' },
      lg: { dialog: 'w-[35rem]' },
    },
  },
  defaultVariants: { size: 'md' },
});

function documentIsRtl(): boolean {
  const { dir } = document.documentElement;
  if (dir === 'rtl' || dir === 'ltr') return dir === 'rtl';
  return getComputedStyle(document.documentElement).direction === 'rtl';
}

const never = () => () => {};

// The edge names are physical in HeroUI's Drawer; the inline end is the left of a right-to-left page.
// The server and the first client render say right-to-left, which is Nasim's own direction.
function useInlineEndEdge(): 'left' | 'right' {
  return useSyncExternalStore(never, documentIsRtl, () => true)
    ? 'left'
    : 'right';
}

type SidePanelProps = {
  isOpen: boolean;
  onOpenChange: (isOpen: boolean) => void;
  title: string;
  description?: string;
  /** The scrolling body. */
  children: ReactNode;
  /** Action buttons: the cancel first, the main action last. It stays in view under the body. */
  footer?: ReactNode;
  /** 420, 480 or 560 px wide from `sm` up; a phone gets the bottom sheet. Default `"md"`. */
  size?: 'sm' | 'md' | 'lg';
  /** `false` for a form with unsaved input: a backdrop press, a drag and Escape close nothing. */
  isDismissable?: boolean;
  /** A request is running: the backdrop, a drag, Escape and Back are ignored until it is over. */
  isBusy?: boolean;
};

// A row opens its detail or its edit form here: a drawer from the inline-end edge on a desktop, the
// bottom sheet on a phone. It behaves like Modal: `isDismissable` and `isBusy` close nothing but the
// panel's own buttons, and the host's Back button closes it as the top layer unless it is busy.
export function SidePanel({
  isOpen,
  onOpenChange,
  title,
  description,
  children,
  footer,
  size,
  isDismissable = true,
  isBusy = false,
}: SidePanelProps) {
  const narrow = useIsNarrow('sm');
  const edge = useInlineEndEdge();
  const slots = sidePanel({ size });
  const dialogClass = narrow ? bottomSheet().dialog() : slots.dialog();
  const quietUntil = useRef(0);
  const descriptionId = useId();
  useRegisterOverlay(isOpen, () => {
    if (!isBusy) onOpenChange(false);
  });
  const closable = isDismissable && !isBusy;
  return (
    <Drawer.Backdrop
      isOpen={isOpen}
      onOpenChange={onOpenChange}
      isDismissable={closable}
      isKeyboardDismissDisabled={!closable}
      shouldCloseOnInteractOutside={
        // A tap that lands where a sheet's button just moved is not meant for the backdrop.
        narrow ? () => performance.now() >= quietUntil.current : undefined
      }
    >
      <Drawer.Content placement={narrow ? 'bottom' : edge}>
        <Drawer.Dialog
          // nasim-panel: tokens.css swaps the slide for a fade under reduced motion
          className={`nasim-panel ${dialogClass}`}
          aria-describedby={description ? descriptionId : undefined}
        >
          {narrow ? <Drawer.Handle /> : null}
          <Drawer.CloseTrigger aria-label={t.common.close} />
          <Drawer.Header className={slots.header()}>
            <Drawer.Heading>{title}</Drawer.Heading>
            {description ? (
              <p id={descriptionId} className={slots.description()}>
                {description}
              </p>
            ) : null}
          </Drawer.Header>
          <SheetBody title={title} quietUntil={quietUntil}>
            {children}
          </SheetBody>
          {footer ? (
            <Drawer.Footer className={slots.footer()}>{footer}</Drawer.Footer>
          ) : null}
        </Drawer.Dialog>
      </Drawer.Content>
    </Drawer.Backdrop>
  );
}
