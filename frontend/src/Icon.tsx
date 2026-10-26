const paths = {
  ledger: 'M5 3h14v18H5z M9 7h6 M9 11h6 M9 15h3',
  upload: 'M12 16V3 M7 8l5-5 5 5 M4 15v6h16v-6',
  download: 'M12 3v13 M7 11l5 5 5-5 M4 16v5h16v-5',
  expense: 'M6 6l12 12 M6 18h12V6',
  income: 'M6 18L18 6 M6 6h12v12',
  refund: 'M4 10h10a6 6 0 0 1 0 12 M4 10l5-5 M4 10l5 5',
  transfer: 'M3 7h17 M16 3l4 4-4 4 M21 17H4 M8 13l-4 4 4 4',
  search: 'M21 21l-5-5 M18 10a8 8 0 1 1-16 0 8 8 0 0 1 16 0',
  check: 'M5 12l4 4L19 6',
  file: 'M14 2H5v20h14V7z M14 2v5h5 M8 12h8 M8 16h6',
  review: 'M12 8v5 M12 17h.01 M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20',
} as const

export function Icon({
  name,
  size = 20,
}: {
  name: keyof typeof paths
  size?: number
}) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.7"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d={paths[name]} />
    </svg>
  )
}
