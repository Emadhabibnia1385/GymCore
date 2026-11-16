import { queryOptions, useQuery } from "@tanstack/react-query";
import { EmptyState, ErrorState, PageHeader, PageSkeleton } from "@nyxon/nasim";
import { Link } from "@tanstack/react-router";
import { CourseSummaryCard, type CourseSummary } from "@/features/courses";
import { apiFetch } from "@/shared/api";
import { CardLink } from "@/shared/CardLink";
import { formatNumber } from "@/shared/format";
import { fill, t } from "@/strings";

type Home = { name: string; active_course: CourseSummary | null; programs: number; packages: number };
const homeQuery = queryOptions({ queryKey: ["me", "home"], queryFn: () => apiFetch<Home>("/api/me/home") });
const s = t.student;

export function StudentHome() {
	const { data, isPending, isError, refetch } = useQuery(homeQuery);
	if (isPending) return <PageSkeleton />;
	if (isError) return <ErrorState as="h1" onRetry={() => void refetch()} />;

	return (
		<div className="flex flex-col gap-6">
			<PageHeader title={fill(s.hello, { name: data.name })} description={s.subscription} />

			{data.active_course ? (
				<>
					<CourseSummaryCard course={data.active_course} />
					<Link to="/courses/$id" params={{ id: String(data.active_course.id) }} className="text-accent underline">
						{s.openCourse}
					</Link>
				</>
			) : (
				<EmptyState title={s.noSubscription} description={s.noSubscriptionHint} action={{ label: t.course.requestAction, href: "/request" }} />
			)}

			<CardLink to="/programs">
				<div className="flex flex-col gap-1">
					<span className="font-medium">{s.library}</span>
					<span className="text-sm text-muted">{s.libraryHint}</span>
				</div>
				<span className="shrink-0 text-sm text-muted">
					{fill(s.counts, { programs: formatNumber(data.programs), packages: formatNumber(data.packages) })}
				</span>
			</CardLink>
		</div>
	);
}
