import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { BottomSheet, Button, Notice, NumberField, SelectField, TextField } from "@nyxon/nasim";
import { useState } from "react";
import { DatePick, isoDay } from "@/shared/DatePick";
import { fill, t } from "@/strings";
import { kindsQuery, recordPayment } from "./api";

const m = t.money;
export type PaymentTarget = { personId: number; courseId: number | null; name: string; course: string };

/** Record a payment for one student's course; a negative amount corrects an earlier one. */
export function PaymentSheet({ target, onClose }: { target: PaymentTarget | null; onClose: () => void }) {
	return (
		<BottomSheet isOpen={target !== null} onOpenChange={(open) => !open && onClose()} title={target ? fill(m.paymentFor, { name: target.name, course: target.course }) : ""}>
			{target ? <Form key={`${target.personId}-${target.courseId}`} target={target} onClose={onClose} /> : null}
		</BottomSheet>
	);
}

function Form({ target, onClose }: { target: PaymentTarget; onClose: () => void }) {
	const queryClient = useQueryClient();
	const kinds = useQuery(kindsQuery);
	const [amount, setAmount] = useState<number | undefined>();
	const [kind, setKind] = useState<string | null>("TUITION");
	const [date, setDate] = useState(isoDay(0));
	const [note, setNote] = useState("");
	const save = useMutation({
		mutationFn: () => recordPayment({ person_id: target.personId, course_id: target.courseId, amount: amount ?? 0, kind: kind ?? "TUITION", paid_at: date, note: note.trim() || null }),
		onSuccess: async () => {
			await queryClient.invalidateQueries({ queryKey: ["admin"] });
			onClose();
		},
	});
	return (
		<div className="flex flex-col gap-4">
			<p className="text-sm text-muted">{m.paymentHint}</p>
			{save.isError ? <Notice tone="danger" role="alert">{save.error.message}</Notice> : null}
			<NumberField label={t.common.amount} value={amount} onChange={setAmount} formatOptions={{ useGrouping: true }} />
			<SelectField label={m.paymentKind} value={kind} onChange={setKind} options={kinds.data ?? []} />
			<DatePick label={m.paymentDate} value={date} onChange={setDate} />
			<TextField label={t.common.note} value={note} onChange={setNote} maxLength={300} />
			<Button size="lg" isDisabled={!amount || !date} isPending={save.isPending} onPress={() => save.mutate()}>
				{m.recordPayment}
			</Button>
		</div>
	);
}
