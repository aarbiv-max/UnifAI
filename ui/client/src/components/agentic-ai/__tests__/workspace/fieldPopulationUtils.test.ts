import { describe, it, expect } from "vitest";
import { normalizeOptions, OptionItem } from "../../workspace/fieldPopulationUtils";

describe("fieldPopulationUtils", () => {
  describe("normalizeOptions", () => {
    it("converts raw API results to OptionItem[]", () => {
      const items = ["item1", "item2"];
      const result = normalizeOptions(items);

      expect(result).toHaveLength(2);
      expect(result[0]).toEqual({
        label: "item1",
        value: "item1",
        originalObject: "item1",
      });
    });

    it("handles string arrays (value = label = item)", () => {
      const items = ["Option A", "Option B", "Option C"];
      const result = normalizeOptions(items);

      expect(result).toEqual([
        { label: "Option A", value: "Option A", originalObject: "Option A" },
        { label: "Option B", value: "Option B", originalObject: "Option B" },
        { label: "Option C", value: "Option C", originalObject: "Option C" },
      ]);
    });

    it("handles object arrays (uses displayField/valueField)", () => {
      const items = [
        { id: "id-1", name: "First Item" },
        { id: "id-2", name: "Second Item" },
      ];
      const result = normalizeOptions(items, "name", "id");

      expect(result).toEqual([
        { label: "First Item", value: "id-1", originalObject: items[0] },
        { label: "Second Item", value: "id-2", originalObject: items[1] },
      ]);
    });

    it("handles nested displayField paths", () => {
      const items = [
        { meta: { title: "Title A" }, uid: "uid-1" },
        { meta: { title: "Title B" }, uid: "uid-2" },
      ];
      const result = normalizeOptions(items, "meta.title", "uid");

      expect(result).toEqual([
        { label: "Title A", value: "uid-1", originalObject: items[0] },
        { label: "Title B", value: "uid-2", originalObject: items[1] },
      ]);
    });

    it("handles nested valueField paths", () => {
      const items = [
        { name: "Item 1", identifiers: { primary: "p1" } },
        { name: "Item 2", identifiers: { primary: "p2" } },
      ];
      const result = normalizeOptions(items, "name", "identifiers.primary");

      expect(result).toEqual([
        { label: "Item 1", value: "p1", originalObject: items[0] },
        { label: "Item 2", value: "p2", originalObject: items[1] },
      ]);
    });

    it("falls back to JSON.stringify when fields not configured", () => {
      const items = [
        { complex: "object", nested: { value: 1 } },
      ];
      const result = normalizeOptions(items);

      // Without displayField or valueField, should stringify
      expect(result[0].label).toBe(JSON.stringify(items[0]));
      expect(result[0].value).toBe(JSON.stringify(items[0]));
    });

    it("returns empty array for null input", () => {
      const result = normalizeOptions(null as any);
      expect(result).toEqual([]);
    });

    it("returns empty array for undefined input", () => {
      const result = normalizeOptions(undefined as any);
      expect(result).toEqual([]);
    });

    it("returns empty array for non-array input", () => {
      const result = normalizeOptions("not an array" as any);
      expect(result).toEqual([]);
    });

    it("returns empty array for empty array input", () => {
      const result = normalizeOptions([]);
      expect(result).toEqual([]);
    });

    it("preserves originalObject for all item types", () => {
      const stringItem = "string-item";
      const objectItem = { id: 1, name: "Object" };

      const result = normalizeOptions([stringItem, objectItem], "name", "id");

      expect(result[0].originalObject).toBe(stringItem);
      expect(result[1].originalObject).toBe(objectItem);
    });

    it("handles mixed content (strings and objects)", () => {
      const items = [
        "simple-string",
        { id: "obj-1", label: "Object Item" },
      ];
      const result = normalizeOptions(items, "label", "id");

      expect(result[0]).toEqual({
        label: "simple-string",
        value: "simple-string",
        originalObject: "simple-string",
      });
      expect(result[1]).toEqual({
        label: "Object Item",
        value: "obj-1",
        originalObject: items[1],
      });
    });

    it("handles number values (converts to string)", () => {
      const items = [1, 2, 3];
      const result = normalizeOptions(items as any);

      expect(result).toEqual([
        { label: "1", value: "1", originalObject: 1 },
        { label: "2", value: "2", originalObject: 2 },
        { label: "3", value: "3", originalObject: 3 },
      ]);
    });

    it("handles objects with null displayField value", () => {
      const items = [{ id: "1", name: null }];
      const result = normalizeOptions(items, "name", "id");

      // Should fall back to JSON.stringify for label since name is null
      expect(result[0].label).toBe(JSON.stringify(items[0]));
      expect(result[0].value).toBe("1");
    });

    it("handles objects with undefined displayField value", () => {
      const items = [{ id: "1" }]; // name is undefined
      const result = normalizeOptions(items, "name", "id");

      // Should fall back to JSON.stringify for label since name is undefined
      expect(result[0].label).toBe(JSON.stringify(items[0]));
      expect(result[0].value).toBe("1");
    });

    it("handles deeply nested paths", () => {
      const items = [
        {
          metadata: {
            display: {
              primary: "Deep Label",
            },
          },
          ids: {
            external: {
              value: "deep-id",
            },
          },
        },
      ];
      const result = normalizeOptions(items, "metadata.display.primary", "ids.external.value");

      expect(result[0]).toEqual({
        label: "Deep Label",
        value: "deep-id",
        originalObject: items[0],
      });
    });

    it("handles array indices in field paths", () => {
      const items = [
        {
          names: ["First", "Second"],
          id: "test-1",
        },
      ];
      const result = normalizeOptions(items, "names.0", "id");

      expect(result[0].label).toBe("First");
      expect(result[0].value).toBe("test-1");
    });

    it("converts boolean values to strings", () => {
      const items = [
        { enabled: true, id: "item-true" },
        { enabled: false, id: "item-false" },
      ];
      const result = normalizeOptions(items, "enabled", "id");

      expect(result[0].label).toBe("true");
      expect(result[1].label).toBe("false");
    });

    it("handles zero as a valid value", () => {
      const items = [
        { count: 0, id: "zero" },
        { count: 5, id: "five" },
      ];
      const result = normalizeOptions(items, "count", "id");

      expect(result[0].label).toBe("0");
      expect(result[0].value).toBe("zero");
      expect(result[1].label).toBe("5");
    });

    it("handles empty string as valid value", () => {
      const items = [
        { name: "", id: "empty" },
      ];
      const result = normalizeOptions(items, "name", "id");

      // Empty string should be returned as-is (not fall back to stringify)
      // Actually checking the implementation - resolvePath returns empty string which is truthy for the check
      expect(result[0].label).toBe("");
      expect(result[0].value).toBe("empty");
    });

    it("handles objects in array items", () => {
      const items = [{ nested: { a: 1 } }];
      const result = normalizeOptions(items, "nested", "nested");

      // nested is an object - resolvePath returns the object which gets String() converted
      // String({a:1}) returns "[object Object]" not JSON.stringify
      expect(result[0].label).toBe("[object Object]");
    });
  });
});
