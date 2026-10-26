import { useCallback, useEffect, useMemo, useState } from "react";
import { api } from "../lib/api.js";
import { REVIEW, totalsByCategory } from "../lib/format.js";

/** Owns the statement being reviewed and every action the user can take on it. */
export function useStatement() {
  const [rows, setRows] = useState([]);
  const [issues, setIssues] = useState([]);
  const [fileName, setFileName] = useState("");
  const [status, setStatus] = useState({ loading: false, error: "", notice: "" });

  const upload = useCallback(async (file) => {
    setStatus({ loading: true, error: "", notice: "" });
    try {
      const result = await api.categorize(file);
      setRows(result.transactions);
      setIssues(result.issues);
      setFileName(file.name);
      setStatus({ loading: false, error: "", notice: "" });
    } catch (e) {
      setStatus({ loading: false, error: e.message, notice: "" });
    }
  }, []);

  const correct = (row) => ({ ...row, confidence: 1, reasons: ["Set by you"], corrected: true });

  const setCategory = useCallback((rowNumber, category) => {
    setRows((current) => current.map((r) => (r.row === rowNumber ? { ...correct(r), category } : r)));
  }, []);

  const applyToMerchant = useCallback((merchant, category) => {
    setRows((current) =>
      current.map((r) => (r.merchant === merchant && r.category === REVIEW && !r.flags.includes("duplicate") ? { ...correct(r), category } : r))
    );
  }, []);

  const rememberMerchant = useCallback(async (merchant, category) => {
    try {
      await api.saveRule(merchant, category);
      applyToMerchant(merchant, category);
      setStatus((s) => ({ ...s, error: "", notice: `Saved: ${merchant} will be "${category}" on future statements.` }));
    } catch (e) {
      setStatus((s) => ({ ...s, error: e.message }));
    }
  }, [applyToMerchant]);

  const pending = useMemo(() => rows.filter((r) => r.category === REVIEW).length, [rows]);
  const totals = useMemo(() => totalsByCategory(rows), [rows]);

  return { rows, issues, fileName, status, pending, totals, upload, setCategory, applyToMerchant, rememberMerchant };
}

/** Re-estimates tax whenever categories change, debounced to avoid a request per click. */
export function useTaxEstimate(rows) {
  const [estimate, setEstimate] = useState(null);
  useEffect(() => {
    if (!rows.length) return setEstimate(null);
    const timer = setTimeout(() => api.taxEstimate(rows).then(setEstimate).catch(() => setEstimate(null)), 300);
    return () => clearTimeout(timer);
  }, [rows]);
  return estimate;
}
