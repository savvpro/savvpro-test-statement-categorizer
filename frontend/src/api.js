const BASE = "http://127.0.0.1:8000/api";

async function handle(response) {
  if (!response.ok) {
    let message = `Request failed (${response.status})`;
    try {
      const body = await response.json();
      if (typeof body.detail === "string") message = body.detail;
      else if (Array.isArray(body.detail)) message = body.detail.map((d) => d.msg).join("; ");
    } catch {
      /* body was not JSON; keep the generic message */
    }
    throw new Error(message);
  }
  return response.json();
}

export async function uploadStatement(file, loan) {
  const form = new FormData();
  form.append("file", file);
  if (loan) form.append("loan", JSON.stringify(loan));
  return handle(await fetch(`${BASE}/statements`, { method: "POST", body: form }));
}

export async function correctTransaction(statementId, transactionId, category) {
  return handle(
    await fetch(`${BASE}/statements/${statementId}/transactions/${transactionId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ category }),
    })
  );
}

export async function setLoan(statementId, loan) {
  return handle(
    await fetch(`${BASE}/statements/${statementId}/loan`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(loan),
    })
  );
}