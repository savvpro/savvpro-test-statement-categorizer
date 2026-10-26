const API = import.meta.env.VITE_API_URL || "http://localhost:8000";

async function handle(res) {
  if (!res.ok) {
    let detail = "Request failed";
    try {
      detail = (await res.json()).detail || detail;
    }  catch { /* response had no JSON body */ }
    throw new Error(detail);
  }
  return res.json();
}

export async function uploadStatement(file) {
  const form = new FormData();
  form.append("file", file);
  return handle(await fetch(`${API}/upload`, { method: "POST", body: form }));
}

export async function getCategories() {
  return handle(await fetch(`${API}/categories`));
}

export async function updateCategory(id, category) {
  return handle(
    await fetch(`${API}/transactions/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ category }),
    })
  );
}