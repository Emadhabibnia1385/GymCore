import { useEffect, useState } from 'react';
import {
  ActionBar,
  Button,
  type DataColumn,
  DataTable,
  ListToolbar,
  RowActions,
  type SortDescriptor,
  StatusChip,
  type StatusTone,
} from '..';
import { CheckIcon, CopyIcon, DangerIcon } from '../icons';

// A list the way an admin panel makes it: the toolbar, a table that chooses, orders and opens rows,
// the bar for a bulk selection and the kebab of a row, all on sample data held in this file.
type Status = 'active' | 'expired' | 'disabled';

type User = {
  id: string;
  name: string;
  server: string;
  protocol: string;
  status: Status;
  usedGb: number;
  totalGb: number;
  daysLeft: number;
};

const USERS: User[] = [
  ['sara', 'de1', 'vless', 'active', 12.4, 50, 21],
  ['reza', 'nl1', 'vmess', 'active', 48.9, 50, 3],
  ['mina', 'tr1', 'trojan', 'expired', 30, 30, 0],
  ['ali', 'de1', 'vless', 'active', 5.1, 100, 58],
  ['negar', 'fi1', 'vless', 'disabled', 0, 20, 12],
  ['kian', 'nl1', 'vmess', 'active', 77.3, 200, 90],
  ['parisa', 'tr1', 'vless', 'active', 19.6, 40, 9],
  ['omid', 'de1', 'trojan', 'expired', 10, 10, 0],
  ['yasaman', 'fi1', 'vmess', 'active', 2.2, 25, 30],
  ['hossein', 'nl1', 'vless', 'active', 64, 100, 14],
  ['tara', 'de1', 'vless', 'disabled', 8.8, 50, 40],
  ['arman', 'tr1', 'vmess', 'active', 41.5, 60, 6],
  ['ghazal', 'fi1', 'trojan', 'active', 15.3, 30, 18],
  ['sina', 'nl1', 'vless', 'expired', 50, 50, 0],
  ['donya', 'de1', 'vmess', 'active', 33.7, 80, 27],
  ['babak', 'tr1', 'vless', 'active', 90.1, 150, 45],
  ['elham', 'fi1', 'vless', 'active', 7.4, 20, 2],
  ['farhad', 'nl1', 'trojan', 'disabled', 0, 40, 33],
  ['hasti', 'de1', 'vless', 'active', 26.2, 60, 11],
  ['iman', 'tr1', 'vmess', 'active', 58.8, 100, 70],
  ['jila', 'fi1', 'vless', 'expired', 20, 20, 0],
  ['kaveh', 'nl1', 'vmess', 'active', 3.3, 15, 5],
  ['leila', 'de1', 'vless', 'active', 71.9, 120, 36],
  ['majid', 'tr1', 'trojan', 'active', 44.4, 90, 23],
].map(([name, server, protocol, status, usedGb, totalGb, daysLeft]) => ({
  id: String(name),
  name: String(name),
  server: String(server),
  protocol: String(protocol),
  status: status as Status,
  usedGb: Number(usedGb),
  totalGb: Number(totalGb),
  daysLeft: Number(daysLeft),
}));

const STATUS_WORDS: Record<Status, { label: string; tone: StatusTone }> = {
  active: { label: 'فعال', tone: 'success' },
  expired: { label: 'منقضی', tone: 'neutral' },
  disabled: { label: 'غیرفعال', tone: 'danger' },
};

const SERVERS = [
  { id: 'de1', label: 'آلمان ۱' },
  { id: 'nl1', label: 'هلند ۱' },
  { id: 'tr1', label: 'ترکیه ۱' },
  { id: 'fi1', label: 'فنلاند ۱' },
];

const PROTOCOLS = [
  { id: 'vless', label: 'VLESS' },
  { id: 'vmess', label: 'VMess' },
  { id: 'trojan', label: 'Trojan' },
];

