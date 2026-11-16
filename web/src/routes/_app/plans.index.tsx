import { createFileRoute } from "@tanstack/react-router";
import { PlansPage } from "@/features/plans";
import { requireRole } from "@/shared/guards";

export const Route = createFileRoute("/_app/plans/")({
	beforeLoad: ({ context }) => requireRole(context.queryClient, "admin"),
	component: PlansPage,
});
