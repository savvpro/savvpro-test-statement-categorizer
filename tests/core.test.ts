import {describe,it,expect} from "vitest";
import {DEMO_TRANSACTIONS as D} from "@/lib/demo-data";
import {summarize,filterTx,setCategory} from "@/lib/calculations";
import {toCsv} from "@/lib/export-csv";
describe("core",()=>{
 it("excludes transfers/refunds/review from expenses",()=>{const s=summarize(D);expect(s.expenses).toBeCloseTo(59.99+18.4+15+20+4+23.1);expect(s.review).toBe(1)});
 it("filters",()=>{expect(filterTx(D,{q:"adobe",category:"",status:"",type:"refund"})).toHaveLength(1)});
 it("preserves original on correction",()=>{const r=setCategory(D,["t7"],"Meals and Coffee")[6];expect(r.originalCategory).toBe("Needs Review");expect(r.status).toBe("corrected");expect(r.description).toBe("MYSTERY SHOP 4821")});
 it("escapes csv and blocks formulas",()=>{const c=toCsv([{...D[0],description:'=SUM(A1), "x"'}]);expect(c).toContain(`"'=SUM(A1), ""x"""`)});
});
