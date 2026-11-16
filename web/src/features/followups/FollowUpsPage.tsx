import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "@tanstack/react-router";
import { Button, EmptyState, ErrorState, FilterChips, PageHeader, PageSkeleton, StatusChip } from "@nyxon/nasim";
import { useState } from "react";
import { formatNumber } from "@/shared/format";
import { fill, t } from "@/strings";
import { completeFollowUp, dueQuery, leadOptionsQuery, leadsQuery, postponeFollowUp, renewalsQuery, summaryQuery, type Lead } from "./api";
import { FollowUpSheet, type FollowUpTarget } from "./FollowUpSheet";
import { LeadSheet } from "./LeadSheet";

const f = t.follow;
type Tab = "today" | "renewals" | "leads";

export function FollowUpsPage() {
	const [tab, setTab] = useState<Tab>("today");
	const summary = useQuery(summaryQuery);
	const n = (value: number | undefined) => formatNumber(value ?? 0);
	return (
		<div className="flex flex-col gap-4">
			<PageHeader title={f.title} description={f.hint} />
			<FilterChips
				label={f.title}
				value={tab}
				onChange={(value) => setTab(value as Tab)}
				options={[
					{ value: "today", label: fill(f.tabToday, { n: n(summary.data?.due) }) },
					{ value: "renewals", label: fill(f.tabRenewals, { n: n(summary.data?.renewals) }) },
					{ value: "leads", label: fill(f.tabLeads, { n: n(summary.data?.leads) }) },
				]}
			/>
			{tab === "today" ? <Today /> : tab === "renewals" ? <Renewals /> : <Leads />}
		</div>
	);
}

function Today() {
	const queryClient = useQueryClient();
	const { data, isPending, isError, refetch } = useQuery(dueQuery);
	const refresh = () => queryClient.invalidateQueries({ queryKey: ["admin"] });
	const done = useMutation({ mutationFn: completeFollowUp, onSuccess: refresh });
	const later = useMutation({ mutationFn: ({ id, days }: { id: number; days: number }) => postponeFollowUp(id, days), onSuccess: refresh });
	if (isPending) return <PageSkeleton />;
	if (isError) return <ErrorState onRetry={() => void refetch()} />;
	if (data.length === 0) return <EmptyState title={f.todayNone} />;
	return (
		<ul className="flex flex-col gap-3">
			{data.map((row) => (
				<li key={row.id} className="flex flex-col gap-3 rounded-field border border-border bg-surface p-4">
					<div className="flex items-start justify-between gap-2">
						<div className="flex flex-col">
							<span className="font-medium">{row.target}</span>
							{row.note ? <span className="text-sm text-muted">{row.note}</span> : null}
						</div>
						<StatusChip size="sm" tone={row.days_late > 0 ? "danger" : "warning"} label={row.days_late > 0 ? fill(f.late, { n: formatNumber(row.days_late) }) : f.dueToday} />
					</div>
					<div className="flex flex-wrap gap-2">
						<Button size="sm" isPending={done.isPending && done.variables === row.id} onPress={() => done.mutate(row.id)}>{f.done}</Button>
						{[[f.tomorrow, 1], [f.threeDays, 3], [f.week, 7]].map(([label, days]) => (
							<Button key={days} size="sm" variant="secondary" isPending={later.isPending && later.variables?.id === row.id && later.variables.days === days} onPress={() => later.mutate({ id: row.id, days: Number(days) })}>{label}</Button>
						))}
						{row.person_id ? <Link to="/students/$id" params={{ id: String(row.person_id) }} className="self-center text-sm text-accent underline">{f.openStudent}</Link> : null}
					</div>
				</li>
			))}
		</ul>
	);
}

function Renewals() {
	const [target, setTarget] = useState<FollowUpTarget | null>(null);
	const { data, isPending, isError, refetch } = useQuery(renewalsQuery);
	if (isPending) return <PageSkeleton />;
	if (isError) return <ErrorState onRetry={() => void refetch()} />;
	if (data.length === 0) return <EmptyState title={f.renewalsNone} description={f.renewalsHint} />;
	return (
		<>
			<p className="text-sm text-muted">{f.renewalsHint}</p>
			<ul className="flex flex-col gap-3">
				{data.map((row) => (
					<li key={row.person_id} className="flex flex-col gap-3 rounded-field border border-border bg-surface p-4">
						<div className="flex items-start justify-between gap-2">
							<div className="flex flex-col">
								<span className="font-medium">{row.student}</span>
								<span className="text-sm text-muted">{row.class_title} · {row.days_since === null ? f.endedUnknown : fill(f.endedAgo, { n: formatNumber(row.days_since) })}</span>
							</div>
							<StatusChip size="sm" tone={row.followed_up ? "success" : "warning"} label={row.followed_up ? f.followedUp : f.waiting} />
						</div>
						<div className="flex flex-wrap gap-2">
							<Link to="/courses/$id" params={{ id: String(row.course_id) }} className="inline-flex"><Button size="sm">{f.openCourse}</Button></Link>
							<Button size="sm" variant="secondary" onPress={() => setTarget({ name: row.student, personId: row.person_id })}>{f.followUp}</Button>
							<Link to="/students/$id" params={{ id: String(row.person_id) }} className="self-center text-sm text-accent underline">{f.openStudent}</Link>
						</div>
					</li>
				))}
			</ul>
			<FollowUpSheet target={target} onClose={() => setTarget(null)} />
		</>
	);
}

function Leads() {
	const [status, setStatus] = useState("NEW");
	const [open, setOpen] = useState<{ lead: Lead | null; isNew: boolean }>({ lead: null, isNew: false });
	const options = useQuery(leadOptionsQuery);
	const { data, isPending, isError, refetch } = useQuery(leadsQuery(status));
	return (
		<>
			<div className="flex items-center justify-between gap-2">
				<FilterChips
					label={f.tabLeads}
					value={status}
					onChange={setStatus}
					options={(options.data?.statuses ?? []).map((s) => ({ value: s.value, label: `${s.label} (${formatNumber(data?.counts[s.value] ?? 0)})` }))}
				/>
			</div>
			<Button size="sm" onPress={() => setOpen({ lead: null, isNew: true })}>{f.addLead}</Button>
			{isPending ? (
				<PageSkeleton />
			) : isError ? (
				<ErrorState onRetry={() => void refetch()} />
			) : data.rows.length === 0 ? (
				<EmptyState title={f.leadsNone} />
			) : (
				<ul className="flex flex-col gap-2">
					{data.rows.map((lead) => (
						<li key={lead.id}>
							<button type="button" className="flex min-h-14 w-full items-center justify-between gap-3 rounded-field border border-border bg-surface p-4 text-start outline-none hover:bg-surface-secondary focus-visible:ring-2 focus-visible:ring-accent" onClick={() => setOpen({ lead, isNew: false })}>
								<span className="flex flex-col">
									<span className="font-medium">{lead.name}</span>
									<span className="text-xs text-muted">{[lead.source_label, lead.interest].filter(Boolean).join(" · ")}</span>
								</span>
								{lead.next_follow_up ? <span className="text-xs text-muted">{lead.next_follow_up}</span> : null}
							</button>
						</li>
					))}
				</ul>
			)}
			<LeadSheet lead={open.lead} isNew={open.isNew} onClose={() => setOpen({ lead: null, isNew: false })} />
		</>
	);
}
