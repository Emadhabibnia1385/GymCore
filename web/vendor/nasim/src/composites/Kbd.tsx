import { Kbd as HeroKbd } from '@heroui/react';
import { Fragment } from 'react';
import { t } from '../strings';

/** The keys Nasim knows by name; any other string is drawn as its own text. */
export type KbdKey = keyof typeof t.kbd;

// The caps are the keyboard's own Latin letters, not copy; HeroUI's Mac symbols (⌃ ⎋) mean nothing on Windows.
const CAPS: Record<KbdKey, string> = {
  command: '⌘',
  shift: 'Shift',
  ctrl: 'Ctrl',
  option: '⌥',
  alt: 'Alt',
  win: 'Win',
  enter: 'Enter',
  delete: 'Del',
  escape: 'Esc',
  tab: 'Tab',
  capslock: 'Caps',
  space: 'Space',
  fn: 'Fn',
  up: '↑',
  down: '↓',
  left: '←',
  right: '→',
  pageup: 'PgUp',
  pagedown: 'PgDn',
  home: 'Home',
  end: 'End',
  help: '?',
};

type KbdProps = {
  /** The shortcut in order: `["ctrl", "K"]`. A named key shows its cap, anything else its own text. */
  keys: readonly string[];
  variant?: 'default' | 'light';
  className?: string;
};

// HeroUI's `rtl:space-x-reverse` also matches this ltr group inside an rtl page, so the caps ran together.
const KEYS_APART = 'gap-0.5 [&>*]:mx-0!';

const named = (key: string): key is KbdKey => key in CAPS;

// A keyboard shortcut. Left to right whatever the page direction: it is a technical value. A named key
// shows its cap with its Persian name on hover and for a screen reader (the cap itself says it in Latin).
export function Kbd({ keys, variant, className }: KbdProps) {
  return (
    <HeroKbd
      dir="ltr"
      variant={variant}
      className={[KEYS_APART, className].filter(Boolean).join(' ')}
    >
      {keys.map((key, index) =>
        named(key) ? (
          <Fragment key={index}>
            <HeroKbd.Content aria-hidden title={t.kbd[key]}>
              {CAPS[key]}
            </HeroKbd.Content>
            <span className="sr-only">{t.kbd[key]}</span>
          </Fragment>
        ) : (
          <HeroKbd.Content key={index}>{key}</HeroKbd.Content>
        ),
      )}
    </HeroKbd>
  );
}
