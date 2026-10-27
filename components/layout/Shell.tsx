"use client";
import Link from "next/link";import {usePathname} from "next/navigation";import {useState} from "react";
import {LayoutDashboard,Upload,Table2,ClipboardCheck,BarChart3,ListChecks,Settings,Moon,Menu,Bell} from "lucide-react";
const NAV=[["/","Dashboard",LayoutDashboard],["/upload","Upload Statement",Upload],["/transactions","Transactions",Table2],["/review","Needs Review",ClipboardCheck],["/reports","Reports",BarChart3],["/rules","Merchant Rules",ListChecks],["/settings","Settings",Settings]] as const;
export function Shell({children}:{children:React.ReactNode}){const p=usePathname();const [open,setOpen]=useState(false);
const nav=<nav aria-label="Main" className="space-y-1 p-3">{NAV.map(([h,l,I])=><Link key={h} href={h} onClick={()=>setOpen(false)} aria-current={p===h?"page":undefined} className={`flex items-center gap-3 rounded-lg px-3 py-2 text-sm ${p===h?"bg-blue-50 font-semibold text-brand dark:bg-slate-800":"hover:bg-slate-100 dark:hover:bg-slate-800"}`}><I size={18} aria-hidden/>{l}</Link>)}</nav>;
return <div className="min-h-screen lg:flex"><aside className="hidden w-60 shrink-0 border-r border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900 lg:block"><div className="p-4 font-bold">Statement Categorizer</div>{nav}</aside>
{open&&<div className="border-b bg-white dark:bg-slate-900 lg:hidden">{nav}</div>}
<div className="flex-1"><header className="flex items-center gap-3 border-b border-slate-200 bg-white p-3 dark:border-slate-800 dark:bg-slate-900"><button className="btn2 lg:hidden" aria-label="Toggle menu" aria-expanded={open} onClick={()=>setOpen(!open)}><Menu size={16}/></button>
<input className="inp max-w-xs flex-1" type="search" aria-label="Search" placeholder="Search"/><span className="ml-auto rounded bg-amber-100 px-2 py-1 text-xs text-amber-900">Demo data</span>
<button className="btn2" aria-label="Notifications"><Bell size={16}/></button><button className="btn2" aria-label="Toggle dark mode" onClick={()=>document.documentElement.classList.toggle("dark")}><Moon size={16}/></button><span className="grid h-8 w-8 place-items-center rounded-full bg-brand text-xs text-white" aria-label="Demo user">DU</span></header>
<main className="mx-auto max-w-6xl space-y-4 p-4">{children}</main></div></div>}
