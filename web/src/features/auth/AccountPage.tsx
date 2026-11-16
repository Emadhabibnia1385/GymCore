import { useSuspenseQuery } from "@tanstack/react-query";
import { KeyValueList, PageHeader, SectionCard } from "@nyxon/nasim";
import { t } from "@/strings";
import { meQuery } from "./api";
import { ChangePasswordForm, CreatePasswordForm } from "./forms";

const a = t.account;

export function AccountPage() {
	const { data: me } = useSuspenseQuery(meQuery);
	return (
		<div className="flex flex-col gap-6">
			<PageHeader title={a.title} description={me.name} />
			{me.username ? (
				<>
					<SectionCard title={a.username}>
						<KeyValueList items={[{ label: a.username, value: me.username, ltr: true }]} />
					</SectionCard>
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
