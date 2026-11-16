import { queryOptions } from "@tanstack/react-query";
import { apiFetch } from "@/shared/api";

export type Summary = { due: number; renewals: number; leads: number; waiting: boolean };
export type FollowUp = { id: number; target: string; person_id: number | null; lead_id: number | null; due: string; due_iso: string; days_late: number; note: string | null };
export type Renewal = { person_id: number; student: string; course_id: number; class_title: string; ended: string | null; days_since: number | null; followed_up: boolean };
export type Lead = {
	id: number; name: string; phone: string | null; source: string; source_label: string; interest: string | null; status: string;
	status_label: string; note: string | null; person_id: number | null; existing_student: number | null; next_follow_up: string | null;
};
export type LeadList = { counts: Record<string, number>; rows: Lead[] };
export type Option = { value: string; label: string };
export type Note = { id: number; date: string; text: string };
export type Saved = { ok: boolean; message: string };

export const summaryQuery = queryOptions({ queryKey: ["admin", "followups", "summary"], queryFn: () => apiFetch<Summary>("/api/admin/followups/summary") });
export const dueQuery = queryOptions({ queryKey: ["admin", "followups", "due"], queryFn: () => apiFetch<FollowUp[]>("/api/admin/followups/due") });
export const renewalsQuery = queryOptions({ queryKey: ["admin", "renewals"], queryFn: () => apiFetch<Renewal[]>("/api/admin/renewals") });
export const leadsQuery = (status: string) => queryOptions({ queryKey: ["admin", "leads", status], queryFn: () => apiFetch<LeadList>(`/api/admin/leads?status=${status}`) });
export const leadOptionsQuery = queryOptions({ queryKey: ["admin", "lead-options"], queryFn: () => apiFetch<{ sources: Option[]; statuses: Option[] }>("/api/admin/leads/options"), staleTime: Infinity });
export const notesQuery = (id: number) => queryOptions({ queryKey: ["admin", "notes", id], queryFn: () => apiFetch<Note[]>(`/api/admin/students/${id}/notes`) });

const send = <T>(method: string, path: string, body?: unknown) => apiFetch<T>(path, { method, body: body === undefined ? undefined : JSON.stringify(body) });
export const completeFollowUp = (id: number) => send<Saved>("POST", `/api/admin/followups/${id}/done`);
export const postponeFollowUp = (id: number, days: number) => send<Saved>("POST", `/api/admin/followups/${id}/postpone`, { days });
export const addFollowUp = (body: { due_on: string; person_id?: number; lead_id?: number; note: string | null }) => send<Saved>("POST", "/api/admin/followups", body);
export const createLead = (body: { name: string; phone: string | null; source: string; interest: string | null }) => send<Lead>("POST", "/api/admin/leads", body);
export const patchLead = (id: number, body: { status?: string; phone?: string; note?: string; follow_up_on?: string }) => send<Lead>("PATCH", `/api/admin/leads/${id}`, body);
export const convertLead = (id: number, kind: string) => send<{ person_id: number; linked: boolean; message: string }>("POST", `/api/admin/leads/${id}/convert`, { kind });
export const deleteLead = (id: number) => send<Saved>("DELETE", `/api/admin/leads/${id}`);
export const addNote = (id: number, text: string) => send<Saved>("POST", `/api/admin/students/${id}/notes`, { text });
