import {DEMO_TRANSACTIONS} from "./demo-data";
import type {Transaction} from "@/types/transaction";
/** DEMO ONLY: ignores file contents and returns synthetic data. Replaced by the FastAPI endpoint in real mode. */
export async function demoProcess(_f:File,onStage:(i:number)=>void):Promise<Transaction[]>{for(let i=0;i<4;i++){onStage(i);await new Promise(r=>setTimeout(r,500))}return DEMO_TRANSACTIONS}
