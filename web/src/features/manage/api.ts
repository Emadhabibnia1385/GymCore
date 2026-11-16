import { queryOptions } from "@tanstack/react-query";
import { apiFetch } from "@/shared/api";

export type ClassType = { id: number; title: string; active: boolean };
export type Created = { id: number; message: string };
export type Saved = { ok: boolean; message: string };

export const classesQuery = queryOptions({ queryKey: ["admin", "classes"], queryFn: () => apiFetch<ClassType[]>("/api/admin/classes") });

const send = <T>(method: string, path: string, body?: unknown) => apiFetch<T>(path, { method, body: body === undefined ? undefined : JSON.stringify(body) });

export type StudentBody = { name: string; phone: string | null; phone2: string | null; kind: "IN_PERSON" | "ONLINE" };
export const createStudent = (body: StudentBody) => send<Created>("POST", "/api/admin/students", body);
export const updateStudent = (id: number, body: Partial<StudentBody>) => send<Saved>("PATCH", `/api/admin/students/${id}`, body);
export const deleteStudent = (id: number) => send<Saved>("DELETE", `/api/admin/students/${id}`);

export type CourseBody = {
	client_id: number; class_type_id: number; sessions_total: number; tuition: number; gym_fee: number;
	allowed_absence: number; start_date: string; weekdays: number[]; class_times: Record<number, string>;
};
export const createCourse = (body: CourseBody) => send<Created>("POST", "/api/admin/courses", body);
export const updateCourse = (id: number, body: { tuition: number; gym_fee: number; allowed_absence: number; weekdays: number[]; class_times: Record<number, string> }) =>
	send<unknown>("PATCH", `/api/admin/courses/${id}`, body);
export const setCourseStatus = (id: number, status: "ACTIVE" | "FINISHED" | "PAUSED") => send<Saved>("POST", `/api/admin/courses/${id}/status`, { status });
export const renewCourse = (id: number) => send<Created>("POST", `/api/admin/courses/${id}/renew`);
export const deleteCourse = (id: number) => send<Saved>("DELETE", `/api/admin/courses/${id}`);

export const createClass = (title: string) => send<Created>("POST", "/api/admin/classes", { title });
export const updateClass = (id: number, body: { title?: string; active?: boolean }) => send<Saved>("PATCH", `/api/admin/classes/${id}`, body);
export const deleteClass = (id: number) => send<Saved>("DELETE", `/api/admin/classes/${id}`);
