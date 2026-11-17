import { useQuery } from "@tanstack/react-query";
import { ErrorState, PageHeader, PageSkeleton, StatusChip } from "@nyxon/nasim";
import { formatNumber } from "@/shared/format";
import { fill, t } from "@/strings";
import { packageQuery, sendPackageItem } from "./api";
import { SendButton } from "./SendButton";

const p = t.programs;
const ICON: Record<string, string> = { video: "🎬", photo: "🖼", document: "📄", text: "📝" };

export function PackagePage({ id }: { id: number }) {
	const { data, isPending, isError, refetch } = useQuery(packageQuery(id));
	if (isPending) return <PageSkeleton />;
	if (isError) return <ErrorState as="h1" onRetry={() => void refetch()} />;
	return (
		<div className="flex flex-col gap-6">
			<PageHeader title={data.title} description={data.description ?? undefined} backHref="/programs" meta={<StatusChip size="sm" tone="info" label={fill(p.items, { n: formatNumber(data.item_list.length) })} />} />
			<ol className="grid grid-cols-1 gap-3 lg:grid-cols-2">
				{data.item_list.map((item, index) => (
					<li key={item.id} className="flex flex-col gap-3 rounded-box border border-border bg-surface p-4">
						<div className="flex items-start justify-between gap-2">
							<span className="flex min-w-0 items-start gap-3">
								<span className="flex size-9 shrink-0 items-center justify-center rounded-full bg-accent/15 text-sm font-bold text-accent tabular-nums">{formatNumber(index + 1)}</span>
								<span className="flex min-w-0 flex-col">
									<span className="font-semibold">{item.title}</span>
									<span className="text-xs text-muted">{ICON[item.kind] ?? ICON.document} {p.itemKind[item.kind as keyof typeof p.itemKind] ?? p.itemKind.document}</span>
								</span>
							</span>
						</div>
						{item.text ? <p className="whitespace-pre-line text-sm">{item.text}</p> : null}
						{item.kind === "text" ? null : item.on_telegram ? (
							<SendButton send={() => sendPackageItem(data.id, item.id)} />
						) : (
							<p className="text-sm text-muted">{p.fileOnTelegramOnly}</p>
						)}
					</li>
				))}
			</ol>
		</div>
	);
}
