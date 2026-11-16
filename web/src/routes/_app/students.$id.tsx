import { createFileRoute } from "@tanstack/react-router";
import { StudentProfilePage } from "@/features/students";
import { requireRole } from "@/shared/guards";

export const Route = createFileRoute("/_app/students/$id")({
	beforeLoad: ({ context }) => requireRole(context.queryClient, "admin"),
	component: Page,
});

function Page() {
	const { id } = Route.useParams();
	return <StudentProfilePage id={Number(id)} />;
}
