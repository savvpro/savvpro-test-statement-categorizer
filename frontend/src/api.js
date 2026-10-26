// All calls to the Python backend live here.
async function request(url, options) {
  const response = await fetch(url, options);
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.detail || "Something went wrong. Try again.");
  return body;
}

export function uploadStatement(file, chargesArePositive) {
  const form = new FormData();
  form.append("file", file);
  form.append("charges_are_positive", String(chargesArePositive));
  return request("/api/statements", { method: "POST", body: form });
}

export function fetchCategories() {
  return request("/api/categories").then((b) => b.categories);
}

export function fetchSummary(rows) {
  const slim = rows.map(({ id, amount, category, refund_of }) => ({ id, amount, category, refund_of }));
  return request("/api/summary", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ rows: slim }),
  });
}
