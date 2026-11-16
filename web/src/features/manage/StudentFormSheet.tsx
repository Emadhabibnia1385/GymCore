import { useMutation, useQueryClient } from "@tanstack/react-query";
import { BottomSheet, Button, Notice, SelectField, TextField } from "@nyxon/nasim";
import { useState } from "react";
import { t } from "@/strings";
import { createStudent, updateStudent, type StudentBody } from "./api";

const g = t.manage;
export type StudentDraft = { id: number | null; name: string; phone: string; phone2: string; kind: StudentBody["kind"] };
export const emptyStudent: StudentDraft = { id: null, name: "", phone: "", phone2: "", kind: "IN_PERSON" };

/** Add a student, or edit one (an empty phone removes it). */
export function StudentFormSheet({ draft, onClose, onSaved }: { draft: StudentDraft | null; onClose: () => void; onSaved?: (id: number) => void }) {
	return (
		<BottomSheet isOpen={draft !== null} onOpenChange={(open) => !open && onClose()} title={draft?.id ? g.editStudent : g.addStudent}>
			{draft ? <Form key={draft.id ?? "new"} draft={draft} onClose={onClose} onSaved={onSaved} /> : null}
		</BottomSheet>
	);
}

function Form({ draft, onClose, onSaved }: { draft: StudentDraft; onClose: () => void; onSaved?: (id: number) => void }) {
	const queryClient = useQueryClient();
	const [name, setName] = useState(draft.name);
	const [phone, setPhone] = useState(draft.phone);
	const [phone2, setPhone2] = useState(draft.phone2);
	const [kind, setKind] = useState<string | null>(draft.kind);
	const save = useMutation({
		mutationFn: async () => {
			const body = { name: name.trim(), phone: phone.trim() || null, phone2: phone2.trim() || null, kind: (kind ?? "IN_PERSON") as StudentBody["kind"] };
			if (draft.id) {
				// An empty text is how the server is told to remove a phone.
				await updateStudent(draft.id, { ...body, phone: phone.trim(), phone2: phone2.trim() });
				return draft.id;
			}
			return (await createStudent(body)).id;
		},
		onSuccess: async (id) => {
			await queryClient.invalidateQueries({ queryKey: ["admin"] });
			onSaved?.(id);
			onClose();
		},
	});
	return (
		<div className="flex flex-col gap-4">
			{save.isError ? <Notice tone="danger" role="alert">{save.error.message}</Notice> : null}
			<TextField label={g.studentName} value={name} onChange={setName} maxLength={120} isRequired />
			<TextField label={g.phone} description={g.phoneHint} value={phone} onChange={setPhone} dir="ltr" inputMode="tel" />
			<TextField label={g.phone2} value={phone2} onChange={setPhone2} dir="ltr" inputMode="tel" />
			<SelectField label={g.kind} value={kind} onChange={setKind} options={[{ value: "IN_PERSON", label: g.inPerson }, { value: "ONLINE", label: g.online }]} />
			<Button size="lg" isDisabled={!name.trim()} isPending={save.isPending} onPress={() => save.mutate()}>
				{t.common.save}
			</Button>
		</div>
	);
}
