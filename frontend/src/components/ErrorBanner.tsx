interface Props {
  message: string
  onDismiss: () => void
}

export function ErrorBanner({ message, onDismiss }: Props) {
  return (
    <div className="banner banner-error" role="alert">
      <span>{message}</span>
      <button type="button" className="link-button" onClick={onDismiss} aria-label="Dismiss error">
        Dismiss
      </button>
    </div>
  )
}
