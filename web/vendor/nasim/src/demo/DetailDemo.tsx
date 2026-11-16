import { useState } from 'react';
import { useForm } from 'react-hook-form';
import {
  Avatar,
  BankCard,
  Button,
  CopyText,
  FormRoot,
  ImageViewer,
  KeyValueList,
  PageHeader,
  SecretField,
  SidePanel,
  StatCard,
  StaticTable,
  StatusChip,
  SubmitButton,
  toast,
  UsageBar,
} from '..';

// A detail panel is read from the top: who it is, the figures, then the fields. The section labels
// are plain small text; the tiles are StatCards.
function SectionLabel({ children }: { children: string }) {
  return (
    <p className="border-t border-separator pt-4 text-xs font-medium text-muted">
      {children}
    </p>
  );
}

type Service = { id: string; name: string; owner: string; link: string };

const SERVICES: Service[] = [
  {
    id: 'b7e2a9c4-3f1d-4a52-9c0e-6d1f2a8b3c71',
    name: 'سرویس ویژه ۳۰ روزه',
    owner: 'علی رضایی',
    link: 'https://shop.example.com/sub/b7e2a9c43f1d4a529c0e6d1f2a8b3c71',
  },
  {
    id: 'd41c8e07-92ab-4f6e-8a3d-5b7c0e9f1a24',
    name: 'سرویس اقتصادی ۱۰ گیگ',
    owner: 'مریم احمدی',
    link: 'https://shop.example.com/sub/d41c8e0792ab4f6e8a3d5b7c0e9f1a24',
  },
];

function ServicePanel({
  service,
  isOpen,
  onOpenChange,
}: {
  service: Service;
  isOpen: boolean;
  onOpenChange: (isOpen: boolean) => void;
}) {
  return (
    <SidePanel
      isOpen={isOpen}
      onOpenChange={onOpenChange}
      title="جزئیات سرویس"
      description="همهٔ اطلاعات این سرویس را اینجا می‌بینید."
      footer={
        <>
          <Button variant="tertiary" onPress={() => onOpenChange(false)}>
            بستن
          </Button>
          <Button onPress={() => onOpenChange(false)}>تمدید سرویس</Button>
        </>
      }
    >
      <div className="flex flex-col gap-5">
        <div className="flex items-center gap-3">
          <Avatar size="lg">
            <Avatar.Fallback>ع</Avatar.Fallback>
          </Avatar>
          <div className="flex flex-col gap-1">
            <p className="font-semibold text-foreground">{service.owner}</p>
            <StatusChip tone="success" size="sm" label="فعال" />
          </div>
        </div>
        <SectionLabel>خلاصه</SectionLabel>
        <div className="grid grid-cols-2 gap-3">
          <StatCard label="روز باقی‌مانده" value="۱۲" className="p-3 sm:p-3" />
          <StatCard label="کانفیگ‌ها" value="۳" className="p-3 sm:p-3" />
          <StatCard label="موجودی" value="۱۲۵٬۰۰۰" className="p-3 sm:p-3" />
          <StatCard label="تمدیدها" value="۴" className="p-3 sm:p-3" />
        </div>
        <SectionLabel>حجم مصرفی</SectionLabel>
        <UsageBar
          label="حجم مصرف‌شده"
          used={8.2}
          total={10}
          valueText="۸٫۲ از ۱۰ گیگابایت"
        />
        <SectionLabel>مشخصات</SectionLabel>
        <KeyValueList
          items={[
            { label: 'بستهٔ خریداری‌شده', value: service.name },
            {
              label: 'شناسهٔ سرویس',
              value: <CopyText value={service.id} label="شناسهٔ سرویس" isLtr />,
            },
            {
              label: 'لینک اشتراک',
              value: (
                <CopyText value={service.link} label="لینک اشتراک" isLtr />
              ),
            },
            { label: 'تاریخ انقضا', value: '۱۴۰۵/۰۸/۱۵' },
            { label: 'روش پرداخت', value: 'کارت به کارت' },
          ]}
        />
      </div>
    </SidePanel>
  );
}

const CARDS = [
  { id: 'a', number: '6037991234567893', holder: 'علی رضایی' },
  { id: 'b', number: '6104337777777777', holder: 'مریم احمدی' },
  { id: 'c', number: '6274121111111111', holder: 'رضا کریمی' },
  { id: 'd', number: '9999991234567890', holder: 'کارت ناشناس' },
];

