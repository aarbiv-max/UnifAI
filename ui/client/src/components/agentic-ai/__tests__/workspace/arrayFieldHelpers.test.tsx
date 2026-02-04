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
    it("returns 'refItems' for array fields with $ref items", () => {
      const fieldSchema = {
        type: "array",
        items: {
          $ref: "#/definitions/ResourceRef",
        },
      };

      expect(getArrayFieldMode(fieldSchema)).toBe("refItems");
    });

    it("returns 'dynamic' for arrays with populateHint", () => {
      const fieldSchema = {
        type: "array",
        items: { type: "string" },
      };
      const hints = { populate: { endpoint: "/api/fetch" } };

      expect(getArrayFieldMode(fieldSchema, hints)).toBe("dynamic");
    });

    it("returns 'regular' for plain string arrays", () => {
      const fieldSchema = {
        type: "array",
        items: { type: "string" },
      };

      expect(getArrayFieldMode(fieldSchema)).toBe("regular");
    });

    it("returns null when array mode cannot be determined", () => {
      const fieldSchema = {
        type: "object", // Not an array
      };

      expect(getArrayFieldMode(fieldSchema)).toBeNull();
    });

    it("handles nested $ref in items", () => {
      const fieldSchema = {
        type: "array",
        items: {
          anyOf: [{ $ref: "#/definitions/Type1" }, { $ref: "#/definitions/Type2" }],
        },
      };

      expect(getArrayFieldMode(fieldSchema)).toBe("refItems");
    });
  });

  describe("getValidRefOptions", () => {
    it("filters options with valid non-empty rids", () => {
      const options = [
        { rid: "valid-1", name: "Option 1" },
        { rid: "", name: "Empty RID" },
        { rid: "valid-2", name: "Option 2" },
        { rid: null, name: "Null RID" },
      ];

      const result = getValidRefOptions(options);

      expect(result).toHaveLength(2);
      expect(result[0].rid).toBe("valid-1");
      expect(result[1].rid).toBe("valid-2");
    });

    it("returns empty array for null input", () => {
      expect(getValidRefOptions(null as any)).toEqual([]);
    });

    it("returns empty array for undefined input", () => {
      expect(getValidRefOptions(undefined as any)).toEqual([]);
    });

    it("handles array with all invalid options", () => {
      const options = [
        { rid: "", name: "A" },
        { rid: null, name: "B" },
        { rid: undefined, name: "C" },
      ];

      expect(getValidRefOptions(options)).toEqual([]);
    });

    it("preserves all properties of valid options", () => {
      const options = [
        { rid: "valid-1", name: "Option", extra: "data", nested: { value: 1 } },
      ];

      const result = getValidRefOptions(options);

      expect(result[0]).toEqual({
        rid: "valid-1",
        name: "Option",
        extra: "data",
        nested: { value: 1 },
      });
    });
  });
});
