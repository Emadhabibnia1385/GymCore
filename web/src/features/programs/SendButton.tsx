import { useMutation } from "@tanstack/react-query";
import { Button, Notice } from "@nyxon/nasim";
import { t } from "@/strings";
import type { Done } from "./api";

/** «Send to my Telegram»: the bot delivers the file to the student's chat. */
export function SendButton({ send }: { send: () => Promise<Done> }) {
	const mutation = useMutation({ mutationFn: send });
	return (
		<div className="flex flex-col gap-2">
			<Button size="sm" variant="secondary" isPending={mutation.isPending} onPress={() => mutation.mutate()}>
				{t.programs.sendToTelegram}
			</Button>
			{mutation.isSuccess ? <Notice tone="success" role="status">{mutation.data.message}</Notice> : null}
			{mutation.isError ? <Notice tone="danger" role="alert">{mutation.error.message}</Notice> : null}
		</div>
	);
}