// Usage reads from its colour and its words: fine, nearly full, at the limit, no limit; a table gets one line.
function UsageDemo() {
  return (
    <div className="grid gap-4 sm:grid-cols-2">
      <UsageBar
        label="مصرف عادی"
        used={3.1}
        total={10}
        valueText="۳٫۱ از ۱۰ گیگابایت"
      />
      <UsageBar
        label="نزدیک به سقف"
        used={8.2}
        total={10}
        valueText="۸٫۲ از ۱۰ گیگابایت"
      />
      <UsageBar
        label="به سقف رسیده"
        used={10}
        total={10}
        valueText="۱۰ از ۱۰ گیگابایت"
      />
      <UsageBar
        label="بدون محدودیت"
        used={42}
        total={null}
        valueText="۴۲ گیگابایت"
      />
      <UsageBar
        label="مصرف فشرده"
        used={6}
        total={10}
        valueText="۶ از ۱۰"
        size="compact"
      />
    </div>
  );
}

// A receipt as a picture drawn here, so the demo needs no file: a wide one, to be turned and zoomed.
const RECEIPT = `data:image/svg+xml;utf8,${encodeURIComponent(
  '<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="800" viewBox="0 0 1200 800"><rect width="1200" height="800" fill="#f4f1ea"/><rect x="40" y="40" width="1120" height="720" fill="none" stroke="#999" stroke-width="4"/><g font-family="sans-serif" fill="#222"><text x="80" y="140" font-size="56" font-weight="700">Card to card transfer</text><text x="80" y="250" font-size="40">Amount: 1,250,000 Toman</text><text x="80" y="330" font-size="40">From: 6037 **** **** 7893</text><text x="80" y="410" font-size="40">To: 6104 **** **** 7777</text><text x="80" y="490" font-size="40">Tracking: 4830021957</text><text x="80" y="570" font-size="40">Date: 2026-10-30 14:25</text></g></svg>',
)}`;
const RECEIPT_PDF =
  'data:application/pdf;base64,JVBERi0xLjQKMSAwIG9iago8PCAvVHlwZSAvQ2F0YWxvZyAvUGFnZXMgMiAwIFIgPj4KZW5kb2JqCjIgMCBvYmoKPDwgL1R5cGUgL1BhZ2VzIC9LaWRzIFszIDAgUl0gL0NvdW50IDEgPj4KZW5kb2JqCjMgMCBvYmoKPDwgL1R5cGUgL1BhZ2UgL1BhcmVudCAyIDAgUiAvTWVkaWFCb3ggWzAgMCAzMDAgMjAwXSAvQ29udGVudHMgNCAwIFIgL1Jlc291cmNlcyA8PCAvRm9udCA8PCAvRjEgNSAwIFIgPj4gPj4gPj4KZW5kb2JqCjQgMCBvYmoKPDwgL0xlbmd0aCA0OSA+PgpzdHJlYW0KQlQgL0YxIDE4IFRmIDMwIDExMCBUZCAoUGF5bWVudCByZWNlaXB0IDMxKSBUaiBFVAplbmRzdHJlYW0KZW5kb2JqCjUgMCBvYmoKPDwgL1R5cGUgL0ZvbnQgL1N1YnR5cGUgL1R5cGUxIC9CYXNlRm9udCAvSGVsdmV0aWNhID4+CmVuZG9iagp4cmVmCjAgNgowMDAwMDAwMDAwIDY1NTM1IGYgCjAwMDAwMDAwMDkgMDAwMDAgbiAKMDAwMDAwMDA1OCAwMDAwMCBuIAowMDAwMDAwMTE1IDAwMDAwIG4gCjAwMDAwMDAyNDEgMDAwMDAgbiAKMDAwMDAwMDM0MCAwMDAwMCBuIAp0cmFpbGVyCjw8IC9TaXplIDYgL1Jvb3QgMSAwIFIgPj4Kc3RhcnR4cmVmCjQxMAolJUVPRgo=';

