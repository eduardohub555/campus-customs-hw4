import { useEffect, useRef } from 'react'
import { Link } from 'react-router-dom'
import ProductCard from './ProductCard'
import HandsomeDan from './HandsomeDan'
import { useChatResults } from '../chatResults'

/**
 * The product matches from the conversation, laid out on the page.
 *
 * Uses the same ProductCard as the Products page, so a card the assistant put
 * here opens the same single-item page as one the shopper found by browsing.
 */
export default function ChatResultsBand() {
  const { results, clear } = useChatResults()
  const ref = useRef<HTMLElement>(null)

  // Bring a new set into view: the chat panel sits in the corner, so results
  // arriving at the top of the page would otherwise go unnoticed.
  useEffect(() => {
    if (results) {
      ref.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }
  }, [results])

  if (!results || results.products.length === 0) return null

  return (
    <section className="results" ref={ref} aria-label="Products from your conversation">
      <div className="results__inner">
        <header className="results__head">
          <HandsomeDan size={56} />
          <div>
            <span className="eyebrow">From the shop assistant</span>
            <h2>{results.title}</h2>
            <p className="results__query">
              You asked: <em>&ldquo;{results.query}&rdquo;</em>
            </p>
          </div>
          <button className="results__close" onClick={clear} aria-label="Dismiss these results">
            &times;
          </button>
        </header>

        <div className="grid">
          {results.products.map((product) => (
            <ProductCard key={product.product_id} product={product} />
          ))}
        </div>

        <footer className="results__foot">
          <span>Pick one up &mdash; sizes, colours and the full story are a click away.</span>
          <Link to="/products" className="btn btn--ghost">
            Browse the whole catalogue
          </Link>
        </footer>
      </div>
    </section>
  )
}
