import { useQuery } from "@tanstack/react-query";
import { EmptyState, ErrorState, PageHeader, PageSkeleton } from "@nyxon/nasim";
import { CardLink } from "@/shared/CardLink";
import { t } from "@/strings";
import { myCoursesQuery } from "./api";
import { CourseSummaryCard } from "./CourseSummaryCard";

export function CourseListPage() {
	const { data, isPending, isError, refetch } = useQuery(myCoursesQuery);
	if (isPending) return <PageSkeleton />;
	if (isError) return <ErrorState as="h1" onRetry={() => void refetch()} />;
	return (
		<div className="flex flex-col gap-6">
			<PageHeader title={t.course.title} />
			{data.length === 0 ? (
				<EmptyState title={t.course.none} description={t.course.noneHint} action={{ label: t.course.requestAction, href: "/request" }} />
			) : (
				<ul className="flex flex-col gap-4">
					{data.map((course) => (
						<li key={course.id}>
							<CardLink to="/courses/$id" params={{ id: String(course.id) }}>
								<div className="min-w-0 flex-1">
									<CourseSummaryCard course={course} level={3} />
								</div>
							</CardLink>
						</li>
					))}
				</ul>
			)}
		</div>
	);
}
