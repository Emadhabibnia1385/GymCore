import { useMutation, useQuery } from "@tanstack/react-query";
import { Link } from "@tanstack/react-router";
import { Button, Notice, PageHeader, SectionCard, TextAreaField } from "@nyxon/nasim";
import { useState } from "react";
import { apiFetch } from "@/shared/api";
import { formatNumber } from "@/shared/format";
import { t } from "@/strings";

const r = t.request;
type ClassOption = { id: number; title: string };
type Done = { ok: boolean; message: string };

// The week from Saturday, and the parts of a day: what the student can offer the coach.
const DAYS = ["شنبه", "یک‌شنبه", "دوشنبه", "سه‌شنبه", "چهارشنبه", "پنج‌شنبه"] as const;
const PARTS = [r.partMorning, r.partNoon, r.partEvening, r.partNight] as const;

function Toggle({ on, onClick, children }: { on: boolean; onClick: () => void; children: string }) {
	return (
		<button
			type="button"
			aria-pressed={on}
			onClick={onClick}
			className={`min-h-11 rounded-field border px-3 text-sm outline-none transition-colors focus-visible:ring-2 focus-visible:ring-accent ${on ? "border-accent bg-accent/15 font-medium text-accent" : "border-border text-muted hover:bg-surface-secondary"}`}
		>
			{children}
		</button>
	);
}

const flip = <T,>(list: T[], value: T) => (list.includes(value) ? list.filter((item) => item !== value) : [...list, value]);

function Steps({ items, from = 1 }: { items: string[]; from?: number }) {
	return (
		<ol className="flex flex-col gap-4 text-sm">
			{items.map((step, index) => (
				<li key={step} className="flex items-start gap-3">
					<span className="flex size-7 shrink-0 items-center justify-center rounded-full bg-accent/15 font-bold text-accent tabular-nums">{formatNumber(index + from)}</span>
					<span className="pt-0.5">{step}</span>
				</li>
			))}
		</ol>
	);
}

export function RequestPage() {
	const classes = useQuery({ queryKey: ["me", "classes"], queryFn: () => apiFetch<ClassOption[]>("/api/me/classes") });
	const [classId, setClassId] = useState<number | null>(null);
	const [days, setDays] = useState<string[]>([]);
	const [parts, setParts] = useState<string[]>([]);
	const [note, setNote] = useState("");
	const send = useMutation({
		mutationFn: () => {
			// The coach reads one note, so the choices go into it as plain words.
			const lines = [
				days.length > 0 ? `${r.daysLine}: ${days.join("، ")}` : "",
				parts.length > 0 ? `${r.partsLine}: ${parts.join("، ")}` : "",
				note.trim(),
			].filter(Boolean);
			return apiFetch<Done>("/api/me/course-request", {
				method: "POST",
				body: JSON.stringify({ class_type_id: classId, note: lines.join("\n") || null }),
			});
		},
	});

	if (send.isSuccess) {
		return (
			<div className="mx-auto flex w-full max-w-xl flex-col gap-6">
				<PageHeader title={r.title} />
				<Notice tone="success" title={r.sentTitle} role="status">{send.data.message}</Notice>
				<SectionCard title={r.nextTitle}>
					<Steps items={[r.step2, r.step3]} from={1} />
				</SectionCard>
				<Link to="/" className="inline-flex min-h-11 items-center justify-center rounded-field bg-accent px-4 font-medium text-accent-foreground">{r.backHome}</Link>
			</div>
		);
	}

	return (
		<div className="flex flex-col gap-6">
			<PageHeader title={r.title} description={r.hint} />
			<div className="grid grid-cols-1 items-start gap-6 lg:grid-cols-3">
				<div className="flex min-w-0 flex-col gap-6 lg:col-span-2">
					<SectionCard title={r.classType} description={r.classHint}>
						<div role="radiogroup" aria-label={r.classType} className="grid grid-cols-1 gap-2 sm:grid-cols-2">
							{[{ id: null, title: r.anyClass }, ...(classes.data ?? [])].map((option) => {
								const chosen = classId === option.id;
								return (
									<button
										key={option.id ?? "any"}
										type="button"
										role="radio"
										aria-checked={chosen}
										onClick={() => setClassId(option.id)}
										className={`flex min-h-14 items-center justify-between gap-3 rounded-field border p-3 text-start outline-none transition-colors focus-visible:ring-2 focus-visible:ring-accent ${chosen ? "border-accent bg-accent/10" : "border-border hover:bg-surface-secondary"}`}
									>
										<span className="font-medium">{option.title}</span>
										<span aria-hidden className={`size-5 shrink-0 rounded-full border-2 ${chosen ? "border-accent bg-accent" : "border-border"}`} />
									</button>
								);
							})}
						</div>
					</SectionCard>

					<SectionCard title={r.whenTitle} description={r.whenHint}>
						<div className="flex flex-col gap-4">
							<div className="flex flex-col gap-2">
								<span className="text-sm font-medium">{r.daysLine}</span>
								<div className="grid grid-cols-3 gap-2 sm:grid-cols-6">
									{DAYS.map((day) => <Toggle key={day} on={days.includes(day)} onClick={() => setDays(flip(days, day))}>{day}</Toggle>)}
								</div>
							</div>
							<div className="flex flex-col gap-2">
								<span className="text-sm font-medium">{r.partsLine}</span>
								<div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
									{PARTS.map((part) => <Toggle key={part} on={parts.includes(part)} onClick={() => setParts(flip(parts, part))}>{part}</Toggle>)}
								</div>
							</div>
						</div>
					</SectionCard>

					<SectionCard title={r.note}>
						<div className="flex flex-col gap-4">
							<TextAreaField label={r.note} placeholder={r.notePlaceholder} value={note} onChange={setNote} rows={3} maxLength={500} />
							{send.isError ? <Notice tone="danger" role="alert">{send.error.message}</Notice> : null}
							<Button size="lg" isPending={send.isPending} onPress={() => send.mutate()}>{r.submit}</Button>
						</div>
					</SectionCard>
				</div>

				<SectionCard title={r.howTitle}>
					<Steps items={[r.step1, r.step2, r.step3]} />
					<p className="mt-4 text-xs text-muted">{r.payNote}</p>
				</SectionCard>
			</div>
		</div>
	);
}
