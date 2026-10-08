import { useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { fetchCategories, fetchProducts } from '../api'
import ProductCard from '../components/ProductCard'
import type { Product } from '../types'

const ALL = 'All'

export default function Products() {
  const [products, setProducts] = useState<Product[]>([])
  const [categories, setCategories] = useState<string[]>([])
  const [query, setQuery] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [params, setParams] = useSearchParams()

  const category = params.get('category') ?? ALL

  useEffect(() => {
    Promise.all([fetchProducts(), fetchCategories()])
      .then(([all, cats]) => {
        setProducts(all)
        setCategories(cats)
      })
      .catch(() => setError('The shop catalogue is not responding. Is the API running?'))
      .finally(() => setLoading(false))
  }, [])

  const visible = useMemo(() => {
    const needle = query.trim().toLowerCase()
    return products.filter((product) => {
      if (category !== ALL && product.category !== category) return false
      if (!needle) return true
      // Search the tags too: three products have thin descriptions, and tags
      // catch shopper phrasing the description never uses.
      const haystack = [product.name, product.description, ...product.colors, ...product.search_tags]
        .join(' ')
        .toLowerCase()
      return haystack.includes(needle)
    })
  }, [products, category, query])

  function pick(next: string) {
    if (next === ALL) {
      params.delete('category')
    } else {
      params.set('category', next)
    }
    setParams(params, { replace: true })
  }

  return (
    <div className="page">
      <header className="page__head">
        <span className="eyebrow">The catalogue</span>
        <h1>Find Yours</h1>
        <p>
          Every garment we print, straight from the shop floor. Pick one up to see its sizes,
          its colours, and exactly what is on the shelf today.
        </p>
      </header>

      <div className="filters">
        <div className="filters__chips">
          {[ALL, ...categories].map((option) => (
            <button
              key={option}
              className={option === category ? 'chip chip--on' : 'chip'}
              onClick={() => pick(option)}
            >
              {option}
            </button>
          ))}
        </div>
        <input
          className="filters__search"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Search by name, colour or tag"
          aria-label="Search products"
        />
      </div>

      {error && <p className="notice notice--error">{error}</p>}
      {loading && <p className="notice">Loading the catalogue...</p>}

      {!loading && !error && (
        <>
          <p className="result-count">
            {visible.length} {visible.length === 1 ? 'product' : 'products'}
            {category !== ALL && ` in ${category}`}
          </p>
          {visible.length === 0 ? (
            <p className="notice">Nothing matched that. Try a broader search.</p>
          ) : (
            <div className="grid">
              {visible.map((product) => (
                <ProductCard key={product.product_id} product={product} />
              ))}
            </div>
          )}
        </>
      )}
    </div>
  )
}
