import { http, HttpResponse } from "msw";

export const api2Handlers = [
  http.get("/api2/catalog/elements.list.get", () =>
    HttpResponse.json({ elements: {} }),
  ),
  http.get("/api2/resources/resources.list", () =>
    HttpResponse.json({ resources: [] }),
  ),
  http.get("/api2/shares/shares.list", () =>
    HttpResponse.json({ invites: [], count: 0 }),
  ),
  http.post("/api2/shares/share.create", () =>
    HttpResponse.json({ status: "ok", share_id: "share-1" }),
  ),
  http.post("/api2/shares/share.accept", () =>
    HttpResponse.json({
      status: "ok",
      result: {
        share_id: "share-1",
        new_item_id: "item-1",
        rid_mapping: {},
        created_resources: 0,
        name_conflicts: {},
      },
    }),
  ),
  http.post("/api2/shares/share.decline", () =>
    HttpResponse.json({ status: "ok" }),
  ),
  http.all("/api2/:path*", () => HttpResponse.json({})),
];

