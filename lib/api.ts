import type {Transaction} from "@/types/transaction";
import type {MerchantRule} from "@/types/merchant-rule";
import {demoProcess} from "./demo-processor";
const BASE=process.env.NEXT_PUBLIC_API_BASE_URL??"";
export const isDemoMode=()=>BASE==="";
async function req<T>(path:string,init?:RequestInit):Promise<T>{const r=await fetch(BASE+path,init);if(!r.ok)throw new Error(`Request failed (${r.status})`);return r.json()}
export const uploadStatement=async(file:File,onStage:(i:number)=>void):Promise<Transaction[]>=>{if(isDemoMode())return demoProcess(file,onStage);const fd=new FormData();fd.append("file",file);return req("/statements",{method:"POST",body:fd})};
export const fetchTransactions=()=>req<Transaction[]>("/transactions");
export const updateTransactionCategory=(id:string,category:string)=>req<Transaction>(`/transactions/${id}`,{method:"PATCH",headers:{"Content-Type":"application/json"},body:JSON.stringify({category})});
export const fetchSummary=()=>req("/summary");
export const fetchMerchantRules=()=>req<MerchantRule[]>("/rules");
export const createMerchantRule=(r:Omit<MerchantRule,"id">)=>req<MerchantRule>("/rules",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(r)});
export const updateMerchantRule=(id:string,r:Partial<MerchantRule>)=>req<MerchantRule>(`/rules/${id}`,{method:"PATCH",headers:{"Content-Type":"application/json"},body:JSON.stringify(r)});
export const deleteMerchantRule=(id:string)=>req<void>(`/rules/${id}`,{method:"DELETE"});
