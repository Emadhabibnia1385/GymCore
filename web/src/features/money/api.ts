import { queryOptions } from "@tanstack/react-query";
import { apiFetch } from "@/shared/api";

export type Line = { key: string; label: string; amount: number };
export type MonthView = {
	jy: number; jm: number; label: string; income: number; income_by_kind: Line[]; payments: number; corrections: number;
	expenses: number; expenses_by_category: Line[]; net: number; prev: [number, number]; next: [number, number] | null;
};
export type YearView = { jy: number; rows: { jm: number; label: string; income: number; expenses: number; net: number }[]; income: number; expenses: number; net: number };
export type ExpenseRow = { id: number; amount: number; date: string; category: string; category_label: string; note: string | null };
export type Owing = { person_id: number; course_id: number; student: string; class_title: string; amount: number };
export type Option = { value: string; label: string };
export type Saved = { ok: boolean; message: string };

export const monthQuery = (jy: number | null, jm: number | null) =>
	queryOptions({ queryKey: ["admin", "finance", "month", jy, jm], queryFn: () => apiFetch<MonthView>(`/api/admin/finance/month${jy && jm ? `?jy=${jy}&jm=${jm}` : ""}`) });
export const yearQuery = (jy: number) => queryOptions({ queryKey: ["admin", "finance", "year", jy], queryFn: () => apiFetch<YearView>(`/api/admin/finance/year?jy=${jy}`) });
export const expensesQuery = (jy: number, jm: number) =>
	queryOptions({ queryKey: ["admin", "finance", "expenses", jy, jm], queryFn: () => apiFetch<ExpenseRow[]>(`/api/admin/finance/expenses?jy=${jy}&jm=${jm}`) });
export const owingQuery = queryOptions({ queryKey: ["admin", "owing"], queryFn: () => apiFetch<Owing[]>("/api/admin/payments/owing") });
export const kindsQuery = queryOptions({ queryKey: ["admin", "payment-kinds"], queryFn: () => apiFetch<Option[]>("/api/admin/payments/kinds"), staleTime: Infinity });
export const categoriesQuery = queryOptions({ queryKey: ["admin", "categories"], queryFn: () => apiFetch<Option[]>("/api/admin/finance/categories"), staleTime: Infinity });

const post = <T>(path: string, body: unknown) => apiFetch<T>(path, { method: "POST", body: JSON.stringify(body) });
export const recordPayment = (body: { person_id: number; course_id: number | null; amount: number; kind: string; paid_at: string; note: string | null }) => post<Saved>("/api/admin/payments", body);
export const recordExpense = (body: { amount: number; category: string; spent_at: string; note: string | null }) => post<Saved>("/api/admin/expenses", body);
