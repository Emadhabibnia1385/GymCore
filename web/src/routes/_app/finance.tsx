import { createFileRoute } from "@tanstack/react-router";
import { FinancePage } from "@/features/money";
import { requireRole } from "@/shared/guards";

export const Route = createFileRoute("/_app/finance")({
	beforeLoad: ({ context }) => requireRole(context.queryClient, "admin"),
	component: FinancePage,
});
