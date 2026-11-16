import { createFileRoute } from "@tanstack/react-router";
import { CourseListPage } from "@/features/courses";
import { requireRole } from "@/shared/guards";

export const Route = createFileRoute("/_app/courses/")({
	beforeLoad: ({ context }) => requireRole(context.queryClient, "student"),
	component: CourseListPage,
});
