import { useSuspenseQuery } from "@tanstack/react-query";
import { createFileRoute, redirect } from "@tanstack/react-router";
import { AppFrame } from "@/app/shell/AppFrame";
import { meQuery } from "@/features/auth";
import { ApiError } from "@/shared/api";

// Everything inside needs a signed-in person; anyone else goes to the login page.
export const Route = createFileRoute("/_app")({
	beforeLoad: async ({ context }) => {
		try {
			await context.queryClient.ensureQueryData(meQuery);
		} catch (error) {
			if (error instanceof ApiError && error.status === 401) throw redirect({ to: "/login" });
			throw error;
		}
	},
	component: Shell,
});

function Shell() {
	const { data: me } = useSuspenseQuery(meQuery);
	return <AppFrame me={me} />;
}
