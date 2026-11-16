import { queryOptions } from "@tanstack/react-query";
import { apiFetch } from "@/shared/api";

export type Line = { key: string; label: string; amount: number };
export type Report = {
	year: number;
	kpis: {
		students: number;
		courses_active: number;
		courses_finished: number;
		courses_paused: number;
		ending_soon: number;
		income_year: number;
		expenses_year: number;
		net_year: number;
		average_payment: number;
		owing_total: number;
		owing_count: number;
		income_this_month: number | null;
		income_last_month: number | null;
		expenses_this_month: number | null;
		expenses_last_month: number | null;
	};
	months: { month: number; label: string; income: number; expenses: number; net: number; previous_income: number; new_students: number; new_courses: number }[];
	attendance: { present: number; absent_allowed: number; absent_unauthorized: number; cancelled: number; holiday: number; rate: number };
	weeks: { label: string; present: number; absent: number }[];
	classes: { title: string; active_courses: number; income: number }[];
	income_by_kind: Line[];
	expenses_by_category: Line[];
	debtors: { course_id: number; student: string; class_title: string; amount: number }[];
	ending_soon: { course_id: number; student: string; class_title: string; remaining: number }[];
};

export const reportQuery = (year: number | null) =>
	queryOptions({
		queryKey: ["admin", "reports", year],
		queryFn: () => apiFetch<Report>(`/api/admin/reports${year ? `?year=${year}` : ""}`),
	});
