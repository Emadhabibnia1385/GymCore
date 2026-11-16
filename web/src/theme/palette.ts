import type { Palette } from "@nyxon/nasim";

// The Sarmad brand: a black page with a lime accent (#B2F828), as on his website.
// Dark is the brand's own look and the default. Lime on white can't hold the contrast a
// button needs, so the light scheme keeps the same hue but darker; Nasim measures every
// pair (palette.test.ts), so a colour that stops being readable fails the build.
export const palette: Palette = {
	radius: "0.875rem",
	dark: {
		background: "#000000",
		foreground: "#ffffff",
		surface: "#0b0b0b",
		surfaceSecondary: "#151515",
		surfaceTertiary: "#202020",
		overlay: "#111111",
		muted: "#a8a8a8",
		border: "#262626",
		fieldBorder: "#707070",
		accent: { fill: "#b2f828", onFill: "#000000" },
		success: { fill: "#4ade80", onFill: "#000000" },
		warning: { fill: "#fbbf24", onFill: "#000000" },
		danger: { fill: "#ff6b6b", onFill: "#000000" },
		info: { fill: "#60a5fa", onFill: "#000000" },
	},
	light: {
		background: "#f6f8ef",
		foreground: "#0a0a0a",
		surface: "#ffffff",
		surfaceSecondary: "#eef2e0",
		surfaceTertiary: "#e3e9cf",
		overlay: "#ffffff",
		muted: "#566049",
		border: "#d6dcc3",
		fieldBorder: "#757d63",
		accent: { fill: "#3d6600", onFill: "#ffffff" },
		success: { fill: "#0a6a33", onFill: "#ffffff" },
		warning: { fill: "#8a5a00", onFill: "#ffffff" },
		danger: { fill: "#b42338", onFill: "#ffffff" },
		info: { fill: "#1f56a8", onFill: "#ffffff" },
	},
};
