const BASE = import.meta.env.VITE_API_BASE || "/api";

async function request(path, options = {}) {
  const response = await fetch(`${BASE}${path}`, options);
  if (response.status === 204) return null;
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = Array.isArray(data.detail) ? data.detail.map((d) => d.msg).join(", ") : data.detail;
    throw new Error(detail || `Request failed (${response.status})`);
  }
  return data;
}

const json = (method, body) => ({ method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });

export const api = {
  categories: () => request("/categories"),
  categorize: (file) => {
    const body = new FormData();
    body.append("file", file);
    return request("/categorize", { method: "POST", body });
  },
  taxEstimate: (transactions) =>
    request("/tax-estimate", json("POST", { transactions: transactions.map(({ category, amount }) => ({ category, amount })) })),
  rules: () => request("/rules"),
  saveRule: (merchant, category) => request("/rules", json("PUT", { merchant, category })),
  deleteRule: (merchant) => request(`/rules/${encodeURIComponent(merchant)}`, { method: "DELETE" }),
};
