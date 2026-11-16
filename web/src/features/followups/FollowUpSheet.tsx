import { useMutation, useQueryClient } from "@tanstack/react-query";
import { BottomSheet, Button, Notice, TextField } from "@nyxon/nasim";
import { useState } from "react";
import { DatePick, isoDay } from "@/shared/DatePick";
import { fill, t } from "@/strings";
import { addFollowUp } from "./api";

const f = t.follow;
export type FollowUpTarget = { name: string; personId?: number; leadId?: number };

/** Schedule a follow-up for a student or a lead. */
export function FollowUpSheet({ target, onClose }: { target: FollowUpTarget | null; onClose: () => void }) {
	return (
		<BottomSheet isOpen={target !== null} onOpenChange={(open) => !open && onClose()} title={target ? fill(f.followUpFor, { name: target.name }) : ""}>
			{target ? <Form target={target} onClose={onClose} /> : null}
		</BottomSheet>
	);
}

function Form({ target, onClose }: { target: FollowUpTarget; onClose: () => void }) {
	const queryClient = useQueryClient();
	const [date, setDate] = useState(isoDay(1));
	const [note, setNote] = useState("");
	const save = useMutation({
		mutationFn: () => addFollowUp({ due_on: date, person_id: target.personId, lead_id: target.leadId, note: note.trim() || null }),
		onSuccess: async () => {
			await queryClient.invalidateQueries({ queryKey: ["admin"] });
			onClose();
		},
	});
	return (
		<div className="flex flex-col gap-4">
			{save.isError ? <Notice tone="danger" role="alert">{save.error.message}</Notice> : null}
			<DatePick label={f.followUpDate} value={date} onChange={setDate} />
			<TextField label={f.followUpNote} value={note} onChange={setNote} maxLength={300} />
			<Button size="lg" isDisabled={!date} isPending={save.isPending} onPress={() => save.mutate()}>{t.common.save}</Button>
		</div>
	);
}
