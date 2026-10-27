"use client";
import {create} from "zustand";
import type {Transaction} from "@/types/transaction";
import type {MerchantRule} from "@/types/merchant-rule";
import {DEMO_TRANSACTIONS,DEMO_RULES} from "./demo-data";
import {setCategory} from "./calculations";
type S={tx:Transaction[];rules:MerchantRule[];setTx:(t:Transaction[])=>void;assign:(ids:string[],c:string)=>void;addRule:(r:MerchantRule)=>void;saveRule:(r:MerchantRule)=>void;delRule:(id:string)=>void;reset:()=>void;clear:()=>void};
export const useStore=create<S>(set=>({tx:DEMO_TRANSACTIONS,rules:DEMO_RULES,setTx:tx=>set({tx}),assign:(ids,c)=>set(s=>({tx:setCategory(s.tx,ids,c)})),addRule:r=>set(s=>({rules:[...s.rules,r]})),saveRule:r=>set(s=>({rules:s.rules.map(x=>x.id===r.id?r:x)})),delRule:id=>set(s=>({rules:s.rules.filter(r=>r.id!==id)})),reset:()=>set({tx:DEMO_TRANSACTIONS,rules:DEMO_RULES}),clear:()=>set({tx:[],rules:[]})}));
