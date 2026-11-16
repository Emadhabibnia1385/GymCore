'use client';

import { Modal, Toolbar } from '@heroui/react';
import { type KeyboardEvent, type ReactNode, useState } from 'react';
import { tv } from 'tailwind-variants';
import {
  DangerIcon,
  DownloadIcon,
  FitIcon,
  RotateIcon,
  ZoomInIcon,
  ZoomOutIcon,
} from '../icons';
import { Button, LinkButton, Spinner } from '../primitives';
import { useRegisterOverlay } from '../providers/overlays';
import { formatPercent, t } from '../strings';
import { transformOf, useImageView } from './useImageView';

const viewer = tv({
  slots: {
    // The dialog is the whole screen and dark in both themes: its own tokens, not the page's.
    dialog:
      'gap-0 overflow-hidden bg-(--viewer-background) p-0 text-(--viewer-foreground)',
    header: 'shrink-0 px-page pt-[max(1rem,var(--nasim-safe-top))] pb-2 pe-16',
    heading: 'truncate text-base font-medium text-(--viewer-foreground)',
    close:
      'bg-(--viewer-foreground)/15 text-(--viewer-foreground) hover:bg-(--viewer-foreground)/25 data-[hovered=true]:bg-(--viewer-foreground)/25 data-[focus-visible=true]:outline-(--viewer-foreground)',
    stage:
      'relative flex min-h-0 flex-1 touch-none items-center justify-center overflow-hidden overscroll-contain outline-offset-[-4px] focus-visible:outline-(--viewer-foreground)',
    picture:
      'max-h-full max-w-full object-contain select-none will-change-transform',
    bar: 'flex shrink-0 justify-center px-page pt-2 pb-[max(0.75rem,var(--nasim-safe-bottom))]',
    toolbar:
      'flex items-center gap-1 rounded-full bg-(--viewer-foreground)/12 p-1',
    control:
      'text-(--viewer-foreground) hover:bg-(--viewer-foreground)/15 data-[hovered=true]:bg-(--viewer-foreground)/15 data-[focus-visible=true]:outline-(--viewer-foreground) aria-disabled:opacity-40',
    level: 'min-w-14 text-center text-sm tabular-nums text-(--viewer-muted)',
    notice:
      'absolute inset-0 flex flex-col items-center justify-center gap-3 p-6 text-center',
    hint: 'text-sm text-(--viewer-muted)',
  },
  variants: {
    zoomed: { true: { stage: 'cursor-grab' } },
    gesturing: { true: { stage: 'cursor-grabbing' } },
    moves: {
      // Transform only, and none under reduced motion; a finger on the picture moves it with no delay.
      true: {
        picture:
          'transition-transform duration-150 ease-out motion-reduce:transition-none',
      },
    },
    ready: { false: { picture: 'opacity-0' } },
  },
});

type ViewerProps = {
  title: string;
  src: string;
  downloadHref?: string;
  downloadName?: string;
  onDownload?: () => void;
};

// The download, as the app wants it: its own function, or a link to a file. Nothing when it gives neither.
function Download({
  downloadHref,
  downloadName,
  onDownload,
}: Pick<ViewerProps, 'downloadHref' | 'downloadName' | 'onDownload'>) {
  const slots = viewer();
  if (downloadHref)
    return (
      <LinkButton
        isIconOnly
        size="md"
        variant="ghost"
        href={downloadHref}
        download={downloadName ?? true}
        aria-label={t.viewer.download}
        className={slots.control()}
      >
        <DownloadIcon />
      </LinkButton>
    );
  if (onDownload)
    return (
      <Button
        isIconOnly
        size="md"
        variant="ghost"
        aria-label={t.viewer.download}
        className={slots.control()}
        onPress={onDownload}
      >
        <DownloadIcon />
      </Button>
    );
  return null;
}

function Frame({
  title,
  toolbar,
  children,
  onKeyDown,
}: {
  title: string;
  toolbar: ReactNode;
  children: ReactNode;
  onKeyDown?: (event: KeyboardEvent<HTMLElement>) => void;
}) {
  const slots = viewer();
  return (
    // the keys of the viewer reach it from any control inside, the stage included
    <div className="flex min-h-0 flex-1 flex-col" onKeyDown={onKeyDown}>
      <Modal.CloseTrigger
        aria-label={t.common.close}
        className={slots.close()}
      />
      <Modal.Header className={slots.header()}>
        <Modal.Heading className={slots.heading()}>{title}</Modal.Heading>
      </Modal.Header>
      {children}
      {toolbar}
    </div>
  );
}

type Status = 'loading' | 'ready' | 'failed';

