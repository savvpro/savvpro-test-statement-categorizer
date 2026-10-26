import { Component, type ErrorInfo, type ReactNode } from 'react'

interface Props {
  children: ReactNode
}

interface State {
  failed: boolean
}

/** Catches an error thrown while rendering, so the page shows a message instead of going blank. */
export class ErrorBoundary extends Component<Props, State> {
  state: State = { failed: false }

  static getDerivedStateFromError(): State {
    return { failed: true }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('The page crashed while rendering:', error, info.componentStack)
  }

  render() {
    if (!this.state.failed) return this.props.children
    return (
      <div className="app">
        <p role="alert" className="alert">
          Something went wrong — reload the page.
        </p>
        <p>
          <button type="button" className="primary" onClick={() => window.location.reload()}>
            Reload page
          </button>
        </p>
      </div>
    )
  }
}
