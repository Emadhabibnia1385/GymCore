import { createFileRoute } from "@tanstack/react-router";
import { StudentListPage } from "@/features/students";
import { requireRole } from "@/shared/guards";

export const Route = createFileRoute("/_app/students/")({
	beforeLoad: ({ context }) => requireRole(context.queryClient, "admin"),
	component: StudentListPage,
});
