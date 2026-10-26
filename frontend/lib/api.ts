const API = "http://localhost:8000";

export type Row = {
  id: string; date: string; description: string; amount: string;
  category: string; confidence: number; reason: string;
};

export async function uploadStatement(file: File): Promise<Row[]> {
  const fd = new FormData();
  fd.append("file", file);
  const r = await fetch(`${API}/upload`, { method: "POST", body: fd });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function updateCategory(id: string, category: string): Promise<Row> {
  const r = await fetch(`${API}/rows/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ category }),
  });
  return r.json();
}