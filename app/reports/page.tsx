"use client";
import {useStore} from "@/lib/store";import {summarize,byCategory} from "@/lib/calculations";import {money} from "@/lib/formatters";import {downloadCsv} from "@/lib/export-csv";
export default function Reports(){const tx=useStore(s=>s.tx);const s=summarize(tx);
return <><h1 className="text-xl font-semibold">Reports</h1><button className="btn2" onClick={()=>downloadCsv(tx)}>Export CSV</button>
<div className="card"><h2 className="font-medium">Income vs expenses</h2><p>Income {money(s.income)} · Expenses {money(s.expenses)}</p><p>Refunds {money(s.refunds)} and transfers {money(s.transfers)} are kept separate. {s.review} transactions still need review.</p></div>
<div className="card"><h2 className="font-medium">Spending by category</h2><ul>{byCategory(tx).map(c=><li key={c.name}>{c.name}: {money(c.value)}</li>)}</ul><p className="mt-2 text-xs text-slate-500">Category totals are not tax-deductibility determinations. Confirm with a tax professional.</p></div></>}
