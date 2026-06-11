import { cn, clamp, formatNumber, unitLabel, assertDefined } from "@/lib/utils";

describe("cn", () => {
  it("merges class strings", () => {
    expect(cn("a", "b")).toBe("a b");
  });

  it("resolves Tailwind conflicts", () => {
    // twMerge: later px wins over earlier
    expect(cn("px-2", "px-4")).toBe("px-4");
  });

  it("filters falsy values", () => {
    expect(cn("a", false && "b", undefined, "c")).toBe("a c");
  });
});

describe("formatNumber", () => {
  it("removes trailing zeros", () => {
    expect(formatNumber(1.5)).toBe("1.5");
    expect(formatNumber(1.0)).toBe("1");
    expect(formatNumber(1.50)).toBe("1.5");
  });

  it("respects maxDecimals", () => {
    expect(formatNumber(1.234, 2)).toBe("1.23");
    expect(formatNumber(1.0, 2)).toBe("1");
  });
});

describe("clamp", () => {
  it("returns value when within range", () => {
    expect(clamp(5, 1, 10)).toBe(5);
  });

  it("clamps to min", () => {
    expect(clamp(0, 1, 10)).toBe(1);
  });

  it("clamps to max", () => {
    expect(clamp(15, 1, 10)).toBe(10);
  });
});

describe("unitLabel", () => {
  it("returns known unit labels", () => {
    expect(unitLabel("kg")).toBe("kg");
    expect(unitLabel("lbs")).toBe("lb");
    expect(unitLabel("fl_oz")).toBe("fl oz");
  });

  it("returns unknown units as-is", () => {
    expect(unitLabel("xyz")).toBe("xyz");
  });
});

describe("assertDefined", () => {
  it("returns the value when defined", () => {
    expect(assertDefined(42)).toBe(42);
    expect(assertDefined("hello")).toBe("hello");
  });

  it("throws on null", () => {
    expect(() => assertDefined(null)).toThrow();
  });

  it("throws on undefined", () => {
    expect(() => assertDefined(undefined)).toThrow();
  });

  it("throws with a custom message", () => {
    expect(() => assertDefined(null, "user required")).toThrow("user required");
  });
});
