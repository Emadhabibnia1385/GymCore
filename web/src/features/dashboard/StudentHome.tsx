import { EmptyState, PageHeader } from "@nyxon/nasim";
import { fill, t } from "@/strings";

export function StudentHome({ name }: { name: string }) {
	return (
		<div className="flex flex-col gap-6">
			<PageHeader title={t.student.title} description={fill(t.student.hello, { name })} />
			<EmptyState title={t.student.soonTitle} description={t.student.soonHint} />
		</div>
	);
}
