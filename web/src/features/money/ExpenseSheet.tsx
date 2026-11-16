import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { BottomSheet, Button, Notice, NumberField, SelectField, TextField } from "@nyxon/nasim";
import { useState } from "react";
import { DatePick, isoDay } from "@/shared/DatePick";
import { t } from "@/strings";
import { categoriesQuery, recordExpense } from "./api";

const m = t.money;

export function ExpenseSheet({ isOpen, onClose }: { isOpen: boolean; onClose: () => void }) {
	return (
		<BottomSheet isOpen={isOpen} onOpenChange={(open) => !open && onClose()} title={m.recordExpense}>
			{isOpen ? <Form onClose={onClose} /> : null}
		</BottomSheet>
	);
}

function Form({ onClose }: { onClose: () => void }) {
	const queryClient = useQueryClient();
	const categories = useQuery(categoriesQuery);
	const [amount, setAmount] = useState<number | undefined>();
	const [category, setCategory] = useState<string | null>("OTHER");
	const [date, setDate] = useState(isoDay(0));
	const [note, setNote] = useState("");
	const save = useMutation({
		mutationFn: () => recordExpense({ amount: amount ?? 0, category: category ?? "OTHER", spent_at: date, note: note.trim() || null }),
		onSuccess: async () => {
			await queryClient.invalidateQueries({ queryKey: ["admin"] });
			onClose();
		},
	});
	return (
		<div className="flex flex-col gap-4">
			<p className="text-sm text-muted">{m.expenseHint}</p>
			{save.isError ? <Notice tone="danger" role="alert">{save.error.message}</Notice> : null}
			<NumberField label={t.common.amount} value={amount} onChange={setAmount} formatOptions={{ useGrouping: true }} />
			<SelectField label={m.expenseCategory} value={category} onChange={setCategory} options={categories.data ?? []} />
			<DatePick label={m.expenseDate} value={date} onChange={setDate} />
			<TextField label={t.common.note} value={note} onChange={setNote} maxLength={300} />
			<Button size="lg" isDisabled={!amount || !date} isPending={save.isPending} onPress={() => save.mutate()}>
				{m.recordExpense}
			</Button>
		</div>
	);
}
