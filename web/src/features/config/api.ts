import { queryOptions } from "@tanstack/react-query";
import { apiFetch } from "@/shared/api";

export type Setting = { key: string; label: string; kind: "text" | "long" | "number" | "toggle" | "link"; value: string };
export type Contact = { id: number; label: string; url: string; icon: string | null; active: boolean };
export type Saved = { ok: boolean; message: string };

export const settingsQuery = queryOptions({ queryKey: ["admin", "settings"], queryFn: () => apiFetch<Setting[]>("/api/admin/settings") });
export const contactsQuery = queryOptions({ queryKey: ["admin", "contacts"], queryFn: () => apiFetch<Contact[]>("/api/admin/contacts") });
export const audienceQuery = queryOptions({ queryKey: ["admin", "audience"], queryFn: () => apiFetch<{ count: number }>("/api/admin/notify/audience") });

const send = <T>(method: string, path: string, body?: unknown) => apiFetch<T>(method === "GET" ? path : path, { method, body: body === undefined ? undefined : JSON.stringify(body) });
export const saveSetting = (key: string, value: string) => send<Saved>("PUT", `/api/admin/settings/${key}`, { value });
export const patchContact = (id: number, body: { label?: string; url?: string; active?: boolean }) => send<Contact>("PATCH", `/api/admin/contacts/${id}`, body);
export const moveContact = (id: number, direction: -1 | 1) => send<Saved>("POST", `/api/admin/contacts/${id}/move`, { direction });
export const broadcast = (text: string) => send<{ count: number; message: string }>("POST", "/api/admin/notify/broadcast", { text });
export const lowSessions = () => send<{ count: number; message: string }>("POST", "/api/admin/notify/low-sessions");
