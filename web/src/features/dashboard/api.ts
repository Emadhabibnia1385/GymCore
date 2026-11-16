import { queryOptions } from "@tanstack/react-query";
import { apiFetch } from "@/shared/api";

export type AdminDashboard = {
	totals: { clients: number; active_courses: number; programs: number };
	month: { label: string; income: number; expenses: number; net: number; payments: number };
	year_label: string;
	months: { month: number; label: string; income: number; expenses: number; net: number }[];
	owing: { count: number; total: number; top: { student: string; class_title: string; amount: number }[] };
	today_label: string;
	today: { time: string; student: string; class_title: string }[];
	follow_ups: { due: number; renewals: number; open_leads: number };
};

export const dashboardQuery = queryOptions({
	queryKey: ["admin", "dashboard"],
	queryFn: () => apiFetch<AdminDashboard>("/api/admin/dashboard"),
	staleTime: 60_000,
});
