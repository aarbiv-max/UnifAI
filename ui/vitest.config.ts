import { defineConfig, mergeConfig } from "vitest/config";
import { webcrypto } from "node:crypto";
import path from "path";
import viteConfig from "./vite.config";

if (!globalThis.crypto) {
  globalThis.crypto = webcrypto as Crypto;
}

export default mergeConfig(
  viteConfig,
  defineConfig({
    test: {
      environment: "happy-dom",
      globals: true,
      setupFiles: [path.resolve(import.meta.dirname, "vitest.setup.ts")],
      include: ["src/**/*.test.{ts,tsx}"],
      css: true,
    },
  }),
);

