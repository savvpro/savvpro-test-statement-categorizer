import type {Transaction} from "@/types/transaction";
import type {MerchantRule} from "@/types/merchant-rule";
const t=(id:string,date:string,description:string,merchant:string|null,amount:number,category:string,confidence:number,reason:string,transactionType:Transaction["transactionType"]):Transaction=>({id,date,description,merchant,amount,category,confidence,reason,transactionType,status:category==="Needs Review"?"needs_review":"automatic"});
export const DEMO_TRANSACTIONS:Transaction[]=[
t("t1","2025-01-03","ADOBE CREATIVE CLOUD","Adobe",-59.99,"Software",98,"Known software merchant rule","expense"),
t("t2","2025-01-05","UBER TRIP","Uber",-18.4,"Travel and Transportation",98,"Known travel merchant rule","expense"),
t("t3","2025-01-07","CLIENT PAYMENT ACME","Acme Co",2400,"Income",90,"Matched invoice deposit pattern","income"),
t("t4","2025-01-09","TRANSFER TO SAVINGS",null,-500,"Transfer",98,"Recognized internal transfer pattern","transfer"),
t("t5","2025-01-12","FIGMA PRO","Figma",-15,"Software",98,"Known software merchant rule","expense"),
t("t6","2025-01-15","VERCEL INC","Vercel",-20,"Software",98,"Known software merchant rule","expense"),
t("t7","2025-01-18","MYSTERY SHOP 4821",null,-42.17,"Needs Review",0,"No reliable rule matched","unknown"),
t("t8","2025-02-02","GITHUB TEAM","GitHub",-4,"Software",98,"Known software merchant rule","expense"),
t("t9","2025-02-06","LYFT RIDE","Lyft",-23.1,"Travel and Transportation",95,"Known travel merchant rule","expense"),
t("t10","2025-02-10","ADOBE REFUND","Adobe",59.99,"Refund",80,"Merchant credit matches prior charge","refund"),
];
export const DEMO_RULES:MerchantRule[]=[
{id:"r1",name:"Adobe",keywords:["adobe"],category:"Software",priority:10},
{id:"r2",name:"Figma",keywords:["figma"],category:"Software",priority:10},
{id:"r3",name:"GitHub",keywords:["github"],category:"Software",priority:10},
{id:"r4",name:"Vercel",keywords:["vercel"],category:"Software",priority:10},
{id:"r5",name:"Uber",keywords:["uber"],category:"Travel and Transportation",priority:10},
{id:"r6",name:"Lyft",keywords:["lyft"],category:"Travel and Transportation",priority:10},
{id:"r7",name:"Internal transfers",keywords:["transfer to","transfer from"],category:"Transfer",priority:20},
];
