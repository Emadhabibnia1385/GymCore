import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { Link, useNavigate } from "@tanstack/react-router";
import { Button, EmptyState, ErrorState, PageHeader, PageSkeleton, SearchBox, StatCard, StatusChip, type StatusTone, UsageBar } from "@nyxon/nasim";
import { ScrollChips } from "@/shared/ScrollChips";
import { useDeferredValue, useState } from "react";
import { emptyStudent, StudentFormSheet, type StudentDraft } from "@/features/manage";
import { formatNumber, formatToman } from "@/shared/format";
import { PersonAvatar } from "@/shared/PersonAvatar";
import { tintStyle } from "@/shared/personColor";
import { fill, t } from "@/strings";
import { studentsQuery, type StudentRow } from "./api";

const s = t.students;
type Filter = "all" | "active" | "ending" | "ended" | "none" | "online" | "owing";

const ending = (row: StudentRow) => row.state === "active" && (row.remaining ?? 0) <= 2;
const MATCH: Record<Filter, (row: StudentRow) => boolean> = {
	all: () => true,
	active: (row) => row.state === "active",
	ending,
	ended: (row) => row.state === "ended",
	none: (row) => row.state === "none",
	online: (row) => row.state === "online",
	owing: (row) => row.owing > 0,
};

function stateOf(row: StudentRow): { tone: StatusTone; label: string } {
	if (row.state === "active") return { tone: ending(row) ? "warning" : "success", label: fill(s.sessionsLeft, { n: formatNumber(row.remaining ?? 0) }) };
	if (row.state === "ended") return { tone: "danger", label: s.ended };
	if (row.state === "online") {
		const parts = [row.programs ? fill(s.programCount, { n: formatNumber(row.programs) }) : "", row.packages ? fill(s.packageCount, { n: formatNumber(row.packages) }) : ""].filter(Boolean);
		return { tone: parts.length ? "info" : "neutral", label: parts.join(" · ") || s.noProgram };
	}
	return { tone: "neutral", label: s.noCourse };
}

function Card({ row }: { row: StudentRow }) {
	const state = stateOf(row);
	const used = row.total !== null && row.remaining !== null ? row.total - row.remaining : null;
	return (
		<Link to="/students/$id" params={{ id: String(row.id) }} style={tintStyle(row.id)} className="flex h-full flex-col gap-3 rounded-box border border-border bg-surface p-4 outline-none transition-colors hover:bg-surface-secondary focus-visible:ring-2 focus-visible:ring-accent">
			<span className="flex items-start gap-3">
				<PersonAvatar id={row.id} name={row.name} src={row.avatar ? `/api/admin/students/${row.id}/avatar?v=${row.avatar}` : null} />
				<span className="flex min-w-0 flex-1 flex-col">
					<span className="truncate font-semibold">{row.name}</span>
					<span className="truncate text-xs text-muted" dir="ltr" style={{ textAlign: "start" }}>{row.phone ?? "—"}</span>
				</span>
				<StatusChip size="sm" tone={state.tone} label={state.label} />
			</span>
			{used !== null && row.total ? (
				<span className="flex flex-col gap-1">
				<span className="text-sm">{row.class_title}</span>
				<UsageBar warningAt={101} dangerAt={101} size="compact" label={row.class_title ?? s.progress} used={used} total={row.total} valueText={fill(s.progressText, { used: formatNumber(used), total: formatNumber(row.total) })} />
				</span>
			) : (
				<span className="text-sm text-muted">{row.class_title ?? (row.kind === "ONLINE" ? t.students.online : s.noCourse)}</span>
			)}
			{row.owing > 0 ? <span className="text-sm font-medium text-danger">{fill(s.owes, { amount: formatToman(row.owing) })}</span> : null}
		</Link>
	);
}

export function StudentListPage() {
	const [filter, setFilter] = useState<Filter>("all");
	const [query, setQuery] = useState("");
	const search = useDeferredValue(query);
	const [draft, setDraft] = useState<StudentDraft | null>(null);
	const navigate = useNavigate();
	const { data, isPending, isError, refetch } = useQuery({ ...studentsQuery(null, search), placeholderData: keepPreviousData });

	const rows = data?.rows ?? [];
	const count = (name: Filter) => rows.filter(MATCH[name]).length;
	const shown = rows.filter(MATCH[filter]);

	return (
		<div className="flex flex-col gap-5">
			<PageHeader title={s.title} actions={<Button size="sm" onPress={() => setDraft(emptyStudent)}>{t.manage.addStudent}</Button>} />
			{data ? (
				<div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
					<StatCard label={s.stat.all} value={formatNumber(rows.length)} />
					<StatCard label={s.stat.active} value={formatNumber(count("active"))} />
					<StatCard label={s.stat.ending} value={formatNumber(count("ending"))} />
					<StatCard label={s.stat.owing} value={formatNumber(count("owing"))} />
				</div>
			) : null}
			<div className="flex flex-col gap-3 md:flex-row md:items-center">
				<div className="md:w-80">
					<SearchBox label={s.search} value={query} onChange={setQuery} />
				</div>
				<div className="min-w-0 flex-1">
					<ScrollChips
						label={s.title}
						value={filter}
						onChange={(value) => setFilter(value as Filter)}
						options={(Object.keys(s.filter) as Filter[]).map((key) => ({ value: key, label: `${s.filter[key]} (${formatNumber(count(key))})` }))}
					/>
				</div>
			</div>
			{isPending ? (
				<PageSkeleton />
			) : isError ? (
				<ErrorState onRetry={() => void refetch()} />
			) : shown.length === 0 ? (
				<EmptyState title={s.none} description={s.noneHint} />
			) : (
				<ul className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
					{shown.map((row) => (
						<li key={row.id}>
							<Card row={row} />
						</li>
					))}
				</ul>
			)}
			<StudentFormSheet draft={draft} onClose={() => setDraft(null)} onSaved={(id) => void navigate({ to: "/students/$id", params: { id: String(id) } })} />
		</div>
	);
}