// A receipt photo or a PDF opens full screen: zoom, turn, drag, reset, download.
function ViewerDemo() {
  const [shown, setShown] = useState<'image' | 'pdf' | 'broken' | null>(null);
  return (
    <div className="flex flex-wrap gap-2">
      <Button variant="secondary" onPress={() => setShown('image')}>
        رسید تصویری
      </Button>
      <Button variant="secondary" onPress={() => setShown('pdf')}>
        رسید PDF
      </Button>
      <Button variant="secondary" onPress={() => setShown('broken')}>
        فایل خراب
      </Button>
      <ImageViewer
        isOpen={shown !== null}
        onOpenChange={(open) => !open && setShown(null)}
        type={shown === 'pdf' ? 'pdf' : 'image'}
        src={
          shown === 'pdf'
            ? RECEIPT_PDF
            : shown === 'broken'
              ? 'https://shop.example.invalid/receipts/none.jpg'
              : RECEIPT
        }
        title="رسید پرداخت ۳۱"
        alt="عکس رسید کارت به کارت"
        downloadHref={shown === 'pdf' ? RECEIPT_PDF : RECEIPT}
        downloadName={shown === 'pdf' ? 'receipt-31.pdf' : 'receipt-31.svg'}
      />
    </div>
  );
}

// A card-to-card method shows its card as a card; a table gets the one-line form.
function CardsDemo() {
  return (
    <div className="flex flex-col gap-4">
      <div className="grid gap-4 sm:grid-cols-2">
        <BankCard number={CARDS[0]!.number} holder={CARDS[0]!.holder} />
        <BankCard
          number={CARDS[1]!.number}
          holder={CARDS[1]!.holder}
          isMasked
        />
        <BankCard number={CARDS[2]!.number} holder={CARDS[2]!.holder} />
        <BankCard number={CARDS[3]!.number} holder={CARDS[3]!.holder} />
      </div>
      <StaticTable
        caption="کارت‌های دریافت"
        columns={['کارت', 'دارنده']}
        rows={CARDS.map((card) => ({
          id: card.id,
          cells: [
            <BankCard key="n" number={card.number} size="compact" />,
            card.holder,
          ],
        }))}
      />
    </div>
  );
}

type KeyValues = { apiKey?: string; botToken?: string };

// A saved key is never shown again: the form sends nothing, a new text, or '' to clear it.
function GatewayForm() {
  const [stored, setStored] = useState({ apiKey: '••••4f2a', botToken: '' });
  const form = useForm<KeyValues>();
  return (
    <FormRoot
      form={form}
      className="flex max-w-md flex-col gap-4"
      onSubmit={(values) => {
        setStored((current) => ({
          apiKey:
            values.apiKey === undefined
              ? current.apiKey
              : values.apiKey && `••••${values.apiKey.slice(-4)}`,
          botToken:
            values.botToken === undefined
              ? current.botToken
              : values.botToken && `••••${values.botToken.slice(-4)}`,
        }));
        form.reset({ apiKey: undefined, botToken: undefined });
        toast(
          `ارسال شد: ${JSON.stringify(values, (_key, value) => (value === undefined ? null : value))}`,
        );
      }}
    >
      <SecretField
        name="apiKey"
        label="کلید API درگاه"
        description="این کلید پس از ذخیره دیگر نمایش داده نمی‌شود."
        isSet={stored.apiKey !== ''}
        maskedHint={stored.apiKey}
      />
      <SecretField
        name="botToken"
        label="توکن ربات"
        isSet={stored.botToken !== ''}
        maskedHint={stored.botToken}
      />
      <SubmitButton>ذخیره</SubmitButton>
    </FormRoot>
  );
}

// The detail-and-edit family: a row opens a panel, an id copies in place, a saved key stays hidden,
// a card is drawn as a card, a quota is a bar, a receipt photo zooms.
export function DetailDemo() {
  const [service, setService] = useState<Service>(SERVICES[0] as Service);
  const [open, setOpen] = useState(false);
  const show = (next: Service) => {
    setService(next);
    setOpen(true);
  };
  return (
    <section className="flex flex-col gap-4">
      <PageHeader as="h3" size="section" title="جزئیات و ویرایش" />
      <ul className="flex flex-col divide-y divide-separator rounded-2xl border border-border bg-surface">
        {SERVICES.map((service) => (
          // a mouse opens the row anywhere; the button is the keyboard's way in
          <li
            key={service.id}
            className="flex cursor-pointer flex-wrap items-center justify-between gap-2 px-4 py-3 hover:bg-default"
            onClick={() => show(service)}
          >
            <Button variant="ghost" size="sm" onPress={() => show(service)}>
              {service.name}
            </Button>
            <CopyText value={service.id} label="شناسهٔ سرویس" isLtr>
              {service.id.slice(0, 8)}
            </CopyText>
          </li>
        ))}
      </ul>
      <ServicePanel service={service} isOpen={open} onOpenChange={setOpen} />
      <UsageDemo />
      <ViewerDemo />
      <CardsDemo />
      <GatewayForm />
    </section>
  );
}
