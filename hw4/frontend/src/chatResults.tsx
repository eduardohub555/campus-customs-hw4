import { createContext, useCallback, useContext, useMemo, useState } from 'react'
import type { Product } from './types'

export interface ChatResults {
  /** The heading the agent chose for this set, e.g. "Hoodies". */
  title: string
  /** What the shopper typed, shown so the band explains itself. */
  query: string
  products: Product[]
}

interface ChatResultsState {
  results: ChatResults | null
  show: (results: ChatResults) => void
  clear: () => void
}

const Context = createContext<ChatResultsState | null>(null)

/**
 * Holds the product matches the shop assistant last returned.
 *
 * The chat panel writes here; the band under the navigation bar reads from
 * here. Keeping it in context rather than inside the panel is what lets the
 * results live on the page instead of in the conversation.
 */
export function ChatResultsProvider({ children }: { children: React.ReactNode }) {
  const [results, setResults] = useState<ChatResults | null>(null)

  const show = useCallback((next: ChatResults) => setResults(next), [])
  const clear = useCallback(() => setResults(null), [])

  const value = useMemo(() => ({ results, show, clear }), [results, show, clear])
  return <Context.Provider value={value}>{children}</Context.Provider>
}

export function useChatResults(): ChatResultsState {
  const context = useContext(Context)
  if (!context) throw new Error('useChatResults must be used inside ChatResultsProvider')
  return context
}
