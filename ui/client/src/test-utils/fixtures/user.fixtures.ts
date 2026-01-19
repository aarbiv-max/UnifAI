import { User } from "@/contexts/AuthContext";

export const buildUser = (overrides: Partial<User> = {}): User => ({
  username: "test-user",
  email: "test@example.com",
  name: "Test User",
  sub: "user-1",
  token_expires_at: Math.floor(Date.now() / 1000) + 3600,
  ...overrides,
});

