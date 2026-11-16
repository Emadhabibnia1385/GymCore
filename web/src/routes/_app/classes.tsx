import { createFileRoute } from "@tanstack/react-router";
import { ClassesPage } from "@/features/manage";
import { requireRole } from "@/shared/guards";

export const Route = createFileRoute("/_app/classes")({
	beforeLoad: ({ context }) => requireRole(context.queryClient, "admin"),
	component: ClassesPage,
});
