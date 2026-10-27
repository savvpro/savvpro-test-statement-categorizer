"use client";
import {useStore} from "@/lib/store";
export default function Settings(){const {reset,clear}=useStore();
return <><h1 className="text-xl font-semibold">Settings</h1><div className="card space-y-2 text-sm"><label className="block">Currency <select className="inp"><option>USD</option><option>EUR</option><option>GBP</option></select></label><p>Data retention: demo data lives only in this browser session. No real statement contents are stored. Never enter bank passwords or card numbers here.</p>
<button className="btn2" onClick={()=>confirm("Clear all demo data?")&&clear()}>Clear demo data</button> <button className="btn2" onClick={()=>confirm("Reset demo data?")&&reset()}>Reset demo data</button></div></>}
