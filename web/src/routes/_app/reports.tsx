import { createFileRoute } from "@tanstack/react-router";
import { ReportsPage } from "@/features/reports";
import { requireRole } from "@/shared/guards";

export const Route = createFileRoute("/_app/reports")({
	beforeLoad: ({ context }) => requireRole(context.queryClient, "admin"),
	component: ReportsPage,
});
