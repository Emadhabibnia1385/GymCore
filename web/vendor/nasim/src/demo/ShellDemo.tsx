import {
  AccountMenu,
  AppShell,
  Breadcrumbs,
  Button,
  Notice,
  PageHeader,
  ThemeToggle,
} from '..';

// The frame as an app draws it: groups, a count on the door that has work waiting, the trail in the
// bar, the person's menu in the sidebar's foot (the phone's menu shows it too).
const NAV = [
  {
    id: 'daily',
    label: 'کار روزانه',
    items: [
      { href: '#dashboard', label: 'داشبورد' },
      { href: '#review', label: 'درخواست‌های نیازمند بررسی', badge: 3 },
    ],
  },
  {
    id: 'sales',
    label: 'کاربران و فروش',
    items: [
      { href: '#users', label: 'خدمات کاربران' },
      { href: '#reports', label: 'گزارشات' },
    ],
  },
  {
    id: 'system',
    label: 'سیستم',
    items: [{ href: '#settings', label: 'تنظیمات' }],
  },
];

const ACCOUNT_ITEMS = [
  { id: 'security', label: 'امنیت و نشست‌ها', href: '#security' },
  { id: 'shop', label: 'بازگشت به فروشگاه', href: '#shop' },
  { id: 'logout', label: 'خروج', tone: 'danger' as const },
];

export function ShellDemo({ onExit }: { onExit: () => void }) {
  const items = NAV.map((group) => ({
    ...group,
    items: group.items.map((item) => ({
      ...item,
      isCurrent: item.href === '#review',
    })),
  }));
  return (
    <AppShell
      brand={<strong>نسیم</strong>}
      navLabel="پیمایش اصلی"
      nav={items}
      header={
        <Breadcrumbs
          items={[
            { id: 'home', label: 'داشبورد', href: '#dashboard' },
            { id: 'review', label: 'درخواست‌های نیازمند بررسی' },
          ]}
        />
      }
      topbar={
        <>
          <Button size="sm" variant="secondary" onPress={onExit}>
            بازگشت به نمایشگاه
          </Button>
          <ThemeToggle lightLabel="حالت روشن" darkLabel="حالت تیره" />
        </>
      }
      sidebarFooter={
        <AccountMenu
          name="سارا احمدی"
          description="مدیر"
          items={ACCOUNT_ITEMS}
          onAction={(id) => id === 'logout' && onExit()}
        />
      }
      contentWidth="full"
    >
      <div className="flex flex-col gap-6">
        <PageHeader
          title="درخواست‌های نیازمند بررسی"
          description="این صفحه تمام عرض کنار منو را می‌گیرد."
        />
        <Notice tone="info">
          نوار بالا هنگام پیمایش می‌ماند و اندازهٔ آن برای پیمایش به یک عنصر
          فوکوس‌شده در نظر گرفته می‌شود.
        </Notice>
        {Array.from({ length: 24 }, (_, index) => (
          <p key={index} className="rounded-lg bg-surface p-4 text-sm">
            ردیف نمونه {index + 1}
          </p>
        ))}
      </div>
    </AppShell>
  );
}
