export const money=(n:number,cur="USD")=>new Intl.NumberFormat("en-US",{style:"currency",currency:cur}).format(n);
export const fmtDate=(d:string)=>new Date(d+"T00:00:00").toLocaleDateString("en-US",{year:"numeric",month:"short",day:"numeric"});
