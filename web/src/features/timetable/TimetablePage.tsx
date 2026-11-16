import { queryOptions, useQuery } from "@tanstack/react-query";
import { Link } from "@tanstack/react-router";
import { EmptyState, ErrorState, PageHeader, PageSkeleton } from "@nyxon/nasim";
import { apiFetch } from "@/shared/api";
import { formatNumber } from "@/shared/format";
import { TINT, tintStyle } from "@/shared/personColor";
import { t } from "@/strings";

type Entry = { time: string; student: string; class_title: string; person_id: number; course_id: number };
type Day = { day: number; name: string; entries: Entry[] };
const weekQuery = queryOptions({ queryKey: ["admin", "timetable"], queryFn: () => apiFetch<Day[]>("/api/admin/timetable") });
const w = t.week;

const hourOf = (time: string) => {
	const hour = Number.parseInt(time.split(":")[0] ?? "", 10);
	return Number.isFinite(hour) ? hour : null;
};

/** The first and last hour with a class, padded to a readable range. */
function hourRange(days: Day[]): number[] {
	const hours = days.flatMap((day) => day.entries.map((entry) => hourOf(entry.time))).filter((hour): hour is number => hour !== null);
	if (hours.length === 0) return [];
	const first = Math.min(...hours);
	const last = Math.max(...hours);
	return Array.from({ length: last - first + 1 }, (_, index) => first + index);
}

function Chip({ entry, withTime }: { entry: Entry; withTime?: boolean }) {
	return (
		<Link to="/courses/$id" params={{ id: String(entry.course_id) }} style={tintStyle(entry.person_id)} className={`flex flex-col rounded-field px-2 py-1 text-xs leading-5 outline-none focus-visible:ring-2 focus-visible:ring-accent ${TINT}`}>
			<span className="font-semibold">{entry.student}</span>
			<span className="opacity-80">{withTime && entry.time ? `${entry.time} · ` : ""}{entry.class_title}</span>
		</Link>
	);
}

export function TimetablePage() {
	const { data, isPending, isError, refetch } = useQuery(weekQuery);
	if (isPending) return <PageSkeleton />;
	if (isError) return <ErrorState as="h1" onRetry={() => void refetch()} />;
	const hours = hourRange(data);
	const untimed = (day: Day) => day.entries.filter((entry) => hourOf(entry.time) === null);
	const anyUntimed = data.some((day) => untimed(day).length > 0);
	const total = data.reduce((sum, day) => sum + day.entries.length, 0);

	return (
		<div className="flex flex-col gap-6">
			<PageHeader title={w.title} description={w.hint} meta={<span className="text-sm text-muted">{`${formatNumber(total)} ${w.sessions}`}</span>} />
			{total === 0 ? (
				<EmptyState title={w.noClass} />
			) : (
				<>
					{/* A wide screen gets the whole week as one grid: days down, hours across. */}
					<div className="hidden overflow-x-auto rounded-box border border-border md:block">
						<table className="w-full border-collapse text-center">
							<thead>
								<tr className="bg-surface-secondary text-sm">
									<th scope="col" className="sticky end-0 z-10 w-24 bg-surface-secondary p-2" />
									{hours.map((hour) => (
										<th key={hour} scope="col" className="min-w-36 border-s border-border p-2 font-medium tabular-nums">{`${formatNumber(hour)}–${formatNumber(hour + 1)}`}</th>
									))}
									{anyUntimed ? <th scope="col" className="min-w-36 border-s border-border p-2 font-medium">{w.noTime}</th> : null}
								</tr>
							</thead>
							<tbody>
								{data.map((day) => (
									<tr key={day.day} className={`border-t border-border align-top ${day.day === 6 ? "bg-danger/10" : ""}`}>
										<th scope="row" className="sticky end-0 z-10 bg-surface p-2 text-sm font-semibold">{day.name}</th>
										{hours.map((hour) => {
											const here = day.entries.filter((entry) => hourOf(entry.time) === hour);
											return (
												<td key={hour} className="border-s border-border p-1.5">
													<div className="flex flex-wrap gap-1 [&>a]:min-w-28 [&>a]:flex-1">{here.map((entry) => <Chip key={entry.course_id} entry={entry} withTime />)}</div>
												</td>
											);
										})}
										{anyUntimed ? (
											<td className="border-s border-border p-1.5">
												<div className="flex flex-wrap gap-1 [&>a]:min-w-28 [&>a]:flex-1">{untimed(day).map((entry) => <Chip key={entry.course_id} entry={entry} />)}</div>
											</td>
										) : null}
									</tr>
								))}
							</tbody>
						</table>
					</div>

					{/* A phone reads it day by day. */}
					<div className="flex flex-col gap-3 md:hidden">
						{data.map((day) => (
							<section key={day.day} className={`rounded-box border border-border p-3 ${day.day === 6 ? "bg-danger/10" : "bg-surface"}`}>
								<h2 className="mb-2 text-sm font-semibold">{day.name}</h2>
								{day.entries.length === 0 ? (
									<p className="text-sm text-muted">{w.noClass}</p>
								) : (
									<div className="grid grid-cols-2 gap-2">{day.entries.map((entry) => <Chip key={entry.course_id} entry={entry} withTime />)}</div>
								)}
							</section>
						))}
					</div>
				</>
			)}
		</div>
	);
}
