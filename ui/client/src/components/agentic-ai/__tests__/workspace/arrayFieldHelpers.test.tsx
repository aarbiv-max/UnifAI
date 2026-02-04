import { describe, it, expect } from "vitest";
import {
  resolvePath,
  getItemLabel,
  getArrayDisplayText,
  getArrayFieldMode,
  getValidRefOptions,
} from "../../workspace/arrayFieldHelpers";

describe("arrayFieldHelpers", () => {
  describe("resolvePath", () => {
    it("resolves dot-notation paths (a.b.c)", () => {
      const obj = {
        a: {
          b: {
            c: "value",
          },
        },
      };

      expect(resolvePath(obj, "a.b.c")).toBe("value");
    });

    it("returns undefined for non-existent paths", () => {
      const obj = { a: { b: 1 } };
      expect(resolvePath(obj, "a.b.c")).toBeUndefined();
    });

    it("handles single-level paths", () => {
      const obj = { name: "test" };
      expect(resolvePath(obj, "name")).toBe("test");
    });

    it("returns undefined for null object", () => {
      expect(resolvePath(null, "a.b")).toBeUndefined();
    });

    it("returns undefined for undefined object", () => {
      expect(resolvePath(undefined, "a")).toBeUndefined();
    });

    it("handles array indices in path", () => {
      const obj = {
        items: [{ name: "first" }, { name: "second" }],
      };
      expect(resolvePath(obj, "items.0.name")).toBe("first");
      expect(resolvePath(obj, "items.1.name")).toBe("second");
    });
  });

  describe("getItemLabel", () => {
    it("returns label from item using displayFieldPath", () => {
      const item = {
        metadata: {
          name: "Item Name",
        },
      };

      expect(getItemLabel(item, "metadata.name")).toBe("Item Name");
    });

    it("returns string value directly if item is string", () => {
      expect(getItemLabel("simple-string", "any.path")).toBe("simple-string");
    });

    it("returns JSON string for objects without displayFieldPath", () => {
      const item = { id: 1, value: "test" };
      expect(getItemLabel(item, undefined)).toBe(JSON.stringify(item));
    });

    it("returns empty string for null/undefined items", () => {
      expect(getItemLabel(null, "name")).toBe("");
      expect(getItemLabel(undefined, "name")).toBe("");
    });
  });

  describe("getArrayDisplayText", () => {
    it("returns comma-separated labels for array", () => {
      const items = [{ name: "A" }, { name: "B" }, { name: "C" }];
      expect(getArrayDisplayText(items, "name")).toBe("A, B, C");
    });

    it("handles empty array", () => {
      expect(getArrayDisplayText([], "name")).toBe("");
    });

    it("handles array of strings", () => {
      const items = ["one", "two", "three"];
      expect(getArrayDisplayText(items, "name")).toBe("one, two, three");
    });

    it("handles mixed content", () => {
      const items = [{ label: "Item 1" }, { label: "Item 2" }];
      expect(getArrayDisplayText(items, "label")).toBe("Item 1, Item 2");
    });
  });

  describe("getArrayFieldMode", () => {
    // The function signature is: getArrayFieldMode(isArrayWithRefItems, hasDynamicHint, isDirectArrayType)
    
    it("returns 'refItems' when isArrayWithRefItems is true", () => {
      expect(getArrayFieldMode(true, false, false)).toBe("refItems");
    });

    it("returns 'dynamic' when hasDynamicHint is true (and not refItems)", () => {
      expect(getArrayFieldMode(false, true, false)).toBe("dynamic");
    });

    it("returns 'regular' when isDirectArrayType is true (and not refItems or dynamic)", () => {
      expect(getArrayFieldMode(false, false, true)).toBe("regular");
    });

    it("returns null when all flags are false", () => {
      expect(getArrayFieldMode(false, false, false)).toBeNull();
    });

    it("refItems takes precedence over dynamic", () => {
      expect(getArrayFieldMode(true, true, false)).toBe("refItems");
    });

    it("refItems takes precedence over regular", () => {
      expect(getArrayFieldMode(true, false, true)).toBe("refItems");
    });

    it("dynamic takes precedence over regular", () => {
      expect(getArrayFieldMode(false, true, true)).toBe("dynamic");
    });
  });

  describe("getValidRefOptions", () => {
    // The function signature is: getValidRefOptions(refOptions, category)
    
    it("filters options with valid non-empty rids from category", () => {
      const refOptions = {
        resources: [
          { rid: "valid-1", name: "Option 1" },
          { rid: "", name: "Empty RID" },
          { rid: "valid-2", name: "Option 2" },
        ],
      };

      const result = getValidRefOptions(refOptions, "resources");

      expect(result).toHaveLength(2);
      expect(result[0].rid).toBe("valid-1");
      expect(result[1].rid).toBe("valid-2");
    });

    it("returns empty array when category is null", () => {
      const refOptions = {
        resources: [{ rid: "valid-1", name: "Option 1" }],
      };
      expect(getValidRefOptions(refOptions, null)).toEqual([]);
    });

    it("returns empty array when category does not exist", () => {
      const refOptions = {
        resources: [{ rid: "valid-1", name: "Option 1" }],
      };
      expect(getValidRefOptions(refOptions, "nonexistent")).toEqual([]);
    });

    it("handles array with all invalid options", () => {
      const refOptions = {
        items: [
          { rid: "", name: "A" },
          { rid: "   ", name: "B" },
        ],
      };

      expect(getValidRefOptions(refOptions, "items")).toEqual([]);
    });

    it("preserves all properties of valid options", () => {
      const refOptions = {
        items: [
          { rid: "valid-1", name: "Option", extra: "data", nested: { value: 1 } },
        ],
      };

      const result = getValidRefOptions(refOptions, "items");

      expect(result[0]).toEqual({
        rid: "valid-1",
        name: "Option",
        extra: "data",
        nested: { value: 1 },
      });
    });

    it("returns empty array for empty refOptions", () => {
      expect(getValidRefOptions({}, "resources")).toEqual([]);
    });
  });
});
