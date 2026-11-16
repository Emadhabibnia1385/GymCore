import { reactAria } from './react-aria';

// Only the words Nasim itself shows; a screen passes its own copy to the components as props.
export const t = {
  common: {
    back: 'بازگشت',
    cancel: 'انصراف',
    clearSearch: 'پاک کردن جست‌وجو',
    close: 'بستن',
    closeDialog: 'بستن پنجره',
    confirm: 'تأیید',
    copied: 'کپی شد',
    copy: 'کپی',
    copyFailed: 'کپی نشد',
    copyFailedHint: 'متن انتخاب شد؛ آن را دستی کپی کنید.',
    copyFailedByHand: 'کپی نشد؛ مقدار را دستی انتخاب و کپی کنید.',
    copyOf: (label: string) => `کپی ${label}`,
    loading: 'در حال بارگذاری',
    retry: 'تلاش دوباره',
    selectPlaceholder: 'انتخاب کنید',
  },
  secret: {
    stored: 'ثبت شده',
    willClear: 'پس از ذخیره پاک می‌شود',
    replace: 'جایگزینی',
    clear: 'پاک کردن',
    undoClear: 'بازگرداندن',
    show: 'نمایش مقدار',
    hide: 'پنهان کردن مقدار',
  },
  bank: {
    melli: 'بانک ملی ایران',
    mellat: 'بانک ملت',
    saderat: 'بانک صادرات ایران',
    tejarat: 'بانک تجارت',
    sepah: 'بانک سپه',
    keshavarzi: 'بانک کشاورزی',
    maskan: 'بانک مسکن',
    parsian: 'بانک پارسیان',
    pasargad: 'بانک پاسارگاد',
    shahr: 'بانک شهر',
    resalat: 'بانک رسالت',
    mehriran: 'بانک قرض‌الحسنه مهر ایران',
    sina: 'بانک سینا',
    gardeshgari: 'بانک گردشگری',
    khavarmianeh: 'بانک خاورمیانه',
    saman: 'بانک سامان',
    refah: 'بانک رفاه کارگران',
    dey: 'بانک دی',
    karafarin: 'بانک کارآفرین',
    ayandeh: 'بانک آینده',
    eghtesadnovin: 'بانک اقتصاد نوین',
    sarmayeh: 'بانک سرمایه',
    post: 'پست بانک ایران',
    toseetaavon: 'بانک توسعه تعاون',
    sanatmadan: 'بانک صنعت و معدن',
    iranzamin: 'بانک ایران زمین',
    melal: 'مؤسسه اعتباری ملل',
  },
  bankCard: {
    generic: 'کارت بانکی',
    label: (bank: string, last?: string) =>
      last ? `کارت ${bank}، پایان ${last}` : `کارت ${bank}`,
    numberOf: (bank?: string) => (bank ? `شماره کارت ${bank}` : 'شماره کارت'),
  },
  usageBar: {
    warning: 'نزدیک به سقف',
    danger: 'به سقف رسیده',
    unlimited: 'نامحدود',
  },
  viewer: {
    toolbar: 'ابزار نمایش',
    stage: 'ناحیهٔ نمایش',
    zoomIn: 'بزرگ‌نمایی',
    zoomOut: 'کوچک‌نمایی',
    zoomLevel: 'میزان بزرگ‌نمایی',
    rotate: 'چرخاندن',
    reset: 'بازنشانی نما',
    download: 'دانلود',
    failed: 'نمایش فایل انجام نشد',
    failedHint: 'اتصال اینترنت را بررسی کنید و دوباره تلاش کنید.',
    pdfFallback: 'این مرورگر نمی‌تواند PDF را نمایش دهد.',
    pdfFallbackHint: 'فایل را دانلود کنید و با برنامهٔ دیگری باز کنید.',
  },
  toast: {
    region: 'اعلان‌ها',
  },
  shell: {
    openMenu: 'باز کردن منو',
    closeMenu: 'بستن منو',
    badge: (count: string) => `${count} مورد در انتظار`,
  },
  pager: {
    label: 'صفحه‌بندی',
    previous: 'صفحه قبل',
    next: 'صفحه بعد',
    page: (page: string) => `صفحه ${page}`,
    pageOf: (page: string, total: string) => `صفحه ${page} از ${total}`,
    refreshing: 'در حال به‌روزرسانی',
  },
  table: {
    selectAll: 'انتخاب همه',
    selectRow: 'انتخاب ردیف',
    summary: (from: string, to: string, total: string) =>
      `${from} تا ${to} از ${total}`,
    pageSize: 'تعداد در صفحه',
  },
  toolbar: {
    all: 'همه',
    clearFacet: (name: string) => `پاک کردن ${name}`,
    moreSelected: (first: string, others: string) =>
      `${first} و ${others} مورد دیگر`,
    sort: 'مرتب‌سازی',
    sortDirection: 'جهت مرتب‌سازی',
    ascending: 'صعودی',
    descending: 'نزولی',
    refresh: 'به‌روزرسانی',
    refreshing: 'در حال به‌روزرسانی',
    autoRefresh: 'به‌روزرسانی خودکار',
    autoRefreshOff: 'خاموش',
    everySeconds: (seconds: string) => `هر ${seconds} ثانیه`,
    columns: 'ستون‌ها',
  },
  actionBar: {
    label: 'اقدام‌های گروهی',
    clear: 'پاک کردن انتخاب',
  },
  rowActions: {
    more: 'اقدام‌های بیشتر',
  },
  tabs: {
    scrollStart: 'پیمایش زبانه‌ها به چپ',
    scrollEnd: 'پیمایش زبانه‌ها به راست',
    scrollUp: 'پیمایش زبانه‌ها به بالا',
    scrollDown: 'پیمایش زبانه‌ها به پایین',
  },
  sortableList: {
    moveUp: (name: string) => `بردن ${name} به بالا`,
    moveDown: (name: string) => `بردن ${name} به پایین`,
    moved: (name: string, position: string, total: string) =>
      `${name} در جایگاه ${position} از ${total} قرار گرفت.`,
  },
  calendar: {
    // HeroUI words this button itself («Mehr 1405 AP, year selector»); the month and year stay visible
    selectYear: 'انتخاب سال',
  },
  multiSelect: {
    placeholder: 'جست‌وجو و انتخاب',
    remove: 'حذف',
    selected: 'انتخاب‌شده‌ها',
    clear: 'پاک کردن همه',
    noResults: 'موردی پیدا نشد.',
  },
  breadcrumbs: {
    label: 'مسیر صفحه',
  },
  kbd: {
    command: 'کامند',
    shift: 'شیفت',
    ctrl: 'کنترل',
    option: 'آپشن',
    alt: 'آلت',
    win: 'ویندوز',
    enter: 'اینتر',
    delete: 'حذف',
    escape: 'اسکیپ',
    tab: 'تب',
    capslock: 'کپس‌لاک',
    space: 'فاصله',
    fn: 'اف‌ان',
    up: 'فلش بالا',
    down: 'فلش پایین',
    left: 'فلش چپ',
    right: 'فلش راست',
    pageup: 'صفحهٔ بالا',
    pagedown: 'صفحهٔ پایین',
    home: 'هوم',
    end: 'اند',
    help: 'راهنما',
  },
  trend: {
    up: (percent: string) => `افزایش ${percent}`,
    down: (percent: string) => `کاهش ${percent}`,
    flat: 'بدون تغییر',
    none: 'بدون مقایسه',
  },
  areaChart: {
    hint: 'با کلیدهای جهت‌نمای چپ و راست، نقطه‌ها را یکی‌یکی مرور کنید.',
    noData: 'بدون داده',
  },
  stepper: {
    position: (step: string, total: string, name: string) =>
      `مرحله ${step} از ${total}: ${name}`,
  },
  state: {
    errorTitle: 'بارگذاری انجام نشد',
    errorMessage: 'اتصال اینترنت را بررسی کنید و دوباره تلاش کنید.',
    contactSupport: 'تماس با پشتیبانی',
    trackingCode: 'کد پیگیری',
    retryIn: (seconds: string) => `تلاش دوباره (${seconds} ثانیه)`,
    emptyTable: 'موردی برای نمایش وجود ندارد.',
    offline:
      'اتصال اینترنت برقرار نیست. پس از برقراری اتصال، اطلاعات به‌روز می‌شود.',
  },
  reactAria,
};

// Persian digits and grouping come from Intl, never from string replacement.
const numbers = new Intl.NumberFormat('fa-IR');

export function formatNumber(value: number): string {
  return numbers.format(value);
}

// Digits only, as a string: «۰۰۷۸», no grouping and no lost leading zeros.
const digits = new Intl.NumberFormat('fa-IR', { useGrouping: false });
const percents = new Intl.NumberFormat('fa-IR', { style: 'percent' });

// A fraction as a percent in Persian digits: 1.5 is «۱۵۰٪».
export function formatPercent(fraction: number): string {
  return percents.format(fraction);
}

const changes = new Intl.NumberFormat('fa-IR', {
  style: 'percent',
  maximumFractionDigits: 1,
});

// The size of a change as a percent with one decimal at most, no sign: -0.034 is «۳٫۴٪».
export function formatChange(fraction: number): string {
  return changes.format(Math.abs(fraction));
}

export function persianDigits(value: string): string {
  return value.replace(/\d/g, (digit) => digits.format(Number(digit)));
}
