import { createFileRoute } from "@tanstack/react-router";
import { ProgramsPage } from "@/features/programs";
import { requireRole } from "@/shared/guards";

export const Route = createFileRoute("/_app/programs/")({
	beforeLoad: ({ context }) => requireRole(context.queryClient, "student"),
	component: ProgramsPage,
});
