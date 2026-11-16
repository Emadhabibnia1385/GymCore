import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { useNavigate } from "@tanstack/react-router";
import { Button, EmptyState, ErrorState, FilterChips, PageHeader, PageSkeleton, SearchBox, StatusChip, type StatusTone } from "@nyxon/nasim";
import { useDeferredValue, useState } from "react";
import { emptyStudent, StudentFormSheet, type StudentDraft } from "@/features/manage";
import { CardLink } from "@/shared/CardLink";
import { formatNumber } from "@/shared/format";
import { fill, t } from "@/strings";
import { type Kind, studentsQuery, type StudentRow } from "./api";

const s = t.students;

function stateOf(row: StudentRow): { tone: StatusTone; label: string } {
	if (row.state === "active") return { tone: (row.remaining ?? 0) <= 2 ? "warning" : "success", label: fill(s.sessionsLeft, { n: formatNumber(row.remaining ?? 0) }) };
	if (row.state === "ended") return { tone: "danger", label: s.ended };
	if (row.state === "online") {
		const parts = [row.programs ? fill(s.programCount, { n: formatNumber(row.programs) }) : "", row.packages ? fill(s.packageCount, { n: formatNumber(row.packages) }) : ""].filter(Boolean);
		return { tone: parts.length ? "info" : "neutral", label: parts.join(" · ") || s.noProgram };
	}
	return { tone: "neutral", label: s.noCourse };
}

export function StudentListPage() {
	const [filter, setFilter] = useState<"all" | Kind>("all");
	const [query, setQuery] = useState("");
	const search = useDeferredValue(query);
	const [draft, setDraft] = useState<StudentDraft | null>(null);
	const navigate = useNavigate();
	const { data, isPending, isError, refetch } = useQuery({ ...studentsQuery(filter === "all" ? null : filter, search), placeholderData: keepPreviousData });

	return (
		<div className="flex flex-col gap-4">
			<PageHeader title={s.title} actions={<Button size="sm" onPress={() => setDraft(emptyStudent)}>{t.manage.addStudent}</Button>} />
			<SearchBox label={s.search} value={query} onChange={setQuery} />
			<FilterChips
				label={s.title}
				value={filter}
				onChange={(value) => setFilter(value as "all" | Kind)}
				options={[
					{ value: "all", label: data ? `${s.all} (${formatNumber(data.in_person + data.online)})` : s.all },
					{ value: "IN_PERSON", label: data ? `${s.inPerson} (${formatNumber(data.in_person)})` : s.inPerson },
					{ value: "ONLINE", label: data ? `${s.online} (${formatNumber(data.online)})` : s.online },
				]}
			/>
			{isPending ? (
				<PageSkeleton />
			) : isError ? (
				<ErrorState onRetry={() => void refetch()} />
			) : data.rows.length === 0 ? (
				<EmptyState title={s.none} description={s.noneHint} />
			) : (
				<ul className="flex flex-col gap-2">
					{data.rows.map((row) => {
						const state = stateOf(row);
						return (
							<li key={row.id}>
								<CardLink to="/students/$id" params={{ id: String(row.id) }}>
									<span className="font-medium">{row.name}</span>
									<StatusChip size="sm" tone={state.tone} label={state.label} />
								</CardLink>
							</li>
						);
					})}
				</ul>
			)}
					<StudentFormSheet draft={draft} onClose={() => setDraft(null)} onSaved={(id) => void navigate({ to: "/students/$id", params: { id: String(id) } })} />
		</div>
	);
}
