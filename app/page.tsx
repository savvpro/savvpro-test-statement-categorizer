"use client";
import Link from "next/link";import {BarChart,Bar,XAxis,YAxis,Tooltip,ResponsiveContainer,PieChart,Pie,Cell} from "recharts";
import {useStore} from "@/lib/store";import {summarize,byCategory,byMonth} from "@/lib/calculations";import {money} from "@/lib/formatters";
export default function Dashboard(){const tx=useStore(s=>s.tx);const s=summarize(tx);
const k=[["Transactions processed",s.count],["Confirmed expenses",money(s.expenses)],["Income received",money(s.income)],["Needs review",s.review],["Refunds",money(s.refunds)],["Transfers excluded",money(s.transfers)]];
return <><h1 className="text-xl font-semibold">Dashboard</h1><p className="text-sm text-slate-500">Demo data. Fictional and not from a real statement.</p>
{tx.length===0&&<p className="card">No transactions yet. <Link className="text-brand underline" href="/upload">Upload a statement</Link></p>}
<div className="grid grid-cols-2 gap-3 md:grid-cols-3">{k.map(([l,v])=><div key={l as string} className="card"><div className="text-xs text-slate-500">{l}</div><div className="text-xl font-semibold">{v}</div></div>)}</div>
<div className="grid gap-3 md:grid-cols-2"><div className="card h-64"><h2 className="mb-2 text-sm font-medium">Monthly expenses</h2><ResponsiveContainer><BarChart data={byMonth(tx)}><XAxis dataKey="month"/><YAxis/><Tooltip/><Bar dataKey="total" fill="#2563eb"/></BarChart></ResponsiveContainer></div>
<div className="card h-64"><h2 className="mb-2 text-sm font-medium">By category</h2><ResponsiveContainer><PieChart><Pie data={byCategory(tx)} dataKey="value" nameKey="name" label>{byCategory(tx).map((_,i)=><Cell key={i} fill={["#2563eb","#0ea5e9","#6366f1","#14b8a6"][i%4]}/>)}</Pie><Tooltip/></PieChart></ResponsiveContainer></div></div>
<div className="flex gap-2"><Link className="btn" href="/upload">Upload statement</Link><Link className="btn2" href="/review">Review transactions</Link></div></>}
