import { useQuery } from "@tanstack/react-query";
import { EmptyState, ErrorState, PageHeader, PageSkeleton, SectionCard } from "@nyxon/nasim";
import { CardLink } from "@/shared/CardLink";
import { formatNumber } from "@/shared/format";
import { fill, t } from "@/strings";
import { myPackagesQuery, myProgramsQuery, sendProgram } from "./api";
import { SendButton } from "./SendButton";

const p = t.programs;

export function ProgramsPage() {
	const programs = useQuery(myProgramsQuery);
	const packages = useQuery(myPackagesQuery);
	if (programs.isPending || packages.isPending) return <PageSkeleton />;
	if (programs.isError || packages.isError) return <ErrorState as="h1" onRetry={() => { void programs.refetch(); void packages.refetch(); }} />;
	const nothing = programs.data.length === 0 && packages.data.length === 0;

	return (
		<div className="flex flex-col gap-6">
			<PageHeader title={p.title} />
			{nothing ? <EmptyState title={p.none} description={p.noneHint} /> : null}

			{packages.data.length > 0 ? (
				<SectionCard title={p.packages}>
					<ul className="flex flex-col gap-2">
						{packages.data.map((pkg) => (
							<li key={pkg.id}>
								<CardLink to="/programs/$id" params={{ id: String(pkg.id) }}>
									<span className="font-medium">📦 {pkg.title}</span>
									<span className="text-xs text-muted">{fill(p.items, { n: formatNumber(pkg.items) })}</span>
								</CardLink>
							</li>
						))}
					</ul>
				</SectionCard>
			) : null}

			{programs.data.length > 0 ? (
				<SectionCard title={p.singles}>
					<ul className="flex flex-col gap-3">
						{programs.data.map((program) => (
							<li key={program.id} className="flex flex-col gap-2 rounded-field border border-border p-3">
								<div className="flex items-center justify-between gap-2">
									<span className="font-medium">{program.title}</span>
									<span className="text-xs text-muted">{program.date}</span>
								</div>
								{program.note ? <p className="whitespace-pre-line text-sm text-muted">{program.note}</p> : null}
								{program.has_file ? <SendButton send={() => sendProgram(program.id)} /> : null}
							</li>
						))}
					</ul>
				</SectionCard>
			) : null}
		</div>
	);
}
