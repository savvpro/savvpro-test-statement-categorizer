export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api${path}`, init);
  if (!response.ok) {
    const error = await response
      .json()
      .catch(() => ({ detail: "The server could not complete this request." }));
    throw new Error(
      typeof error.detail === "string"
        ? error.detail
        : error.detail?.message ||
            (Array.isArray(error.detail)
              ? error.detail
                  .map((item: { msg: string }) =>
                    item.msg.replace(/^Value error, /, ""),
                  )
                  .join(" ")
              : "Check your values and try again."),
    );
  }
  return response.status === 204 ? (undefined as T) : response.json();
}
export function uploadData(file: File, options?: unknown) {
  const form = new FormData();
  form.append("file", file);
  if (options) form.append("options", JSON.stringify(options));
  return form;
}
export function money(amount: number, currency = "PKR") {
  return new Intl.NumberFormat("en-PK", {
    style: "currency",
    currency,
    maximumFractionDigits: 2,
  }).format(amount / 100);
}
export function title(value: string) {
  return value.replaceAll("_", " ").replace(/\b\w/g, (c) => c.toUpperCase());
}
