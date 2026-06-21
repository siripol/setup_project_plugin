import { describe, it, expect } from "vitest";
import { runSession } from "../src/client.js";

describe("runSession", () => {
  it("throws without ANTHROPIC_API_KEY", async () => {
    const old = process.env.ANTHROPIC_API_KEY;
    delete process.env.ANTHROPIC_API_KEY;
    await expect(runSession("agent-stub")).rejects.toThrow(/ANTHROPIC_API_KEY/);
    if (old !== undefined) process.env.ANTHROPIC_API_KEY = old;
  });
});
