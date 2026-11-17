import { queryOptions } from "@tanstack/react-query";
import { apiFetch } from "@/shared/api";
import type { CourseSummary } from "@/features/courses";

export type Kind = "IN_PERSON" | "ONLINE";
export type StudentRow = {
	id: number;
	name: string;
	kind: Kind;
	state: "active" | "ended" | "none" | "online";
	remaining: number | null;
	programs: number;
	packages: number;
	phone: string | null;
	avatar: number;
	class_title: string | null;
	total: number | null;
	owing: number;
};
export type StudentList = { in_person: number; online: number; rows: StudentRow[] };

export type Program = { id: number; title: string; type_title: string; date: string; iso: string; note: string | null; kind: string | null; has_file: boolean };
export type PackageSummary = { id: number; title: string; description: string | null; items: number };
export type StudentStats = {
	present: number;
	absent_allowed: number;
	absent_unauthorized: number;
	cancelled: number;
	rate: number | null;
	since: string | null;
	courses: number;
	last_session: string | null;
	next_session: string | null;
	average_payment: number;
	payment_count: number;
};
export type ActivityRow = { kind: "attendance" | "payment" | "note" | "program"; date: string; iso: string; title: string; detail: string | null; amount: number | null; status: string | null };
export type StudentProfile = {
	id: number;
	name: string;
	phone: string | null;
	phone2: string | null;
	kind: Kind;
	on_telegram: boolean;
	on_bale: boolean;
	courses: CourseSummary[];
	paid: number;
	owing: number;
	payments: { id: number; amount: number; date: string; kind: string; note: string | null }[];
	programs: Program[];
	packages: PackageSummary[];
	notes: number;
	username: string | null;
	avatar: number;
	stats: StudentStats;
	activity: ActivityRow[];
};

export const studentsQuery = (kind: Kind | null, q: string) =>
	queryOptions({
		queryKey: ["admin", "students", kind, q],
		queryFn: () => {
			const params = new URLSearchParams();
			if (kind) params.set("kind", kind);
			if (q.trim()) params.set("q", q.trim());
			return apiFetch<StudentList>(`/api/admin/students?${params}`);
		},
	});

export const studentQuery = (id: number) =>
	queryOptions({ queryKey: ["admin", "student", id], queryFn: () => apiFetch<StudentProfile>(`/api/admin/students/${id}`) });
