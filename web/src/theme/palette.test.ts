import { checkPalette } from "@nyxon/nasim/palette";
import { expect, it } from "vitest";
import { palette } from "./palette";

it("keeps every contrast the design system requires", () => {
	expect(checkPalette(palette)).toEqual([]);
});