const SORTABLE = [
  { id: 'name', label: 'نام کاربری' },
  { id: 'usedGb', label: 'مصرف' },
  { id: 'daysLeft', label: 'روز باقی‌مانده' },
];

const ALL_COLUMNS = [
  { id: 'name', label: 'کاربر' },
  { id: 'server', label: 'سرور' },
  { id: 'status', label: 'وضعیت' },
  { id: 'usedGb', label: 'مصرف' },
  { id: 'daysLeft', label: 'روز باقی‌مانده' },
];

const number = new Intl.NumberFormat('fa-IR', { maximumFractionDigits: 1 });

function matches(user: User, query: string) {
  return user.name.includes(query.trim().toLowerCase());
}

function compare(a: User, b: User, sort: SortDescriptor | undefined) {
  if (!sort) return 0;
  const key = sort.column as 'name' | 'usedGb' | 'daysLeft';
  const order = a[key] < b[key] ? -1 : a[key] > b[key] ? 1 : 0;
  return sort.direction === 'ascending' ? order : -order;
}

export function UsersListDemo() {
  const [query, setQuery] = useState('');
  const [status, setStatus] = useState('all');
  const [server, setServer] = useState<string | null>(null);
  const [protocols, setProtocols] = useState<string[]>([]);
  const [sort, setSort] = useState<SortDescriptor | undefined>({
    column: 'usedGb',
    direction: 'descending',
  });
  const [shown, setShown] = useState(ALL_COLUMNS.map((column) => column.id));
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(5);
  const [selected, setSelected] = useState<ReadonlySet<string>>(new Set());
  const [opened, setOpened] = useState<string | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [seconds, setSeconds] = useState(0);
  const [refreshedAt, setRefreshedAt] = useState(0);

  const refresh = () => {
    setIsRefreshing(true);
    setTimeout(() => {
      setIsRefreshing(false);
      setRefreshedAt((count) => count + 1);
    }, 800);
  };
  // The screen owns the timer: the toolbar only says which interval was asked for.
  useEffect(() => {
    if (!seconds) return;
    const timer = setInterval(refresh, seconds * 1000);
    return () => clearInterval(timer);
  }, [seconds]);

  const counts = (key: Status) =>
    USERS.filter((user) => user.status === key).length;
  const filtered = USERS.filter(
    (user) =>
      matches(user, query) &&
      (status === 'all' || user.status === status) &&
      (server === null || user.server === server) &&
      (protocols.length === 0 || protocols.includes(user.protocol)),
  ).sort((a, b) => compare(a, b, sort));
  const rows = filtered.slice((page - 1) * pageSize, page * pageSize);

  const columns: DataColumn<User>[] = [
    {
      id: 'name',
      header: 'کاربر',
      isRowHeader: true,
      allowsSorting: true,
      cell: (user) => <span dir="ltr">{user.name}</span>,
    },
    {
      id: 'server',
      header: 'سرور',
      cell: (user) =>
        SERVERS.find((item) => item.id === user.server)?.label ?? user.server,
    },
    {
      id: 'status',
      header: 'وضعیت',
      cell: (user) => (
        <StatusChip
          size="sm"
          tone={STATUS_WORDS[user.status].tone}
          label={STATUS_WORDS[user.status].label}
        />
      ),
    },
    {
      id: 'usedGb',
      header: 'مصرف',
      align: 'end',
      allowsSorting: true,
      cell: (user) => (
        <span className="tabular-nums">
          {number.format(user.usedGb)} از {number.format(user.totalGb)} گیگ
        </span>
      ),
    },
    {
      id: 'daysLeft',
      header: 'روز باقی‌مانده',
      align: 'end',
      allowsSorting: true,
      cell: (user) => (
        <span className="tabular-nums">{number.format(user.daysLeft)}</span>
      ),
    },
    {
      id: 'actions',
      header: 'اقدام‌ها',
      isActions: true,
      cell: (user) => (
        <RowActions
          label={`اقدام‌های ${user.name}`}
          items={[
            { id: 'copy', label: 'کپی اشتراک', icon: <CopyIcon /> },
            { id: 'renew', label: 'تمدید', icon: <CheckIcon /> },
            {
              id: 'delete',
              label: 'حذف',
              icon: <DangerIcon />,
              tone: 'danger',
            },
          ]}
          onAction={(id) => setOpened(`${id}: ${user.name}`)}
        />
      ),
    },
  ];

  const reset = () => setPage(1);

  return (
    <div className="flex flex-col gap-4">
      <ListToolbar label="فیلتر کاربران">
        <ListToolbar.Search
          label="جست‌وجوی کاربر"
          placeholder="جست‌وجوی نام کاربری"
          value={query}
          onChange={(next) => {
            setQuery(next);
            reset();
          }}
        />
        <ListToolbar.Tabs
          label="وضعیت کاربر"
          value={status}
          onChange={(next) => {
            setStatus(next);
            reset();
          }}
          items={[
            { id: 'all', label: 'همه', count: USERS.length },
            { id: 'active', label: 'فعال', count: counts('active') },
            { id: 'expired', label: 'منقضی', count: counts('expired') },
            { id: 'disabled', label: 'غیرفعال', count: counts('disabled') },
          ]}
        />
        <ListToolbar.Facet
          label="سرور"
          options={SERVERS}
          value={server}
          onChange={(next) => {
            setServer(next);
            reset();
          }}
        />
        <ListToolbar.Facet
          label="پروتکل"
          options={PROTOCOLS}
          selectionMode="multiple"
          value={protocols}
          onChange={(next) => {
            setProtocols(next);
            reset();
          }}
        />
        <ListToolbar.Sort options={SORTABLE} value={sort} onChange={setSort} />
        <ListToolbar.Columns
          options={ALL_COLUMNS}
          value={shown}
          onChange={setShown}
        />
        <ListToolbar.Refresh
          onRefresh={refresh}
          isRefreshing={isRefreshing}
          interval={seconds}
          onIntervalChange={setSeconds}
        />
        <ListToolbar.Actions>
          <Button>کاربر جدید</Button>
        </ListToolbar.Actions>
      </ListToolbar>
      <DataTable
        ariaLabel="کاربران"
        columns={columns.filter(
          (column) => column.isActions || shown.includes(column.id),
        )}
        rows={rows}
        getRowId={(user) => user.id}
        status="ready"
        cards="md"
        maxHeight="32rem"
        emptyTitle="کاربری پیدا نشد"
        empty="فیلترها را تغییر دهید یا کاربر جدید بسازید."
        sortDescriptor={sort}
        onSortChange={setSort}
        selectedKeys={selected}
        onSelectionChange={setSelected}
        onRowAction={(id) => setOpened(`جزئیات: ${id}`)}
        pagination={{
          page,
          total: filtered.length,
          pageSize,
          pageSizes: [5, 10, 20],
          onPageChange: setPage,
          onPageSizeChange: (size) => {
            setPageSize(size);
            reset();
          },
        }}
      />
      <p className="text-sm text-muted" aria-live="polite">
        {opened
          ? `آخرین اقدام: ${opened}`
          : `به‌روزرسانی‌ها: ${number.format(refreshedAt)}`}
      </p>
      <ActionBar
        count={selected.size}
        label={`${number.format(selected.size)} کاربر انتخاب شد`}
        onClear={() => setSelected(new Set())}
      >
        <ActionBar.Action
          label="تمدید"
          icon={<CheckIcon />}
          onPress={() =>
            setOpened(`تمدید ${number.format(selected.size)} کاربر`)
          }
        />
        <ActionBar.Action
          label="حذف"
          icon={<DangerIcon />}
          tone="danger"
          onPress={() => setOpened(`حذف ${number.format(selected.size)} کاربر`)}
        />
      </ActionBar>
    </div>
  );
}
