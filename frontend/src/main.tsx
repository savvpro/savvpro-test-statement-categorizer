import { Component, type ReactNode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import "./styles.css";

class ErrorBoundary extends Component<
  { children: ReactNode },
  { failed: boolean }
> {
  state = { failed: false };
  static getDerivedStateFromError() {
    return { failed: true };
  }
  render() {
    if (this.state.failed)
      return (
        <div className="loading-state">
          <h1>Let’s reopen your workspace.</h1>
          <p>
            The interface encountered an error. Your saved statements are still
            on this computer.
          </p>
          <button
            className="button primary"
            onClick={() => window.location.reload()}
          >
            Reload Ledgerly
          </button>
        </div>
      );
    return this.props.children;
  }
}
createRoot(document.getElementById("root")!).render(
  <ErrorBoundary>
    <App />
  </ErrorBoundary>,
);
