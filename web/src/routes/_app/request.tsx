import { createFileRoute } from "@tanstack/react-router";
import { RequestPage } from "@/features/request";
import { requireRole } from "@/shared/guards";

export const Route = createFileRoute("/_app/request")({
	beforeLoad: ({ context }) => requireRole(context.queryClient, "student"),
	component: RequestPage,
});
