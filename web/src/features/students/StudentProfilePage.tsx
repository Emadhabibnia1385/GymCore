import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate } from "@tanstack/react-router";
import { Button, ConfirmDialog, EmptyState, Notice, ErrorState, KeyValueList, PageHeader, PageSkeleton, SectionCard, StatCard, StaticTable, StatusChip, Tabs } from "@nyxon/nasim";
import { CourseSummaryCard } from "@/features/courses";
import { CourseFormSheet, deleteStudent, StudentFormSheet, type CourseDraft, type StudentDraft } from "@/features/manage";
import { PaymentSheet, type PaymentTarget } from "@/features/money";
import { NotesCard } from "./NotesCard";
import { WebAccessCard } from "./WebAccessCard";
import { useState } from "react";
import { formatNumber, formatToman } from "@/shared/format";
import { fill, t } from "@/strings";
import { studentQuery } from "./api";

const p = t.profile;

export function StudentProfilePage({ id }: { id: number }) {
	const { data, isPending, isError, refetch } = useQuery(studentQuery(id));
	const queryClient = useQueryClient();
	const navigate = useNavigate();
	const [editing, setEditing] = useState<StudentDraft | null>(null);
	const [course, setCourse] = useState<CourseDraft | null>(null);
	const [payment, setPayment] = useState<PaymentTarget | null>(null);
	const [confirmDelete, setConfirmDelete] = useState(false);
	const remove = useMutation({
		mutationFn: () => deleteStudent(id),
		onSuccess: async () => {
			await queryClient.invalidateQueries({ queryKey: ["admin"] });
			await navigate({ to: "/students" });
		},
	});
	if (isPending) return <PageSkeleton />;
	if (isError) return <ErrorState as="h1" onRetry={() => void refetch()} />;

	const accounts = [data.on_telegram ? p.telegram : "", data.on_bale ? p.bale : ""].filter(Boolean).join("، ");
	const active = data.courses.filter((course) => course.status === "ACTIVE");
	const others = data.courses.filter((course) => course.status !== "ACTIVE");
	const remaining = active.reduce((sum, course) => sum + course.remaining, 0);
	const newCourse = () => setCourse({ courseId: null, clientId: data.id, classTypeId: null, sessions: 12, tuition: 0, gymFee: 0, allowed: 2, weekdays: [], times: {} });
	const pay = () => {
		const latest = active[0] ?? data.courses[0];
		if (latest) setPayment({ personId: data.id, courseId: latest.id, name: data.name, course: latest.class_title });
	};
	const courseList = (list: typeof data.courses) => (
		<ul className="grid grid-cols-1 gap-4 xl:grid-cols-2">
			{list.map((item) => (
				<li key={item.id} className="flex flex-col gap-2">
					<CourseSummaryCard course={item} level={3} />
					<Link to="/courses/$id" params={{ id: String(item.id) }} className="text-sm text-accent underline">
						{t.course.manage}
					</Link>
				</li>
			))}
		</ul>
	);

	return (
		<div className="flex flex-col gap-6">
			<PageHeader
				title={data.name}
				backHref="/students"
				meta={<StatusChip size="sm" tone="neutral" label={data.kind === "ONLINE" ? t.students.online : t.students.inPerson} />}
				actions={
					<div className="flex flex-wrap gap-2">
						<Button size="sm" onPress={newCourse}>{t.manage.addCourse}</Button>
						{data.courses.length > 0 ? <Button size="sm" variant="secondary" onPress={pay}>{t.money.recordPayment}</Button> : null}
						<Button size="sm" variant="secondary" onPress={() => setEditing({ id: data.id, name: data.name, phone: data.phone ?? "", phone2: data.phone2 ?? "", kind: data.kind })}>{t.manage.editStudent}</Button>
					</div>
				}
			/>

			<div className="grid grid-cols-1 gap-3 min-[480px]:grid-cols-2 lg:grid-cols-4">
				<StatCard label={p.remaining} value={formatNumber(remaining)} hint={active.length > 0 ? active.map((course) => course.class_title).join("، ") : p.noActive} />
				<StatCard label={p.paid} value={formatToman(data.paid)} />
				<StatCard label={p.owing} value={data.owing > 0 ? formatToman(data.owing) : p.settled} />
				<StatCard label={p.programs} value={formatNumber(data.programs.length + data.packages.length)} hint={fill(p.coursesCount, { n: formatNumber(data.courses.length) })} />
			</div>

			<div className="grid grid-cols-1 items-start gap-6 lg:grid-cols-3">
				<div className="min-w-0 lg:col-span-2">
					<Tabs
						label={data.name}
						items={[
							{
								id: "courses",
								label: p.courses,
								content: (
									<div className="flex flex-col gap-6 pt-4">
										{data.courses.length === 0 ? <EmptyState title={p.noCourses} /> : null}
										{active.length > 0 ? courseList(active) : null}
										{others.length > 0 ? (
											<section className="flex flex-col gap-3">
												<h2 className="text-sm font-semibold text-muted">{p.past}</h2>
												{courseList(others)}
											</section>
										) : null}
									</div>
								),
							},
							{
								id: "money",
								label: p.money,
								content: (
									<div className="pt-4">
										{data.payments.length === 0 ? (
											<EmptyState title={p.noPayments} />
										) : (
											<StaticTable
												caption={p.payments}
												columns={[p.date, p.amount]}
												rows={data.payments.map((payment) => ({ id: String(payment.id), cells: [payment.date, formatToman(payment.amount)] }))}
											/>
										)}
									</div>
								),
							},
							{
								id: "programs",
								label: p.programs,
								content: (
									<div className="pt-4">
										{data.programs.length === 0 && data.packages.length === 0 ? (
											<EmptyState title={p.noPrograms} />
										) : (
											<ul className="grid grid-cols-1 gap-2 md:grid-cols-2">
												{data.packages.map((pkg) => (
													<li key={`pkg-${pkg.id}`} className="flex items-center justify-between rounded-field border border-border p-3">
														<span>📦 {pkg.title}</span>
														<span className="text-xs text-muted">{fill(t.programs.items, { n: formatNumber(pkg.items) })}</span>
													</li>
												))}
												{data.programs.map((program) => (
													<li key={program.id} className="flex items-center justify-between rounded-field border border-border p-3">
														<span>{program.title}</span>
														<span className="text-xs text-muted">{program.date}</span>
													</li>
												))}
											</ul>
										)}
									</div>
								),
							},
						]}
					/>
				</div>

				<div className="flex flex-col gap-6">
					<SectionCard title={p.contact}>
						<KeyValueList
							items={[
								{ label: p.phone, value: data.phone ?? "—", ltr: true },
								!!data.phone2 && { label: p.phone2, value: data.phone2, ltr: true },
								{ label: p.accounts, value: accounts || p.noAccounts },
							]}
						/>
					</SectionCard>
					<NotesCard id={data.id} name={data.name} />
					<WebAccessCard id={data.id} username={data.username} />
					{remove.isError ? <Notice tone="danger" role="alert">{remove.error.message}</Notice> : null}
					<Button variant="danger-soft" onPress={() => setConfirmDelete(true)}>{t.manage.deleteStudent}</Button>
				</div>
			</div>

			<ConfirmDialog isOpen={confirmDelete} onOpenChange={setConfirmDelete} tone="danger" title={t.manage.deleteStudentTitle} description={t.manage.deleteStudentBody} confirmLabel={t.manage.deleteGo} isPending={remove.isPending} onConfirm={() => remove.mutate()} />
			<StudentFormSheet draft={editing} onClose={() => setEditing(null)} />
			<CourseFormSheet draft={course} onClose={() => setCourse(null)} onSaved={(courseId) => courseId && void navigate({ to: "/courses/$id", params: { id: String(courseId) } })} />
			<PaymentSheet target={payment} onClose={() => setPayment(null)} />
		</div>
	);
}
