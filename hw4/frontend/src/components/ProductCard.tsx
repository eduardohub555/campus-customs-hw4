import { Link } from 'react-router-dom'
import { formatPrice } from '../api'
import type { Product } from '../types'

export default function ProductCard({ product }: { product: Product }) {
  const soldOut = product.total_stock === 0

  return (
    <Link to={`/products/${product.product_id}`} className="card">
      <div className="card__frame">
        <img src={product.image_url} alt={product.name} loading="lazy" />
        {soldOut && <span className="card__badge">Sold out</span>}
      </div>
      <div className="card__body">
        <span className="card__category">{product.category}</span>
        <h3 className="card__name">{product.name}</h3>
        <p className="card__blurb">{product.short_description}</p>
        <div className="card__foot">
          <span className="card__price">{formatPrice(product.price)}</span>
          <span className="card__sizes">
            {soldOut ? 'Gone for now' : `${product.sizes_in_stock.length} sizes ready`}
          </span>
        </div>
      </div>
    </Link>
  )
}
