import { useSuspenseQuery } from "@tanstack/react-query";
import { createFileRoute } from "@tanstack/react-router";
import { meQuery } from "@/features/auth";
import { AdminDashboard, StudentHome } from "@/features/dashboard";

export const Route = createFileRoute("/_app/")({ component: Home });

function Home() {
	const { data: me } = useSuspenseQuery(meQuery);
	return me.role === "admin" ? <AdminDashboard /> : <StudentHome name={me.name} />;
}
