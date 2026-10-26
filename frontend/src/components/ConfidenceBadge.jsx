export default function ConfidenceBadge({ band, confidence }) {
  return (
    <span className={`badge badge-${band}`} title={`confidence ${confidence.toFixed(2)}`}>
      {band}
    </span>
  )
}
