import { queryOptions } from "@tanstack/react-query";
import { apiFetch } from "@/shared/api";

export type DayRow = { course_id: number; student: string; class_title: string; time: string; status: string | null; label: string };
export type Day = { iso: string; label: string; is_today: boolean; is_future: boolean; prev: string; next: string; rows: DayRow[] };
export type Outcome = { value: string; label: string };
export type Saved = { ok: boolean; message: string };

export const dayQuery = (iso: string | null) =>
	queryOptions({
		queryKey: ["admin", "attendance", iso ?? "today"],
		queryFn: () => apiFetch<Day>(`/api/admin/attendance/day${iso ? `?date=${iso}` : ""}`),
	});

export const outcomesQuery = queryOptions({
	queryKey: ["admin", "attendance", "outcomes"],
	queryFn: () => apiFetch<Outcome[]>("/api/admin/attendance/statuses"),
	staleTime: Infinity,
});

const post = <T>(path: string, body: unknown) => apiFetch<T>(path, { method: "POST", body: JSON.stringify(body) });

export const recordAttendance = (body: { course_id: number; date: string; status: string; note?: string | null }) => post<Saved>("/api/admin/attendance", body);
export const moveSession = (body: { course_id: number; date: string; new_date: string }) => post<Saved>("/api/admin/attendance/move", body);

export type SheetCell = { status: string | null; session_no: number | null; paid: boolean };
export type Sheet = {
	jy: number;
	jm: number;
	label: string;
	prev: [number, number];
	next: [number, number] | null;
	days: { iso: string; day: number; weekday: string; friday: boolean; today: boolean }[];
	columns: { course_id: number; student: string; class_title: string; status: string }[];
	cells: Record<string, Record<string, SheetCell>>;
};
export const sheetQuery = (month: [number, number] | null) =>
	queryOptions({
		queryKey: ["admin", "attendance", "sheet", month],
		queryFn: () => apiFetch<Sheet>(`/api/admin/attendance/sheet${month ? `?year=${month[0]}&month=${month[1]}` : ""}`),
	});
