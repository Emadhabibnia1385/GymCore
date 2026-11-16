import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { BottomSheet, Button, MultiSelect, Notice, NumberField, SelectField, TextField } from "@nyxon/nasim";
import { useState } from "react";
import { DatePick, isoDay } from "@/shared/DatePick";
import { fill, t } from "@/strings";
import { classesQuery, createCourse, updateCourse } from "./api";

const g = t.manage;
export type CourseDraft = {
	courseId: number | null; // null: a new course
	clientId: number;
	classTypeId: number | null;
	sessions: number;
	tuition: number;
	gymFee: number;
	allowed: number;
	weekdays: number[];
	times: Record<number, string>;
};

export function CourseFormSheet({ draft, onClose, onSaved }: { draft: CourseDraft | null; onClose: () => void; onSaved?: (id: number | null) => void }) {
	return (
		<BottomSheet isOpen={draft !== null} onOpenChange={(open) => !open && onClose()} title={draft?.courseId ? g.editCourse : g.addCourse}>
			{draft ? <Form key={draft.courseId ?? "new"} draft={draft} onClose={onClose} onSaved={onSaved} /> : null}
		</BottomSheet>
	);
}

function Form({ draft, onClose, onSaved }: { draft: CourseDraft; onClose: () => void; onSaved?: (id: number | null) => void }) {
	const queryClient = useQueryClient();
	const classes = useQuery(classesQuery);
	const editing = draft.courseId !== null;
	const [classId, setClassId] = useState<string | null>(draft.classTypeId ? String(draft.classTypeId) : null);
	const [sessions, setSessions] = useState<number | undefined>(draft.sessions);
	const [tuition, setTuition] = useState<number | undefined>(draft.tuition);
	const [gymFee, setGymFee] = useState<number | undefined>(draft.gymFee);
	const [allowed, setAllowed] = useState<number | undefined>(draft.allowed);
	const [start, setStart] = useState(isoDay(0));
	const [days, setDays] = useState<string[]>(draft.weekdays.map(String));
	const [times, setTimes] = useState<Record<number, string>>(draft.times);

	const picked = days.map(Number).sort((a, b) => a - b);
	const save = useMutation({
		mutationFn: async () => {
			const common = { tuition: tuition ?? 0, gym_fee: gymFee ?? 0, allowed_absence: allowed ?? 0, weekdays: picked, class_times: times };
			if (draft.courseId) {
				await updateCourse(draft.courseId, common);
				return draft.courseId;
			}
			return (await createCourse({ ...common, client_id: draft.clientId, class_type_id: Number(classId), sessions_total: sessions ?? 0, start_date: start })).id;
		},
		onSuccess: async (id) => {
			await queryClient.invalidateQueries({ queryKey: ["admin"] });
			onSaved?.(id);
			onClose();
		},
	});
	const ready = picked.length > 0 && (editing || (classId !== null && !!sessions && !!start));
	const money = { formatOptions: { useGrouping: true }, minValue: 0 } as const;

	return (
		<div className="flex flex-col gap-4">
			{save.isError ? <Notice tone="danger" role="alert">{save.error.message}</Notice> : null}
			{editing ? null : (
				<>
					<SelectField label={g.classType} value={classId} onChange={setClassId} options={(classes.data ?? []).filter((c) => c.active).map((c) => ({ value: String(c.id), label: c.title }))} />
					<NumberField label={g.sessions} value={sessions} onChange={setSessions} minValue={1} maxValue={200} />
					<DatePick label={g.startDate} value={start} onChange={setStart} />
				</>
			)}
			<NumberField label={g.tuition} value={tuition} onChange={setTuition} {...money} />
			<NumberField label={g.gymFee} value={gymFee} onChange={setGymFee} {...money} />
			<NumberField label={g.allowedAbsence} description={g.allowedHint} value={allowed} onChange={setAllowed} minValue={0} maxValue={100} />
			<MultiSelect label={g.weekdays} value={days} onChange={setDays} options={t.weekdays.map((name, index) => ({ value: String(index), label: name }))} />
			{picked.length > 0 ? (
				<fieldset className="flex flex-col gap-3">
					<legend className="mb-1 text-sm font-medium">{g.times}</legend>
					{picked.map((day) => (
						<TextField key={day} label={fill(g.timeFor, { day: t.weekdays[day] })} description={g.timeHint} value={times[day] ?? ""} onChange={(value) => setTimes((current) => ({ ...current, [day]: value }))} dir="ltr" maxLength={5} />
					))}
				</fieldset>
			) : null}
			<Button size="lg" isDisabled={!ready} isPending={save.isPending} onPress={() => save.mutate()}>
				{t.common.save}
			</Button>
		</div>
	);
}
