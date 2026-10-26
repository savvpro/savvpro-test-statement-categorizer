import React from 'react';

export default function Navbar({ backendConnected }) {
  return (
    <header className="header">
      <div className="header-brand">
        <h1>
          <span>⚡</span>
          <span>Statement Categorizer</span>
        </h1>
        <p>Deterministic tax-time transaction sorting & review for freelancers</p>
      </div>
      <div className="header-actions">
        {backendConnected ? (
          <span className="badge badge-success" title="FastAPI backend is running and responding">
            ● API Connected
          </span>
        ) : (
          <span className="badge badge-danger" title="Ensure backend server is running on port 8000">
            ○ API Disconnected
          </span>
        )}
      </div>
    </header>
  );
}
