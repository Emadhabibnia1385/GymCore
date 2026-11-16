import { queryOptions } from "@tanstack/react-query";
import { apiFetch } from "@/shared/api";

export type CourseSummary = {
	id: number;
	class_title: string;
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
	date: string;
	weekday: string;
	status: string | null;
	label: string;
	session_no: number | null;
	note: string | null;
};

export type CourseDetail = CourseSummary & { slots: Slot[] };

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
