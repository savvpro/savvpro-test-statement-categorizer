import { useEffect } from 'react'

interface Props {
  message: string
  onClose: () => void
}

export function Toast({ message, onClose }: Props) {
  useEffect(() => {
    const timer = window.setTimeout(onClose, 4000)
    return () => window.clearTimeout(timer)
  }, [message, onClose])

  return (
    <div className="toast" role="status">
      {message}
    </div>
  )
}
