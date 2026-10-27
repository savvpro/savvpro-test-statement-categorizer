"use client";
import {useState} from "react";import {useStore} from "@/lib/store";import {CATEGORIES} from "@/types/category";import {money} from "@/lib/formatters";
export default function Review(){const {tx,assign}=useStore();const [i,setI]=useState(0);const [cat,setCat]=useState("");const q=tx.filter(t=>t.status==="needs_review");const total=tx.filter(t=>t.status==="needs_review"||t.status==="corrected").length;const t=q[Math.min(i,q.length-1)];
if(!t)return <><h1 className="text-xl font-semibold">Needs review</h1><p className="card" role="status">Nothing left to review.</p></>;
const act=(c:string)=>{assign([t.id],c);setCat("")};
return <><h1 className="text-xl font-semibold">Needs review</h1><p className="text-sm">{total-q.length} of {total} reviewed</p>
<div className="card space-y-2"><h2 className="font-medium">{t.description}</h2><p>{money(t.amount)} on {t.date}</p><p className="text-sm">Why uncertain: {t.reason}. Merchant identity alone cannot show business or personal use.</p>
<select className="inp" aria-label="Category" value={cat} onChange={e=>setCat(e.target.value)}><option value="">Choose category</option>{CATEGORIES.filter(c=>c!=="Needs Review").map(c=><option key={c}>{c}</option>)}</select>
<div className="flex flex-wrap gap-2"><button className="btn" disabled={!cat} onClick={()=>act(cat)}>Confirm category</button><button className="btn2" onClick={()=>act("Transfer")}>Mark as transfer</button><button className="btn2" onClick={()=>act("Refund")}>Mark as refund</button><button className="btn2" onClick={()=>setI((i+1)%q.length)}>Skip for later</button></div>
<div className="flex gap-2"><button className="btn2" disabled={i===0} onClick={()=>setI(i-1)}>Previous</button><button className="btn2" disabled={i>=q.length-1} onClick={()=>setI(i+1)}>Next</button></div></div></>}
