import { queryOptions, useQuery } from "@tanstack/react-query";
import { Link } from "@tanstack/react-router";
import { EmptyState, ErrorState, PageHeader, PageSkeleton, SectionCard } from "@nyxon/nasim";
import { apiFetch } from "@/shared/api";
import { t } from "@/strings";

type Day = { day: number; name: string; entries: { time: string; student: string; class_title: string; person_id: number; course_id: number }[] };
const weekQuery = queryOptions({ queryKey: ["admin", "timetable"], queryFn: () => apiFetch<Day[]>("/api/admin/timetable") });
const w = t.week;

export function TimetablePage() {
	const { data, isPending, isError, refetch } = useQuery(weekQuery);
	if (isPending) return <PageSkeleton />;
	if (isError) return <ErrorState as="h1" onRetry={() => void refetch()} />;
	return (
		<div className="flex flex-col gap-6">
			<PageHeader title={w.title} description={w.hint} />
			<div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
				{data.map((day) => (
					<SectionCard key={day.day} title={day.name} level={3}>
						{day.entries.length === 0 ? (
							<EmptyState title={w.noClass} />
						) : (
							<ul className="flex flex-col gap-2">
								{day.entries.map((entry) => (
									<li key={entry.course_id}>
										<Link to="/courses/$id" params={{ id: String(entry.course_id) }} className="flex items-center justify-between gap-3 rounded-field border border-border p-3 hover:bg-surface-secondary">
											<span className="flex flex-col">
												<span className="font-medium">{entry.student}</span>
												<span className="text-xs text-muted">{entry.class_title}</span>
											</span>
											<span className="text-sm text-muted" dir="ltr">{entry.time || w.noTime}</span>
										</Link>
									</li>
								))}
							</ul>
						)}
					</SectionCard>
				))}
			</div>
		</div>
	);
}
