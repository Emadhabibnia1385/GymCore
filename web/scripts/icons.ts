// Renders public/favicon.svg into the PNG icons the install prompt needs. Run: bun run icons
import sharp from "sharp";

const source = "public/favicon.svg";
const sizes: [string, number, number][] = [
	["icon-180", 180, 0],
	["icon-192", 192, 0],
	["icon-512", 512, 0],
	// A maskable icon keeps its art inside the middle 80%, so a round crop never cuts it.
	["icon-maskable-512", 512, 0.12],
];

for (const [name, size, padding] of sizes) {
	const art = Math.round(size * (1 - padding * 2));
	const icon = await sharp(source).resize(art, art).png().toBuffer();
	await sharp({ create: { width: size, height: size, channels: 4, background: "#0a0e12" } })
		.composite([{ input: icon, gravity: "centre" }])
		.png()
		.toFile(`public/icons/${name}.png`);
}
console.log("icons written");
