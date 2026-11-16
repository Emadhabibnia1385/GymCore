import { useQueryClient, useSuspenseQuery } from "@tanstack/react-query";
import { KeyValueList, PageHeader, SectionCard } from "@nyxon/nasim";
import { AvatarEditor } from "@/features/avatar";
import { t } from "@/strings";
import { meQuery } from "./api";
import { ChangePasswordForm, CreatePasswordForm } from "./forms";
import { TelegramLinkCard } from "./TelegramLinkCard";

const a = t.account;

export function AccountPage() {
	const { data: me } = useSuspenseQuery(meQuery);
	const queryClient = useQueryClient();
	return (
		<div className="flex flex-col gap-6">
			<PageHeader title={a.title} description={me.name} />
			<SectionCard title={t.avatar.title}>
				<AvatarEditor base="/api/me/avatar" version={me.avatar ?? 0} id={0} name={me.name} onChange={() => void queryClient.invalidateQueries({ queryKey: meQuery.queryKey })} />
			</SectionCard>
			{me.username ? (
				<>
					<SectionCard title={a.username}>
						<KeyValueList items={[{ label: a.username, value: me.username, ltr: true }]} />
					</SectionCard>
					<TelegramLinkCard />
					<SectionCard title={a.changeTitle}>
						<ChangePasswordForm />
					</SectionCard>
				</>
			) : (
				<SectionCard title={a.createTitle} description={`${a.noPassword} ${a.createHint}`}>
					<CreatePasswordForm />
				</SectionCard>
			)}
		</div>
	);
}
