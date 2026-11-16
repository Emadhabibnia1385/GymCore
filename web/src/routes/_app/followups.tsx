import { createFileRoute } from "@tanstack/react-router";
import { FollowUpsPage } from "@/features/followups";
import { requireRole } from "@/shared/guards";

export const Route = createFileRoute("/_app/followups")({
	beforeLoad: ({ context }) => requireRole(context.queryClient, "admin"),
	component: FollowUpsPage,
});
