import { http, HttpResponse } from "msw";

export const api3Handlers = [
  http.get("/api3/auth/user", () =>
    HttpResponse.json({ authenticated: false, user: null }),
  ),
  http.post("/api3/auth/logout", () => HttpResponse.json({ status: "ok" })),
  http.post("/api3/auth/refresh", () => HttpResponse.json({ status: "ok" })),
  http.all("/api3/:path*", () => HttpResponse.json({})),
];

