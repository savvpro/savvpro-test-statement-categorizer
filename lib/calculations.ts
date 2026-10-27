import type {Transaction} from "@/types/transaction";
export const summarize=(tx:Transaction[])=>({
 count:tx.length,
 expenses:-tx.filter(t=>t.transactionType==="expense"&&t.status!=="needs_review").reduce((s,t)=>s+t.amount,0),
 income:tx.filter(t=>t.transactionType==="income").reduce((s,t)=>s+t.amount,0),
 refunds:tx.filter(t=>t.transactionType==="refund").reduce((s,t)=>s+t.amount,0),
 transfers:tx.filter(t=>t.transactionType==="transfer").reduce((s,t)=>s+Math.abs(t.amount),0),
 review:tx.filter(t=>t.status==="needs_review").length});
export const byCategory=(tx:Transaction[])=>{const m:Record<string,number>={};tx.filter(t=>t.transactionType==="expense"&&t.status!=="needs_review").forEach(t=>{m[t.category]=(m[t.category]??0)-t.amount});return Object.entries(m).map(([name,value])=>({name,value:Math.round(value*100)/100}))};
export const byMonth=(tx:Transaction[])=>{const m:Record<string,number>={};tx.filter(t=>t.transactionType==="expense"&&t.status!=="needs_review").forEach(t=>{const k=t.date.slice(0,7);m[k]=(m[k]??0)-t.amount});return Object.entries(m).sort().map(([month,total])=>({month,total:Math.round(total*100)/100}))};
export type Filters={q:string;category:string;status:string;type:string};
export const filterTx=(tx:Transaction[],f:Filters)=>tx.filter(t=>(!f.q||(t.description+(t.merchant??"")).toLowerCase().includes(f.q.toLowerCase()))&&(!f.category||t.category===f.category)&&(!f.status||t.status===f.status)&&(!f.type||t.transactionType===f.type));
export const setCategory=(tx:Transaction[],ids:string[],category:string):Transaction[]=>tx.map(t=>ids.includes(t.id)?{...t,originalCategory:t.originalCategory??t.category,category,status:"corrected",confidence:100,reason:"Manually corrected by user"}:t);
