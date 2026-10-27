"use client";
import {useState} from "react";import Link from "next/link";import {uploadStatement,isDemoMode} from "@/lib/api";import {validateFile} from "@/lib/validation";import {useStore} from "@/lib/store";
const STAGES=["Reading statement","Validating transactions","Categorizing transactions","Preparing results"];
export default function Upload(){const [f,setF]=useState<File|null>(null);const [err,setErr]=useState("");const [stage,setStage]=useState(-1);const [done,setDone]=useState(false);const setTx=useStore(s=>s.setTx);
const pick=(x?:File)=>{if(!x)return;const e=validateFile(x);setErr(e??"");setF(e?null:x);setDone(false)};
const run=async()=>{if(!f)return;setStage(0);try{setTx(await uploadStatement(f,setStage));setDone(true)}catch(e){setErr((e as Error).message)}setStage(-1)};
return <><h1 className="text-xl font-semibold">Upload statement</h1>
{isDemoMode()&&<p role="note" className="card text-sm">Demo mode: file contents are not read. Processing loads synthetic sample transactions.</p>}
<div className="card border-dashed text-center" onDragOver={e=>e.preventDefault()} onDrop={e=>{e.preventDefault();pick(e.dataTransfer.files[0])}}><p>Drag a CSV here (max 5 MB)</p><label className="btn mt-2 cursor-pointer">Browse files<input type="file" accept=".csv" className="sr-only" onChange={e=>pick(e.target.files?.[0])}/></label></div>
{err&&<p role="alert" className="text-red-700">{err}</p>}
{f&&<div className="card flex items-center justify-between"><span>{f.name} ({(f.size/1024).toFixed(1)} KB)</span><span className="flex gap-2"><button className="btn2" onClick={()=>setF(null)}>Remove</button><button className="btn" disabled={stage>=0} onClick={run}>Process</button></span></div>}
{stage>=0&&<ol className="card text-sm" aria-live="polite">{STAGES.map((s,i)=><li key={s}>{i<stage?"✓":i===stage?"…":"○"} {s}</li>)}</ol>}
{done&&<p role="status" className="card">Demo processing finished. <Link className="text-brand underline" href="/transactions">View categorized transactions</Link></p>}</>}
