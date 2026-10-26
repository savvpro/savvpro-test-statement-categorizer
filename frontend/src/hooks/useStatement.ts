import { useCallback, useEffect, useState } from "react";
import {
  DEFAULT_CONFIG,
  correctTransaction,
  fetchConfig,
  getCategories,
  uploadStatement,
} from "../api/client";
import { describeError, isRateLimited } from "../errors";
import type { FriendlyError } from "../errors";
import { savedMessage } from "../format";
import type {
  AmountConvention,
  AppConfig,
  Category,
  SaveCorrection,
  StatementResult,
} from "../types";

export interface Notice {
  kind: "success" | "error";
  text: string;
}

export function useStatement() {
  const [statement, setStatement] = useState<StatementResult | null>(null);
  const [categories, setCategories] = useState<Category[]>([]);
  const [categoriesError, setCategoriesError] = useState<string | null>(null);
  const [config, setConfig] = useState<AppConfig>(DEFAULT_CONFIG);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<FriendlyError | null>(null);
  const [retryUntil, setRetryUntil] = useState<number | null>(null);
  const [savingId, setSavingId] = useState<string | null>(null);
  const [notice, setNotice] = useState<Notice | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetchConfig().then((cfg) => {
      if (!cancelled) setConfig(cfg);
    });
    getCategories()
      .then((list) => {
        if (!cancelled) setCategories(list);
      })
      .catch((err: unknown) => {
        if (!cancelled) setCategoriesError(describeError(err).message);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const upload = useCallback(async (file: File, convention: AmountConvention) => {
    setUploading(true);
    setUploadError(null);
    setNotice(null);
    try {
      setStatement(await uploadStatement(file, convention));
    } catch (err) {
      if (isRateLimited(err)) {
        setRetryUntil(Date.now() + (err.retryAfter ?? 10) * 1000);
      } else {
        setUploadError(describeError(err));
      }
    } finally {
      setUploading(false);
    }
  }, []);

  const statementId = statement?.id ?? null;

  const save: SaveCorrection = useCallback(
    async (txnId, categoryId, applyToSimilar) => {
      if (!statementId) return;
      setSavingId(txnId);
      setNotice(null);
      try {
        const res = await correctTransaction(statementId, txnId, categoryId, applyToSimilar);
        setStatement(res.statement);
        setNotice({ kind: "success", text: savedMessage(res.updated_count, applyToSimilar) });
      } catch (err) {
        setNotice({ kind: "error", text: `Could not save. ${describeError(err).message}` });
      } finally {
        setSavingId(null);
      }
    },
    [statementId],
  );

  return {
    statement,
    categories,
    categoriesError,
    config,
    uploading,
    uploadError,
    retryUntil,
    savingId,
    notice,
    upload,
    save,
  };
}
