export interface SizeStock {
  size: string
  quantity: number
}

export interface Product {
  product_id: string
  name: string
  garment_type: string
  category: string
  description: string
  short_description: string
  colors: string[]
  search_tags: string[]
  image_url: string
  price: number
  inventory: SizeStock[]
  total_stock: number
  sizes_in_stock: string[]
}

export interface ChatReply {
  reply: string
  products: Product[]
  /** The agent's heading for the cards, e.g. "Hoodies". */
  result_title: string | null
}

/** Where the shopper is standing, sent with every chat message. */
export interface PageContext {
  path: string
  product_id: string | null
  category: string | null
}

export interface StoredTurn {
  role: 'user' | 'assistant'
  content: string
  products: Product[]
  created_at: string
}

export interface ChatHistory {
  turns: StoredTurn[]
}

export interface DiscountOffer {
  code: string
  percent: number
  offered_at: string | null
  interested_at: string | null
  expired: boolean
}

export interface DiscountState {
  signed_in: boolean
  fresh?: boolean
  offer: DiscountOffer | null
  /** Handsome Dan's line, present only when the offer is new. */
  greeting: string | null
}

export interface ProductRating {
  product_id: string
  ratings: number
  average: number | null
}

export interface PurchaseReceipt {
  purchase_id: number
  product_id: string
  product_name: string
  size: string
  price_paid: number
  list_price: number
  discount_code: string | null
  stars: number | null
}
