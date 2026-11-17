import { useQuery } from "@tanstack/react-query";
import { Link } from "@tanstack/react-router";
import { EmptyState, ErrorState, PageHeader, PageSkeleton, SectionCard, StatCard, StatusChip } from "@nyxon/nasim";
import { useState } from "react";
import { formatNumber } from "@/shared/format";
import { ScrollChips } from "@/shared/ScrollChips";
import { fill, t } from "@/strings";
import { myPackagesQuery, myProgramsQuery, sendProgram } from "./api";
import { SendButton } from "./SendButton";

const p = t.programs;
const FRESH_DAYS = 14; // a program this recent is marked «new»
const KIND_ICON: Record<string, string> = { video: "🎬", photo: "🖼", document: "📄" };

const daysSince = (iso: string) => Math.floor((Date.now() - new Date(`${iso}T12:00:00`).getTime()) / 86_400_000);

export function ProgramsPage() {
	const programs = useQuery(myProgramsQuery);
	const packages = useQuery(myPackagesQuery);
	const [type, setType] = useState("all");
	if (programs.isPending || packages.isPending) return <PageSkeleton />;
	if (programs.isError || packages.isError) return <ErrorState as="h1" onRetry={() => { void programs.refetch(); void packages.refetch(); }} />;

	const newest = [...programs.data].sort((a, b) => b.iso.localeCompare(a.iso));
	const types = [...new Set(newest.map((program) => program.type_title))];
	const shown = type === "all" ? newest : newest.filter((program) => program.type_title === type);
	const nothing = programs.data.length === 0 && packages.data.length === 0;
	const fresh = newest.filter((program) => daysSince(program.iso) <= FRESH_DAYS).length;

	return (
		<div className="flex flex-col gap-6">
			<PageHeader title={p.title} description={p.hint} />
			{nothing ? (
				<EmptyState title={p.none} description={p.noneHint} />
			) : (
				<div className="grid grid-cols-3 gap-3">
					<StatCard label={p.singles} value={formatNumber(programs.data.length)} />
					<StatCard label={p.packages} value={formatNumber(packages.data.length)} />
					<StatCard label={p.fresh} value={formatNumber(fresh)} />
				</div>
			)}

			{packages.data.length > 0 ? (
				<SectionCard title={p.packages} description={p.packagesHint}>
					<ul className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
						{packages.data.map((pkg) => (
							<li key={pkg.id}>
								<Link to="/programs/$id" params={{ id: String(pkg.id) }} className="flex h-full flex-col gap-2 rounded-box border border-border bg-surface p-4 outline-none transition-colors hover:bg-surface-secondary focus-visible:ring-2 focus-visible:ring-accent">
									<span className="flex items-start justify-between gap-2">
										<span className="text-2xl" aria-hidden>📦</span>
										<StatusChip size="sm" tone="info" label={fill(p.items, { n: formatNumber(pkg.items) })} />
									</span>
									<span className="font-semibold">{pkg.title}</span>
									{pkg.description ? <span className="line-clamp-2 text-sm text-muted">{pkg.description}</span> : null}
									<span className="mt-auto pt-1 text-sm text-accent">{p.openPackage}</span>
								</Link>
							</li>
						))}
					</ul>
				</SectionCard>
			) : null}

			{programs.data.length > 0 ? (
				<section className="flex flex-col gap-3">
					<h2 className="text-lg font-semibold">{p.singles}</h2>
					{types.length > 1 ? (
						<ScrollChips label={p.singles} value={type} onChange={setType} options={[{ value: "all", label: `${p.allTypes} (${formatNumber(newest.length)})` }, ...types.map((name) => ({ value: name, label: `${name} (${formatNumber(newest.filter((program) => program.type_title === name).length)})` }))]} />
					) : null}
					<ul className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
						{shown.map((program) => (
							<li key={program.id} className="flex flex-col gap-3 rounded-box border border-border bg-surface p-4">
								<div className="flex items-start justify-between gap-2">
									<span className="flex min-w-0 items-start gap-2">
										<span className="text-2xl" aria-hidden>{KIND_ICON[program.kind ?? ""] ?? "📝"}</span>
										<span className="flex min-w-0 flex-col">
											<span className="font-semibold">{program.title}</span>
											<span className="text-xs text-muted">{program.type_title}</span>
										</span>
									</span>
									<span className="flex shrink-0 flex-col items-end gap-1">
										{daysSince(program.iso) <= FRESH_DAYS ? <StatusChip size="sm" tone="success" label={p.freshMark} /> : null}
										<span className="text-xs text-muted tabular-nums">{program.date}</span>
									</span>
								</div>
								{program.note ? <p className="whitespace-pre-line text-sm text-muted">{program.note}</p> : null}
								{program.has_file ? <SendButton send={() => sendProgram(program.id)} /> : null}
							</li>
						))}
					</ul>
				</section>
			) : null}
		</div>
	);
}
