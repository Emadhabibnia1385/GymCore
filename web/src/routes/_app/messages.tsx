import { createFileRoute } from "@tanstack/react-router";
import { MessagesPage } from "@/features/config";
import { requireRole } from "@/shared/guards";

export const Route = createFileRoute("/_app/messages")({
	beforeLoad: ({ context }) => requireRole(context.queryClient, "admin"),
	component: MessagesPage,
});
