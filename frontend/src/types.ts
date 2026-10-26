export interface Transaction {
  id: number
  date: string
  descriptionraw: string
  amount: number
  category: string
  confidence: number
  reason: string
  route: string
  signals: any[]
  conflicts: string[]
  suggestedcategory: string | null
  tworeasonsmet: boolean
  isrefund: boolean
  isduplicate: boolean
  isrecurring: boolean
}

export interface Summary {
  totalspercategory: Record<string, number>
  totalincome: number
  totalspending: number
  needsreviewcount: number
  excludedcount: number
}