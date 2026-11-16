import { createFileRoute } from "@tanstack/react-router";
import { AttendancePage } from "@/features/attendance";
import { requireRole } from "@/shared/guards";

export const Route = createFileRoute("/_app/attendance")({
	beforeLoad: ({ context }) => requireRole(context.queryClient, "admin"),
	component: AttendancePage,
});
