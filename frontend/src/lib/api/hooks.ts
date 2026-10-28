"use client";
import { useMutation, useQueries, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, type TxFilters } from "./client";
import type { CorrectionIn, CorrectionOut, TransactionPage } from "./types";

export const keys = {
  statements: ["statements"] as const,
  statement: (id: string) => ["statement", id] as const,
  txs: (id: string) => ["transactions", id] as const,
  summary: (id: string) => ["summary", id] as const,
  categories: ["categories"] as const,
};

export const useStatements = () =>
  useQuery({ queryKey: keys.statements, queryFn: api.listStatements });
export const useStatement = (id: string) =>
  useQuery({ queryKey: keys.statement(id), queryFn: () => api.getStatement(id) });
export const useTransactions = (id: string, f: TxFilters = {}) =>
  useQuery({ queryKey: [...keys.txs(id), f], queryFn: () => api.listTransactions(id, f) });
export const TX_PAGE = 500;

/** Loads `pages` consecutive pages (limit/offset) and merges them; the server caps a page at 500. */
export function usePagedTransactions(id: string, pages: number) {
  const results = useQueries({
    queries: Array.from({ length: pages }, (_, i) => ({
      queryKey: [...keys.txs(id), { limit: TX_PAGE, offset: i * TX_PAGE }],
      queryFn: () => api.listTransactions(id, { limit: TX_PAGE, offset: i * TX_PAGE }),
    })),
  });
  const first = results[0];
  const data: TransactionPage | undefined = first?.data
    ? { items: results.flatMap((r) => r.data?.items ?? []), total: first.data.total }
    : undefined;
  const failed = results.find((r) => r.isError);
  return {
    data,
    isLoading: first?.isLoading ?? true,
    isFetching: results.some((r) => r.isFetching),
    isError: Boolean(failed),
    error: (failed?.error ?? null) as Error | null,
    refetch: () => Promise.all(results.map((r) => r.refetch())),
  };
}

export const useSummary = (id: string) =>
  useQuery({ queryKey: keys.summary(id), queryFn: () => api.summary(id) });
export const useCategories = () =>
  useQuery({ queryKey: keys.categories, queryFn: api.categories, staleTime: Infinity });

export function useUpload() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (v: { file: File; accountType: string }) => api.upload(v.file, v.accountType),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.statements }),
  });
}

type Snapshot = [readonly unknown[], TransactionPage | undefined][];

/** Optimistic fix: patch the row in every cached page, then reconcile with the server. */
export function useFixTransaction(statementId: string) {
  const qc = useQueryClient();
  return useMutation<CorrectionOut, Error, CorrectionIn & { id: string }, { prev: Snapshot }>({
    mutationFn: ({ id, ...body }) => api.fix(id, body),
    onMutate: async (v) => {
      await qc.cancelQueries({ queryKey: keys.txs(statementId) });
      const prev = qc.getQueriesData<TransactionPage>({ queryKey: keys.txs(statementId) });
      qc.setQueriesData<TransactionPage>({ queryKey: keys.txs(statementId) }, (old) =>
        old
          ? {
              ...old,
              items: old.items.map((t) =>
                t.id === v.id
                  ? { ...t, category: v.category, status: "user_confirmed" as const }
                  : t,
              ),
            }
          : old,
      );
      return { prev };
    },
    onError: (_e, _v, ctx) => {
      ctx?.prev.forEach(([k, d]) => qc.setQueryData(k, d));
    },
    onSettled: () => {
      void qc.invalidateQueries({ queryKey: keys.txs(statementId) });
      void qc.invalidateQueries({ queryKey: keys.statement(statementId) });
      void qc.invalidateQueries({ queryKey: keys.summary(statementId) });
      void qc.invalidateQueries({ queryKey: keys.statements });
    },
  });
}

export function useRestoreDuplicate(statementId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (txId: string) => api.restore(txId),
    onSettled: () => {
      void qc.invalidateQueries({ queryKey: keys.txs(statementId) });
      void qc.invalidateQueries({ queryKey: keys.statement(statementId) });
      void qc.invalidateQueries({ queryKey: keys.summary(statementId) });
    },
  });
}
