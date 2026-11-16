import { createFileRoute } from "@tanstack/react-router";
import { SettingsPage } from "@/features/config";
import { requireRole } from "@/shared/guards";

export const Route = createFileRoute("/_app/settings")({
	beforeLoad: ({ context }) => requireRole(context.queryClient, "admin"),
	component: SettingsPage,
});
