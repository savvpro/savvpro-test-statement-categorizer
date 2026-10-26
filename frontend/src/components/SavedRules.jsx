import { useEffect, useState } from "react";
import { api } from "../lib/api.js";

/** Merchant rules learned from the user's corrections; applied on every future upload. */
export function SavedRules({ refreshKey }) {
  const [rules, setRules] = useState([]);
  const [error, setError] = useState("");

  useEffect(() => {
    api.rules().then(setRules).catch((e) => setError(e.message));
  }, [refreshKey]);

  const remove = async (merchant) => {
    try {
      await api.deleteRule(merchant);
      setRules((current) => current.filter((r) => r.merchant !== merchant));
    } catch (e) {
      setError(e.message);
    }
  };

  return (
    <details className="panel">
      <summary>Your saved merchant rules ({rules.length})</summary>
      {error && <p className="error-text">{error}</p>}
      {!rules.length && <p className="hint">Fix a row and choose "Always use this" to teach the app your merchants.</p>}
      <ul className="rules">
        {rules.map((r) => (
          <li key={r.merchant}><span><strong>{r.merchant}</strong> → {r.category}</span>
            <button className="link" onClick={() => remove(r.merchant)}>Remove</button></li>
        ))}
      </ul>
    </details>
  );
}
