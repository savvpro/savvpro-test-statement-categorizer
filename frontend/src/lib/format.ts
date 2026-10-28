const usd = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" });

export const money = (value: string | number) => usd.format(Number(value));

export const shortDate = (iso: string) =>
  new Date(`${iso}T00:00:00`).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });

export const percent = (confidence: number) => `${Math.round(confidence * 100)}%`;
