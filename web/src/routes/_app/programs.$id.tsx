import { createFileRoute } from "@tanstack/react-router";
import { PackagePage } from "@/features/programs";
import { requireRole } from "@/shared/guards";

export const Route = createFileRoute("/_app/programs/$id")({
	beforeLoad: ({ context }) => requireRole(context.queryClient, "student"),
	component: Page,
});

function Page() {
	const { id } = Route.useParams();
	return <PackagePage id={Number(id)} />;
}
