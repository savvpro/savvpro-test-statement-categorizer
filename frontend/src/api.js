const BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

async function handle(res) {
  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    try {
      const body = await res.json();
      if (typeof body.detail === "string") detail = body.detail;
    } catch {
      /* keep the default message */
    }
    throw new Error(detail);
  }
  return res.json();
}

export async function getCategories() {
  return handle(await fetch(`${BASE}/api/categories`));
}

export async function categorize(file, chargesPositive, userRules) {
  const form = new FormData();
  form.append("file", file);
  form.append("charges_positive", String(chargesPositive));
  form.append("user_rules", JSON.stringify(userRules));
  return handle(await fetch(`${BASE}/api/categorize`, { method: "POST", body: form }));
}