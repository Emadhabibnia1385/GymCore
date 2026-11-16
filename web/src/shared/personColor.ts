/** Each person keeps one hue wherever they appear, so a glance at a grid tells who is who. */
const hue = (id: number) => (id * 47 + 20) % 360;

/** Tailwind sees these class names whole, so they are spelled out; only the hue varies. */
export const TINT =
	"border border-[oklch(0.62_0.13_var(--h))] bg-[oklch(0.93_0.07_var(--h))] text-[oklch(0.28_0.09_var(--h))] dark:bg-[oklch(0.3_0.08_var(--h))] dark:text-[oklch(0.93_0.07_var(--h))]";

export const tintStyle = (id: number) => ({ "--h": hue(id) }) as React.CSSProperties;