function PictureBody({
  src,
  title,
  alt,
  ...download
}: ViewerProps & { alt: string }) {
  const [status, setStatus] = useState<Status>('loading');
  const [attempt, setAttempt] = useState(0);
  const control = useImageView();
  const { view } = control;
  const ready = status === 'ready';
  const slots = viewer({
    zoomed: view.scale > 1,
    gesturing: control.gesturing,
    moves: !control.gesturing,
    ready,
  });
  // Until the picture is there nothing can be zoomed; a press on a held button is not a no-op to hear
  const held = !ready;
  const hold = (can: boolean) => (held || !can ? true : undefined);
  const whenReady = (run: () => void) => () => {
    if (ready) run();
  };
  return (
    <Frame
      title={title}
      onKeyDown={(event) => {
        if (ready) control.onKeyDown(event);
      }}
      toolbar={
        <div className={slots.bar()}>
          <Toolbar aria-label={t.viewer.toolbar} className={slots.toolbar()}>
            <Button
              isIconOnly
              size="md"
              variant="ghost"
              aria-label={t.viewer.zoomOut}
              aria-disabled={hold(control.canZoomOut)}
              className={slots.control()}
              onPress={whenReady(control.zoomOut)}
            >
              <ZoomOutIcon />
            </Button>
            <output aria-label={t.viewer.zoomLevel} className={slots.level()}>
              {formatPercent(view.scale)}
            </output>
            <Button
              isIconOnly
              size="md"
              variant="ghost"
              aria-label={t.viewer.zoomIn}
              aria-disabled={hold(control.canZoomIn)}
              className={slots.control()}
              onPress={whenReady(control.zoomIn)}
            >
              <ZoomInIcon />
            </Button>
            <Button
              isIconOnly
              size="md"
              variant="ghost"
              aria-label={t.viewer.rotate}
              aria-disabled={hold(true)}
              className={slots.control()}
              onPress={whenReady(control.rotate)}
            >
              <RotateIcon />
            </Button>
            <Button
              isIconOnly
              size="md"
              variant="ghost"
              aria-label={t.viewer.reset}
              aria-disabled={hold(true)}
              className={slots.control()}
              onPress={whenReady(control.reset)}
            >
              <FitIcon />
            </Button>
            <Download {...download} />
          </Toolbar>
        </div>
      }
    >
      <div
        ref={control.stage}
        role="group"
        aria-label={t.viewer.stage}
        // the keys the stage answers: React Aria's Button would drop the attribute, so it is said here
        aria-keyshortcuts="+ - 0 R ArrowLeft ArrowRight ArrowUp ArrowDown"
        tabIndex={0}
        className={slots.stage()}
        {...(ready ? control.stageProps : {})}
      >
        {status === 'failed' ? null : (
          <img
            key={attempt}
            ref={(node) => {
              control.image.current = node;
              // a picture already in the cache is loaded before React listens
              if (node?.complete && node.naturalWidth > 0) setStatus('ready');
            }}
            src={src}
            alt={alt}
            draggable={false}
            className={slots.picture()}
            style={{ transform: transformOf(view) }}
            onLoad={() => setStatus('ready')}
            onError={() => setStatus('failed')}
          />
        )}
        {status === 'loading' ? (
          <div className={slots.notice()}>
            <Spinner size="lg" color="current" />
          </div>
        ) : null}
        {status === 'failed' ? (
          <div role="alert" className={slots.notice()}>
            <DangerIcon width="2.5em" height="2.5em" />
            <p className="text-base font-medium">{t.viewer.failed}</p>
            <p className={slots.hint()}>{t.viewer.failedHint}</p>
            <Button
              variant="secondary"
              onPress={() => {
                setStatus('loading');
                setAttempt((count) => count + 1);
              }}
            >
              {t.common.retry}
            </Button>
          </div>
        ) : null}
      </div>
    </Frame>
  );
}

function PdfBody({ src, title, ...download }: ViewerProps) {
  const slots = viewer();
  const hasDownload = Boolean(download.downloadHref ?? download.onDownload);
  return (
    <Frame
      title={title}
      toolbar={
        hasDownload ? (
          <div className={slots.bar()}>
            <Toolbar aria-label={t.viewer.toolbar} className={slots.toolbar()}>
              <Download {...download} />
            </Toolbar>
          </div>
        ) : null
      }
    >
      <object
        data={src}
        type="application/pdf"
        aria-label={title}
        className="min-h-0 w-full flex-1"
      >
        {/* Where the browser cannot show a PDF: say so, and hand the file over */}
        <div role="group" aria-label={title} className={slots.notice()}>
          <p className="text-base font-medium">{t.viewer.pdfFallback}</p>
          <p className={slots.hint()}>{t.viewer.pdfFallbackHint}</p>
          <LinkButton
            variant="secondary"
            href={download.downloadHref ?? src}
            download={download.downloadName ?? true}
          >
            <DownloadIcon />
            {t.viewer.download}
          </LinkButton>
        </div>
      </object>
    </Frame>
  );
}

type ImageViewerProps = {
  isOpen: boolean;
  onOpenChange: (isOpen: boolean) => void;
  /** The file's address: a picture, or a PDF with `type="pdf"`. */
  src: string;
  /** Names the dialog and says what it shows («رسید پرداخت ۳۱»). */
  title: string;
  type?: 'image' | 'pdf';
  /** What the picture shows, when more than the title says. Defaults to the title. */
  alt?: string;
  /** A link to the file to keep; the button is a link with `download`. */
  downloadHref?: string;
  /** The name the saved file gets, with `downloadHref`. */
  downloadName?: string;
  /** Or the app's own function; with neither there is no download button. */
  onDownload?: () => void;
};

// A receipt photo or a PDF, full screen: zoom, rotate, pan and reset, by buttons, keys, the wheel and
// fingers. Back and Escape close it; a loading and an error state say what is going on.
export function ImageViewer({
  isOpen,
  onOpenChange,
  src,
  title,
  type = 'image',
  alt,
  downloadHref,
  downloadName,
  onDownload,
}: ImageViewerProps) {
  const slots = viewer();
  useRegisterOverlay(isOpen, () => onOpenChange(false));
  const shared = { src, title, downloadHref, downloadName, onDownload };
  return (
    <Modal.Backdrop isOpen={isOpen} onOpenChange={onOpenChange}>
      <Modal.Container size="full" className="sm:w-full">
        <Modal.Dialog className={slots.dialog()}>
          {type === 'pdf' ? (
            <PdfBody {...shared} />
          ) : (
            // a new file starts from its own view
            <PictureBody key={src} alt={alt ?? title} {...shared} />
          )}
        </Modal.Dialog>
      </Modal.Container>
    </Modal.Backdrop>
  );
}
