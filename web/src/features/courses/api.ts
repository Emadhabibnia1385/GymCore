import { queryOptions } from "@tanstack/react-query";
import { apiFetch } from "@/shared/api";

export type CourseSummary = {
	id: number;
	client_id: number;
	client_name: string;
	class_title: string;
	class_type_id: number;
	weekdays: number[];
	class_times: Record<string, string>;
	status: "ACTIVE" | "FINISHED" | "PAUSED";
	status_label: string;
	start: string;
	schedule: string;
	total: number;
	consumed: number;
	remaining: number;
	allowed_absence: number;
	absent_allowed: number;
	absent_unauthorized: number;
};

export type Slot = {
	iso: string;
	date: string;
	weekday: string;
	status: string | null;
	label: string;
	session_no: number | null;
	note: string | null;
};

export type CoursePayment = { id: number; amount: number; date: string; kind: string; note: string | null };
export type CourseDetail = CourseSummary & {
	slots: Slot[];
	tuition?: number;
	gym_fee?: number;
	paid?: number;
	outstanding?: number;
	payments?: CoursePayment[];
	notes?: number;
};

export const myCoursesQuery = queryOptions({
	queryKey: ["me", "courses"],
	queryFn: () => apiFetch<CourseSummary[]>("/api/me/courses"),
});

/** The student reads their own course; the coach reads any course by id. */
export const courseQuery = (role: "admin" | "student", id: number) =>
	queryOptions({
		queryKey: [role, "course", id],
		queryFn: () => apiFetch<CourseDetail>(role === "admin" ? `/api/admin/courses/${id}` : `/api/me/courses/${id}`),
	});
