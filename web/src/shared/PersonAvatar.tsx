import { useState } from "react";
import { TINT, tintStyle } from "@/shared/personColor";

/** A person's photo, or their initial on their own colour when there is none (or it fails to load). */
export function PersonAvatar({ id, name, src, size = 40 }: { id: number; name: string; src?: string | null; size?: number }) {
	const [failed, setFailed] = useState(false);
	const box = { width: size, height: size };
	if (src && !failed) return <img src={src} alt="" aria-hidden onError={() => setFailed(true)} style={box} className="shrink-0 rounded-full object-cover" />;
	return (
		<span aria-hidden style={{ ...tintStyle(id), ...box, fontSize: size * 0.42 }} className={`flex shrink-0 items-center justify-center rounded-full font-bold ${TINT}`}>
			{name.trim().charAt(0)}
		</span>
	);
}
