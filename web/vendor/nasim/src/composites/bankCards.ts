// What BankCard knows about Iranian cards: the first six digits (the BIN) name the issuer.

// The tone of a card is a loose nod to its bank's colour, not its logo: eight gradients in tokens.css.
export const TONES = [
  'blue',
  'teal',
  'green',
  'orange',
  'red',
  'wine',
  'purple',
  'graphite',
] as const;
export type BankTone = (typeof TONES)[number];

// The key is the bank's code; `t.bank` has its name in Persian.
export const BANK_TONES = {
  melli: 'blue',
  mellat: 'red',
  saderat: 'blue',
  tejarat: 'blue',
  sepah: 'orange',
  keshavarzi: 'green',
  maskan: 'orange',
  parsian: 'wine',
  pasargad: 'orange',
  shahr: 'red',
  resalat: 'green',
  mehriran: 'teal',
  sina: 'teal',
  gardeshgari: 'teal',
  khavarmianeh: 'teal',
  saman: 'blue',
  refah: 'blue',
  dey: 'purple',
  karafarin: 'green',
  ayandeh: 'wine',
  eghtesadnovin: 'purple',
  sarmayeh: 'orange',
  post: 'green',
  toseetaavon: 'green',
  sanatmadan: 'graphite',
  iranzamin: 'teal',
  melal: 'blue',
} as const satisfies Record<string, BankTone>;
export type BankCode = keyof typeof BANK_TONES;

// Public Shetab prefixes; a merged bank keeps its historic ones, a bank with several lists them all.
export const BIN_TO_BANK: Record<string, BankCode> = {
  '603799': 'melli',
  '610433': 'mellat',
  '991975': 'mellat',
  '603769': 'saderat',
  '627353': 'tejarat',
  '585983': 'tejarat',
  '589210': 'sepah',
  '627381': 'sepah',
  '603770': 'keshavarzi',
  '639217': 'keshavarzi',
  '628023': 'maskan',
  '622106': 'parsian',
  '627884': 'parsian',
  '639194': 'parsian',
  '502229': 'pasargad',
  '639347': 'pasargad',
  '502806': 'shahr',
  '504706': 'shahr',
  '504172': 'resalat',
  '606373': 'mehriran',
  '639346': 'sina',
  '505416': 'gardeshgari',
  '585947': 'khavarmianeh',
  '621986': 'saman',
  '589463': 'refah',
  '502938': 'dey',
  '627488': 'karafarin',
  '636214': 'ayandeh',
  '627412': 'eghtesadnovin',
  '639607': 'sarmayeh',
  '627760': 'post',
  '502908': 'toseetaavon',
  '627961': 'sanatmadan',
  '505785': 'iranzamin',
  '606256': 'melal',
};

/** The number as digits: Persian and Arabic digits become Latin, spaces, dashes and joiners go. */
export function cardDigits(input: string): string {
  return input
    .replace(/[۰-۹]/g, (digit) => String(digit.charCodeAt(0) - 0x06f0))
    .replace(/[٠-٩]/g, (digit) => String(digit.charCodeAt(0) - 0x0660))
    .replace(/[\s\-‌‎‏]/g, '');
}

/** The issuer of the first six digits, or null when they are not a known prefix (or not digits). */
export function bankOf(digits: string): BankCode | null {
  return BIN_TO_BANK[digits.slice(0, 6)] ?? null;
}

/** Groups of four from the left; the last may be shorter. */
export function groupsOf(text: string): string[] {
  return text.match(/.{1,4}/g) ?? [];
}
