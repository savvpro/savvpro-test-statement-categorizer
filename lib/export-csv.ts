import type {Transaction} from "@/types/transaction";
const cell=(v:string|number|null)=>{let s=v==null?"":String(v);if(/^[=+\-@\t\r]/.test(s))s="'"+s;return /[",\n\r]/.test(s)?`"${s.replace(/"/g,'""')}"`:s};
export const toCsv=(tx:Transaction[])=>["date,description,merchant,amount,category,confidence,status,reason",...tx.map(t=>[t.date,t.description,t.merchant,t.amount,t.category,t.confidence,t.status,t.reason].map(cell).join(","))].join("\n");
export function downloadCsv(tx:Transaction[]){const b=new Blob([toCsv(tx)],{type:"text/csv"});const a=document.createElement("a");a.href=URL.createObjectURL(b);a.download="transactions.csv";a.click();URL.revokeObjectURL(a.href)}
