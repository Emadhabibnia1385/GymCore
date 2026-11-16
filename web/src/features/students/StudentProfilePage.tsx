import { useQuery } from "@tanstack/react-query";
import { Link } from "@tanstack/react-router";
import { EmptyState, ErrorState, KeyValueList, PageHeader, PageSkeleton, SectionCard, StaticTable, StatusChip } from "@nyxon/nasim";
import { CourseSummaryCard } from "@/features/courses";
import { formatNumber, formatToman } from "@/shared/format";
import { fill, t } from "@/strings";
import { studentQuery } from "./api";

const p = t.profile;

export function StudentProfilePage({ id }: { id: number }) {
	const { data, isPending, isError, refetch } = useQuery(studentQuery(id));
	if (isPending) return <PageSkeleton />;
	if (isError) return <ErrorState as="h1" onRetry={() => void refetch()} />;

	const accounts = [data.on_telegram ? p.telegram : "", data.on_bale ? p.bale : ""].filter(Boolean).join("، ");
	return (
		<div className="flex flex-col gap-6">
			<PageHeader title={data.name} backHref="/students" meta={<StatusChip size="sm" tone="neutral" label={data.kind === "ONLINE" ? t.students.online : t.students.inPerson} />} />

			<SectionCard title={data.name}>
				<KeyValueList
					layout="grid"
					items={[
						{ label: p.phone, value: data.phone ?? "—", ltr: true },
						!!data.phone2 && { label: p.phone2, value: data.phone2, ltr: true },
						{ label: p.accounts, value: accounts || p.noAccounts },
						{ label: p.notes, value: formatNumber(data.notes), numeric: true },
					]}
				/>
			</SectionCard>

			<SectionCard title={p.courses}>
				{data.courses.length === 0 ? (
					<EmptyState title={p.noCourses} />
				) : (
					<ul className="flex flex-col gap-4">
						{data.courses.map((course) => (
							<li key={course.id} className="flex flex-col gap-2">
								<CourseSummaryCard course={course} level={3} />
								<Link to="/courses/$id" params={{ id: String(course.id) }} className="text-sm text-accent underline">
									{t.course.grid}
								</Link>
							</li>
						))}
					</ul>
				)}
			</SectionCard>

			<SectionCard title={p.money}>
				<div className="flex flex-col gap-4">
					<KeyValueList
						layout="grid"
						items={[
							{ label: p.paid, value: formatToman(data.paid), numeric: true },
							{ label: p.owing, value: data.owing > 0 ? formatToman(data.owing) : p.settled, numeric: true },
						]}
					/>
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
			</SectionCard>

			<SectionCard title={p.programs}>
				{data.programs.length === 0 && data.packages.length === 0 ? (
					<EmptyState title={p.noPrograms} />
				) : (
					<ul className="flex flex-col gap-2">
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
			</SectionCard>
		</div>
	);
}
