import { useState } from 'react';
import {
  AccountMenu,
  BottomSheet,
  Breadcrumbs,
  Button,
  ConfirmDialog,
  CopyField,
  EmptyState,
  ErrorState,
  FilterChips,
  Kbd,
  KeyValueList,
  LoadingState,
  MessageBar,
  OptionCards,
  PageHeader,
  SearchBox,
  SortableList,
  Stepper,
  toast,
} from '..';
import { DetailDemo } from './DetailDemo';
import { Section } from './PrimitivesDemo';

const STATUSES = [
  { value: 'all', label: 'همه' },
  { value: 'active', label: 'فعال' },
  { value: 'disabled', label: 'غیرفعال' },
  { value: 'expired', label: 'منقضی' },
];

const METHODS = [
  {
    value: 'wallet',
    title: 'کیف پول',
    description: 'از موجودی شما کم می‌شود',
    meta: '۱۲۰٬۰۰۰ تومان',
  },
  {
    value: 'card',
    title: 'کارت به کارت',
    description: 'پس از واریز، رسید را بفرستید',
  },
  {
    value: 'paused',
    title: 'درگاه آنلاین',
    description: 'فعلاً در دسترس نیست',
    isDisabled: true,
  },
];

const GATEWAYS = [
  { id: 'zarinpal', label: 'زرین‌پال', description: 'درگاه آنلاین' },
  { id: 'card', label: 'کارت به کارت', description: 'با رسید' },
  { id: 'wallet', label: 'کیف پول' },
];

export function CompositesDemo() {
  const [confirm, setConfirm] = useState<'default' | 'danger' | null>(null);
  const [sheet, setSheet] = useState(false);
  const [query, setQuery] = useState('');
  const [message, setMessage] = useState('');
  const [status, setStatus] = useState('all');
  const [method, setMethod] = useState<string | null>('wallet');
  const [gateways, setGateways] = useState(GATEWAYS);
  return (
    <Section title="قطعه‌های ترکیبی">
      <Breadcrumbs
        items={[
          { id: 'home', label: 'خانه', href: '#' },
          { id: 'services', label: 'سرویس‌های من', href: '#' },
          { id: 'one', label: 'سرویس ویژه ۳۰ روزه' },
        ]}
      />
      <PageHeader
        backHref="#"
        title="سرویس‌های من"
        description="همهٔ سرویس‌های فعال و پایان‌یافته"
        actions={<Button size="sm">خرید سرویس</Button>}
      />
      <p className="flex flex-wrap items-center gap-2 text-sm text-muted">
        جست‌وجوی سریع: <Kbd keys={['ctrl', 'K']} />
        بستن پنجره: <Kbd keys={['escape']} />
        مرور فهرست: <Kbd keys={['up']} /> <Kbd keys={['down']} />
      </p>
      <div className="w-64 rounded-xl border border-border bg-surface p-3">
        <AccountMenu
          name="سارا احمدی"
          description="مدیر"
          placement="bottom start"
          items={[
            { id: 'security', label: 'امنیت و نشست‌ها', href: '#' },
            { id: 'logout', label: 'خروج', tone: 'danger' },
          ]}
          onAction={() => toast('خروج انجام شد')}
        />
      </div>
      <div className="grid gap-4 sm:grid-cols-2">
        <LoadingState size="inline" />
        <LoadingState size="inline" label="در حال بررسی پرداخت" />
      </div>
      <EmptyState
        title="هنوز سرویسی ندارید"
        description="یک سرویس بخرید تا اینجا وضعیت و حجم باقی‌ماندهٔ آن را ببینید."
        action={{ label: 'مشاهدهٔ فروشگاه', href: '#' }}
      />
      <ErrorState
        onRetry={() => toast('دوباره تلاش شد')}
        supportHref="#"
        requestId="b7e2a9c4"
      />
      <KeyValueList
        items={[
          { label: 'نام سرویس', value: 'سرویس ویژه ۳۰ روزه' },
          { label: 'موجودی کیف پول', value: '۱۲۵٬۰۰۰ تومان', numeric: true },
          { label: 'اعتبار تا', value: '۱۴۰۵/۰۸/۱۵' },
        ]}
      />
      <KeyValueList
        layout="stacked"
        items={[
          {
            label: 'شناسهٔ سرویس',
            value: 'b7e2a9c4-3f1d-4a52-9c0e-6d1f2a8b3c71',
            ltr: true,
          },
        ]}
      />
      <CopyField
        label="لینک اشتراک"
        value="https://shop.example.com/sub/b7e2a9c43f1d4a529c0e6d1f2a8b3c71"
      />
      <MessageBar
        label="پیام شما"
        sendLabel="ارسال"
        value={message}
        onValueChange={setMessage}
        onSubmit={() => setMessage('')}
        canSend={message.trim() !== ''}
      />
      <SearchBox label="جست‌وجوی سرویس" value={query} onChange={setQuery} />
      <FilterChips
        label="وضعیت سرویس"
        value={status}
        onChange={setStatus}
        options={STATUSES}
      />
      <OptionCards
        label="روش پرداخت"
        value={method}
        onChange={setMethod}
        options={METHODS}
      />
      <SortableList
        label="ترتیب روش‌های پرداخت"
        items={gateways}
        onReorder={(ids) =>
          setGateways(ids.map((id) => GATEWAYS.find((g) => g.id === id)!))
        }
      />
      <Stepper steps={['گزینه‌ها', 'روش پرداخت', 'تأیید']} current={1} />
      <div className="flex flex-wrap gap-2">
        <Button variant="secondary" onPress={() => setConfirm('default')}>
          تأیید معمولی
        </Button>
        <Button variant="danger" onPress={() => setConfirm('danger')}>
          تأیید خطرناک
        </Button>
        <Button variant="secondary" onPress={() => setSheet(true)}>
          برگهٔ پایین
        </Button>
      </div>
      <ConfirmDialog
        isOpen={confirm !== null}
        onOpenChange={(open) => !open && setConfirm(null)}
        tone={confirm ?? 'default'}
        title={confirm === 'danger' ? 'حذف سرویس؟' : 'تمدید سرویس؟'}
        description={
          confirm === 'danger'
            ? 'این کار برگشت‌پذیر نیست و کانفیگ‌های سرویس از کار می‌افتند.'
            : 'هزینهٔ تمدید از موجودی کیف پول شما کم می‌شود.'
        }
        confirmLabel={confirm === 'danger' ? 'حذف سرویس' : 'تمدید'}
        onConfirm={() => new Promise((resolve) => setTimeout(resolve, 1200))}
      />
      <BottomSheet
        isOpen={sheet}
        onOpenChange={setSheet}
        title="روش پرداخت"
        description="یکی از روش‌های زیر را انتخاب کنید."
        footer={
          <>
            <Button size="lg" onPress={() => setSheet(false)}>
              ادامه
            </Button>
            <Button
              size="lg"
              variant="tertiary"
              onPress={() => setSheet(false)}
            >
              انصراف
            </Button>
          </>
        }
      >
        <KeyValueList
          items={Array.from({ length: 12 }, (_, i) => ({
            label: `گزینهٔ شمارهٔ ${i + 1}`,
            value: 'توضیح کوتاه',
          }))}
        />
      </BottomSheet>
      <DetailDemo />
    </Section>
  );
}
