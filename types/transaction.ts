export type TransactionType="expense"|"income"|"refund"|"transfer"|"unknown";
export type Status="automatic"|"needs_review"|"corrected";
export type Transaction={id:string;date:string;description:string;merchant:string|null;amount:number;category:string;confidence:number;reason:string;status:Status;transactionType:TransactionType;originalCategory?:string};
