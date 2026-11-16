'use client';

import { useEffect, useRef, useState } from 'react';

// The clipboard API first; a WebView without its permission (Telegram's) still takes execCommand.
export async function writeClipboard(text: string): Promise<boolean> {
  try {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(text);
      return true;
    }
  } catch {
    // fall through to the older path
  }
  try {
    const area = document.createElement('textarea');
    area.value = text;
    area.setAttribute('readonly', '');
    area.style.position = 'fixed';
    area.style.opacity = '0';
    document.body.appendChild(area);
    area.select();
    const done = document.execCommand('copy');
    document.body.removeChild(area);
    return done;
  } catch {
    return false;
  }
}

export type CopyState = 'idle' | 'done' | 'failed';

// What a copy button shows: a success fades back after a moment, a failure stays until the next press.
export function useClipboardCopy(value: string): {
  state: CopyState;
  copy: () => Promise<void>;
} {
  const [state, setState] = useState<CopyState>('idle');
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  useEffect(
    () => () => {
      if (timer.current) clearTimeout(timer.current);
    },
    [],
  );

  async function copy() {
    const done = await writeClipboard(value);
    setState(done ? 'done' : 'failed');
    if (timer.current) clearTimeout(timer.current);
    if (done) timer.current = setTimeout(() => setState('idle'), 2500);
  }

  return { state, copy };
}
