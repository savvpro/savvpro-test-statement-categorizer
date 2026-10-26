const BASE = "/api/v1";

async function request(path: string, init: RequestInit): Promise<unknown> {
  const res = await fetch(`${BASE}${path}`, init);
  if (!res.ok) {
    let msg = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      if (body?.error?.message) msg = body.error.message;
    } catch {}
    throw new Error(msg);
  }
  if (res.status === 204) return null;
  return res.json();
}

export const api = {
  get(path: string, params?: Record<string, string | number | boolean | undefined>): Promise<unknown> {
    const url = params
      ? `${path}?${new URLSearchParams(
          Object.fromEntries(
            Object.entries(params)
              .filter(([, v]) => v !== undefined)
              .map(([k, v]) => [k, String(v)])
          )
        )}`
      : path;
    return request(url, { method: "GET" });
  },
  post(path: string, body?: unknown): Promise<unknown> {
    return request(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  },
  patch(path: string, body?: unknown): Promise<unknown> {
    return request(path, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  },
  del(path: string): Promise<unknown> {
    return request(path, { method: "DELETE" });
  },
  postForm(path: string, formData: FormData): Promise<unknown> {
    return request(path, { method: "POST", body: formData });
  },
};
