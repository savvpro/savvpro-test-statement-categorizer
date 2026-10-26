async function readError(response) {
  try {
    const body = await response.json();
    if (typeof body.detail === "string") return body.detail;
  } catch {
    /* The body was not JSON. */
  }
  return `The server returned ${response.status}.`;
}

export async function getCategories() {
  const response = await fetch("/api/categories");
  if (!response.ok) throw new Error(await readError(response));
  return response.json();
}

export async function uploadStatement(file, accountType) {
  const form = new FormData();
  form.set("file", file);
  form.set("account_type", accountType);
  const response = await fetch("/api/statements", { method: "POST", body: form });
  if (!response.ok) throw new Error(await readError(response));
  return response.json();
}

export async function loadSample() {
  const response = await fetch("/api/statements/sample?account_type=credit_card", { method: "POST" });
  if (!response.ok) throw new Error(await readError(response));
  return response.json();
}

export async function saveCategory(statementId, transactionId, category, remember) {
  const response = await fetch(`/api/statements/${statementId}/transactions/${transactionId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ category, remember }),
  });
  if (!response.ok) throw new Error(await readError(response));
  return response.json();
}
