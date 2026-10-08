import { readToken } from './auth'
import type {
  ChatHistory,
  ChatReply,
  DiscountState,
  PageContext,
  Product,
  ProductRating,
  PurchaseReceipt,
} from './types'

async function get<T>(path: string): Promise<T> {
  const response = await fetch(path)
  if (!response.ok) {
    throw new Error(`${response.status} from ${path}`)
  }
  return response.json() as Promise<T>
}

export const fetchProducts = () => get<Product[]>('/api/products')

export const fetchCategories = () => get<string[]>('/api/categories')

export const fetchProduct = (productId: string) =>
  get<Product>(`/api/products/${encodeURIComponent(productId)}`)

/** Ask the shop assistant. The reply carries product cards built from the database. */
export async function sendChatMessage(
  message: string,
  page: PageContext,
): Promise<ChatReply> {
  const token = readToken()
  const response = await fetch('/api/chat', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      // Signed in: the API passes the first name to the agent, nothing more.
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({ message, page }),
  })
  if (!response.ok) {
    throw new Error(`${response.status} from /api/chat`)
  }
  return response.json() as Promise<ChatReply>
}

/** A signed-in shopper's stored conversation. Guests always get an empty list. */
export async function fetchChatHistory(): Promise<ChatHistory> {
  const token = readToken()
  if (!token) return { turns: [] }
  const response = await fetch('/api/chat/history', {
    headers: { Authorization: `Bearer ${token}` },
  })
  if (!response.ok) return { turns: [] }
  return response.json() as Promise<ChatHistory>
}

export const formatPrice = (price: number) => `$${price.toFixed(2)}`


/** Handsome Dan's standing offer. Guests always get `signed_in: false`. */
export async function fetchDiscount(): Promise<DiscountState> {
  const token = readToken()
  if (!token) return { signed_in: false, offer: null, greeting: null }
  const response = await fetch('/api/perks/discount', {
    headers: { Authorization: `Bearer ${token}` },
  })
  if (!response.ok) return { signed_in: false, offer: null, greeting: null }
  return response.json() as Promise<DiscountState>
}

/** Record that the shopper asked to hear more about their discount. */
export async function noteDiscountInterest(): Promise<void> {
  const token = readToken()
  if (!token) return
  await fetch('/api/perks/discount/interest', {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}` },
  }).catch(() => undefined)
}

export async function fetchProductRating(productId: string): Promise<ProductRating> {
  return get<ProductRating>(`/api/products/${encodeURIComponent(productId)}/rating`)
}

/** Buy a garment, saving the star rating given at the same moment. */
export async function buyProduct(body: {
  product_id: string
  size: string
  stars: number | null
  use_discount: boolean
}): Promise<PurchaseReceipt> {
  const token = readToken()
  const response = await fetch('/api/purchases', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(body),
  })
  const payload = await response.json().catch(() => ({}))
  if (!response.ok) {
    throw new Error(typeof payload.detail === 'string' ? payload.detail : 'Could not complete the order.')
  }
  return payload as PurchaseReceipt
}
