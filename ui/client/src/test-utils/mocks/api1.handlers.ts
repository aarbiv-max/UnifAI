import { http, HttpResponse } from "msw";

export const api1Handlers = [
  http.get("/api1/settings/get.umami.settings", () =>
    HttpResponse.json({ website_id: null, umami_url: null }),
  ),
  http.all("/api1/:path*", () => HttpResponse.json({})),
];

