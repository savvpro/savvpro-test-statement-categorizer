import { colorFor } from '../categories'

export function Panel({ title, aside, children, className = '' }) {
  return (
    <section className={`rounded-2xl border border-line bg-white p-5 sm:p-6 ${className}`}>
      {(title || aside) && (
        <div className="mb-4 flex flex-wrap items-baseline justify-between gap-2">
          {title && <h2 className="font-display text-xl font-bold tracking-tight">{title}</h2>}
          {aside}
        </div>
      )}
      {children}
    </section>
  )
}

export function Segmented({ label, value, options, onChange }) {
  return (
    <fieldset>
      <legend className="mb-1.5 text-sm font-medium text-ink-soft">{label}</legend>
      <div className="inline-flex flex-wrap gap-1 rounded-xl bg-paper p-1">
        {options.map((option) => (
          <button
            key={option.value}
            type="button"
            aria-pressed={value === option.value}
            onClick={() => onChange(option.value)}
            className={`rounded-lg px-3 py-1.5 text-sm transition-colors ${
              value === option.value
                ? 'bg-ink font-medium text-white'
                : 'text-ink-soft hover:bg-white hover:text-ink'
            }`}
          >
            {option.label}
          </button>
        ))}
      </div>
    </fieldset>
  )
}

export function CategoryChip({ name, muted = false }) {
  const color = colorFor(name)
  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-sm font-medium"
      style={{ backgroundColor: `${color}${muted ? '12' : '1f'}`, color }}
    >
      <span className="size-2 rounded-full" style={{ backgroundColor: color }} />
      {name}
    </span>
  )
}

export function CategorySelect({ categories, value, onChange, id, money }) {
  const fits = categories.filter((c) => (money === 'out' ? c.kind !== 'income' : true))
  return (
    <select
      id={id}
      value={value ?? ''}
      onChange={(event) => onChange(event.target.value)}
      className="w-full rounded-lg border border-line bg-white px-2.5 py-1.5 text-sm"
    >
      <option value="" disabled>
        Pick a category
      </option>
      {fits.map((c) => (
        <option key={c.name} value={c.name}>
          {c.name}
        </option>
      ))}
    </select>
  )
}

export function Button({ variant = 'primary', className = '', ...props }) {
  const styles = {
    primary: 'bg-lapis text-white hover:bg-[#1b39a3] disabled:bg-[#9aaae0]',
    ink: 'bg-ink text-white hover:bg-[#0c1529]',
    quiet: 'border border-line bg-white text-ink hover:border-ink-soft',
    danger: 'text-brick hover:bg-[#fbeae7]',
  }
  return (
    <button
      type="button"
      className={`inline-flex items-center justify-center gap-2 rounded-lg px-3.5 py-2 text-sm font-medium transition-colors disabled:cursor-not-allowed ${styles[variant]} ${className}`}
      {...props}
    />
  )
}
