import { describe, expect, it } from "vitest";
import { fill } from "@/strings";
import { yTicks } from "./chart";

describe("yTicks", () => {
	it("draws three even steps from zero just above the largest value", () => {
		const ticks = yTicks(4_200_000);
		expect(ticks.map((tick) => tick.value)).toEqual([0, 2_000_000, 4_000_000, 6_000_000]);
	});

	it("still draws a baseline when there is no money yet", () => {
		expect(yTicks(0)[0].value).toBe(0);
		expect(yTicks(0).length).toBe(4);
	});
});

describe("fill", () => {
	it("puts values into the named slots", () => {
		expect(fill("سلام {name}", { name: "سارا" })).toBe("سلام سارا");
	});
});
