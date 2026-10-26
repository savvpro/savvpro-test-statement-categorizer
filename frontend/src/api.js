export async function categorize(file, { positiveIsCharge, overrides }) {
  const form = new FormData();
  form.append("file", file);
  form.append("positive_is_charge", String(positiveIsCharge));
  form.append("overrides", JSON.stringify(overrides));
  const response = await fetch("/api/categorize", { method: "POST", body: form });
  if (!response.ok) {
    let message = `Request failed (${response.status})`;
    try {
      const body = await response.json();
      if (typeof body.detail === "string") message = body.detail;
    } catch {
      /* keep default message */
    }
    throw new Error(message);
  }
  return response.json();
}
