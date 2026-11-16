import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "@tanstack/react-router";
import { Button, ConfirmDialog, Notice } from "@nyxon/nasim";
import { useState } from "react";
import type { CourseDetail } from "@/features/courses";
import { PaymentSheet, type PaymentTarget } from "@/features/money";
import { t } from "@/strings";
import { deleteCourse, renewCourse, setCourseStatus } from "./api";
import { CourseFormSheet, type CourseDraft } from "./CourseFormSheet";

const g = t.manage;
type Ask = "finish" | "renew" | "delete" | null;

/** What the coach can do with one course: edit, record a payment, finish or reactivate, renew, delete. */
export function CourseActions({ course }: { course: CourseDetail }) {
	const queryClient = useQueryClient();
	const navigate = useNavigate();
	const [ask, setAsk] = useState<Ask>(null);
	const [draft, setDraft] = useState<CourseDraft | null>(null);
	const [payment, setPayment] = useState<PaymentTarget | null>(null);
	const refresh = () => queryClient.invalidateQueries({ queryKey: ["admin"] });
	const status = useMutation({ mutationFn: (next: "ACTIVE" | "FINISHED") => setCourseStatus(course.id, next), onSuccess: refresh });
	const renew = useMutation({
		mutationFn: () => renewCourse(course.id),
		onSuccess: async (made) => {
			await refresh();
			setAsk(null);
			await navigate({ to: "/courses/$id", params: { id: String(made.id) } });
		},
	});
	const remove = useMutation({
		mutationFn: () => deleteCourse(course.id),
		onSuccess: async () => {
			await refresh();
			setAsk(null);
			await navigate({ to: "/students/$id", params: { id: String(course.client_id) } });
		},
	});
	const active = course.status === "ACTIVE";
	const error = status.error ?? renew.error ?? remove.error;

	return (
		<div className="flex flex-col gap-3">
			{error ? <Notice tone="danger" role="alert">{error.message}</Notice> : null}
			<div className="grid grid-cols-2 gap-2">
				<Button variant="secondary" onPress={() => setPayment({ personId: course.client_id, courseId: course.id, name: course.client_name, course: course.class_title })}>{t.money.recordPayment}</Button>
				<Button variant="secondary" onPress={() => setDraft({ courseId: course.id, clientId: course.client_id, classTypeId: course.class_type_id, sessions: course.total, tuition: course.tuition ?? 0, gymFee: course.gym_fee ?? 0, allowed: course.allowed_absence, weekdays: course.weekdays, times: Object.fromEntries(Object.entries(course.class_times).map(([day, time]) => [Number(day), time])) as Record<number, string> })}>{g.editCourse}</Button>
				{active ? (
					<Button variant="secondary" onPress={() => setAsk("finish")}>{g.finishCourse}</Button>
				) : (
					<Button variant="secondary" isPending={status.isPending} onPress={() => status.mutate("ACTIVE")}>{g.reactivate}</Button>
				)}
				<Button variant="secondary" onPress={() => setAsk("renew")}>{g.renew}</Button>
			</div>
			<Button variant="danger-soft" onPress={() => setAsk("delete")}>{g.deleteCourse}</Button>

			<ConfirmDialog isOpen={ask === "finish"} onOpenChange={(open) => !open && setAsk(null)} title={g.finishTitle} description={g.finishBody} confirmLabel={g.finishGo} isPending={status.isPending} onConfirm={() => status.mutate("FINISHED", { onSuccess: () => setAsk(null) })} />
			<ConfirmDialog isOpen={ask === "renew"} onOpenChange={(open) => !open && setAsk(null)} title={g.renewTitle} description={g.renewBody} confirmLabel={g.renewGo} isPending={renew.isPending} onConfirm={() => renew.mutate()} />
			<ConfirmDialog isOpen={ask === "delete"} onOpenChange={(open) => !open && setAsk(null)} tone="danger" title={g.deleteCourseTitle} description={g.deleteCourseBody} confirmLabel={g.deleteGo} isPending={remove.isPending} onConfirm={() => remove.mutate()} />
			<CourseFormSheet draft={draft} onClose={() => setDraft(null)} />
			<PaymentSheet target={payment} onClose={() => setPayment(null)} />
		</div>
	);
}
