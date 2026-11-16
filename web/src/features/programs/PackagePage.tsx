import { useQuery } from "@tanstack/react-query";
import { ErrorState, PageHeader, PageSkeleton, SectionCard, StatusChip } from "@nyxon/nasim";
import { t } from "@/strings";
import { packageQuery, sendPackageItem } from "./api";
import { SendButton } from "./SendButton";

const p = t.programs;

export function PackagePage({ id }: { id: number }) {
	const { data, isPending, isError, refetch } = useQuery(packageQuery(id));
	if (isPending) return <PageSkeleton />;
	if (isError) return <ErrorState as="h1" onRetry={() => void refetch()} />;
	return (
		<div className="flex flex-col gap-6">
			<PageHeader title={data.title} description={data.description ?? undefined} backHref="/programs" />
			<ul className="flex flex-col gap-3">
				{data.item_list.map((item) => (
					<li key={item.id}>
						<SectionCard title={item.title} level={3} actions={<StatusChip size="sm" tone="neutral" label={p.itemKind[item.kind as keyof typeof p.itemKind] ?? p.itemKind.document} />}>
							<div className="flex flex-col gap-3">
								{item.text ? <p className="whitespace-pre-line text-sm">{item.text}</p> : null}
								{item.kind === "text" ? null : item.on_telegram ? (
									<SendButton send={() => sendPackageItem(data.id, item.id)} />
								) : (
									<p className="text-sm text-muted">{p.fileOnTelegramOnly}</p>
								)}
							</div>
						</SectionCard>
					</li>
				))}
			</ul>
		</div>
	);
}
