import { useSuspenseQuery } from "@tanstack/react-query";
import { createFileRoute } from "@tanstack/react-router";
import { meQuery } from "@/features/auth";
import { CourseDetailPage } from "@/features/courses";

// Both roles open a course: the student their own, the coach any (the server decides).
export const Route = createFileRoute("/_app/courses/$id")({ component: Page });

function Page() {
	const { id } = Route.useParams();
	const { data: me } = useSuspenseQuery(meQuery);
	return <CourseDetailPage role={me.role} id={Number(id)} backHref={me.role === "admin" ? "/students" : "/courses"} />;
}
