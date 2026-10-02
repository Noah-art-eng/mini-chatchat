import { afterEach, describe, expect, it, vi } from "vitest";
import { uploadDocument } from "./kb";

describe("knowledge base upload API", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("includes the explicit target knowledge base in multipart data", async () => {
    const fetchMock = vi.fn(async (_url: string, init?: RequestInit) => {
      const formData = init?.body as FormData;
      expect(formData.get("kb_name")).toBe("个人简历");
      expect((formData.get("file") as File).name).toBe("resume.txt");
      return new Response(JSON.stringify({ message: "uploaded" }), {
        status: 200,
        headers: { "Content-Type": "application/json" }
      });
    });
    vi.stubGlobal("fetch", fetchMock);

    await uploadDocument(
      new File(["resume"], "resume.txt", { type: "text/plain" }),
      "个人简历"
    );

    expect(fetchMock).toHaveBeenCalledOnce();
  });
});
