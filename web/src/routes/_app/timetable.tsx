import { createFileRoute } from "@tanstack/react-router";
import { TimetablePage } from "@/features/timetable";
import { requireRole } from "@/shared/guards";

export const Route = createFileRoute("/_app/timetable")({
	beforeLoad: ({ context }) => requireRole(context.queryClient, "admin"),
	component: TimetablePage,
});
