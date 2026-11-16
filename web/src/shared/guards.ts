import type { QueryClient } from "@tanstack/react-query";
import { redirect } from "@tanstack/react-router";
import { meQuery, type Me } from "@/features/auth";

/** For a route only one role has: anyone else goes back to the home page. */
export async function requireRole(queryClient: QueryClient, role: Me["role"]): Promise<void> {
	const me = await queryClient.ensureQueryData(meQuery);
	if (me.role !== role) throw redirect({ to: "/" });
}
