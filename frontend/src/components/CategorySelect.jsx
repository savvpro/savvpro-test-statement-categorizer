import { getCategoryTone } from "../constants/categories";

export default function CategorySelect({ value, categories, onChange, disabled }) {
  const tone = getCategoryTone(value);

  return (
    <span
      className="cat-select"
      style={{ "--cat-bg": tone.bg, "--cat-fg": tone.fg }}
    >
      <select
        value={value}
        disabled={disabled}
        onChange={(e) => onChange(e.target.value)}
      >
        {categories.map((c) => (
          <option key={c} value={c}>
            {c}
          </option>
        ))}
      </select>
    </span>
  );
}
