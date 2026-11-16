import { useMutation, useQuery } from "@tanstack/react-query";
import { Button, Notice, PageHeader, SectionCard, SelectField, TextAreaField } from "@nyxon/nasim";
import { useState } from "react";
import { apiFetch } from "@/shared/api";
import { t } from "@/strings";

const r = t.request;
type ClassOption = { id: number; title: string };
type Done = { ok: boolean; message: string };

export function RequestPage() {
	const classes = useQuery({ queryKey: ["me", "classes"], queryFn: () => apiFetch<ClassOption[]>("/api/me/classes") });
	const [classId, setClassId] = useState<string | null>(null);
	const [note, setNote] = useState("");
	const send = useMutation({
		mutationFn: () =>
			apiFetch<Done>("/api/me/course-request", {
				method: "POST",
				body: JSON.stringify({ class_type_id: classId ? Number(classId) : null, note: note.trim() || null }),
			}),
	});

	return (
		<div className="flex flex-col gap-6">
			<PageHeader title={r.title} description={r.hint} />
			<SectionCard title={r.title}>
				<div className="flex flex-col gap-4">
					{send.isSuccess ? (
						<Notice tone="success" title={r.sentTitle} role="status">{send.data.message}</Notice>
					) : (
						<>
							<SelectField
								label={r.classType}
								value={classId}
								onChange={setClassId}
								options={[{ value: "", label: r.anyClass }, ...(classes.data ?? []).map((c) => ({ value: String(c.id), label: c.title }))]}
							/>
							<TextAreaField label={r.note} placeholder={r.notePlaceholder} value={note} onChange={setNote} rows={3} maxLength={500} />
							{send.isError ? <Notice tone="danger" role="alert">{send.error.message}</Notice> : null}
							<Button isPending={send.isPending} onPress={() => send.mutate()}>{r.submit}</Button>
						</>
					)}
				</div>
			</SectionCard>
		</div>
	);
}
