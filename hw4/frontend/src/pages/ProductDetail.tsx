import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { fetchDiscount, fetchProduct, fetchProductRating, formatPrice } from '../api'
import BuyPanel from '../components/BuyPanel'
import { useAuth } from '../auth'
import type { DiscountOffer, Product, ProductRating } from '../types'

export default function ProductDetail() {
  const { productId } = useParams<{ productId: string }>()
  const { user } = useAuth()
  const [product, setProduct] = useState<Product | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [chosenSize, setChosenSize] = useState<string | null>(null)
  const [rating, setRating] = useState<ProductRating | null>(null)
  const [offer, setOffer] = useState<DiscountOffer | null>(null)

  useEffect(() => {
    if (!productId) return
    window.scrollTo(0, 0)
    setProduct(null)
    setError(null)
    setChosenSize(null)
    fetchProduct(productId)
      .then(setProduct)
      .catch(() => setError('We could not find that product.'))
    fetchProductRating(productId).then(setRating).catch(() => setRating(null))
  }, [productId])

  // Handsome Dan's standing offer, so the price shown here is the price paid.
  useEffect(() => {
    if (!user) {
      setOffer(null)
      return
    }
    fetchDiscount().then((state) => setOffer(state.offer)).catch(() => setOffer(null))
  }, [user?.id])

  if (error) {
    return (
      <div className="page">
        <p className="notice notice--error">{error}</p>
        <Link to="/products" className="btn">
          Back to products
        </Link>
      </div>
    )
  }

  if (!product) {
    return (
      <div className="page">
        <p className="notice">Loading...</p>
      </div>
    )
  }

  const inStock = product.inventory.filter((size) => size.quantity > 0)

  return (
    <div className="page">
      <nav className="crumbs">
        <Link to="/products">Products</Link>
        <span>/</span>
        <Link to={`/products?category=${encodeURIComponent(product.category)}`}>
          {product.category}
        </Link>
        <span>/</span>
        <em>{product.name}</em>
      </nav>

      <div className="detail">
        <div className="detail__media">
          <img src={product.image_url} alt={product.name} />
        </div>

        <div className="detail__info">
          <span className="eyebrow">{product.category}</span>
          <h1>{product.name}</h1>
          <p className="detail__price">{formatPrice(product.price)}</p>

          {rating && (
            <p className="detail__rating">
              {rating.average !== null ? (
                <>
                  <span className="detail__stars" aria-hidden="true">
                    {'\u2605'.repeat(Math.round(rating.average))}
                    <span className="detail__stars-dim">
                      {'\u2605'.repeat(5 - Math.round(rating.average))}
                    </span>
                  </span>
                  {rating.average.toFixed(1)} out of 5 &middot;{' '}
                  {rating.ratings} {rating.ratings === 1 ? 'buyer' : 'buyers'}
                </>
              ) : (
                <span className="detail__unrated">No ratings yet</span>
              )}
            </p>
          )}
          <p className="detail__description">{product.description}</p>

          <dl className="detail__facts">
            <div>
              <dt>Style</dt>
              <dd>{product.garment_type}</dd>
            </div>
            {product.colors.length > 0 && (
              <div>
                <dt>Colours</dt>
                <dd className="swatches">
                  {product.colors.map((color) => (
                    <span key={color} className="swatch">
                      {color}
                    </span>
                  ))}
                </dd>
              </div>
            )}
          </dl>

          <div className="detail__sizes">
            <h2>Sizes</h2>
            {inStock.length === 0 ? (
              <p className="notice notice--error">Sold out in every size.</p>
            ) : (
              <>
                <div className="sizes">
                  {product.inventory.map((size) => {
                    const out = size.quantity === 0
                    const on = size.size === chosenSize
                    return (
                      <button
                        key={size.size}
                        disabled={out}
                        onClick={() => setChosenSize(on ? null : size.size)}
                        className={`size${out ? ' size--out' : ''}${on ? ' size--on' : ''}`}
                        title={out ? 'Out of stock' : `${size.quantity} in stock`}
                      >
                        {size.size}
                      </button>
                    )
                  })}
                </div>
                <p className="detail__stock">
                  {chosenSize
                    ? `${product.inventory.find((s) => s.size === chosenSize)?.quantity} left in ${chosenSize}.`
                    : `In stock: ${inStock.map((s) => `${s.size} (${s.quantity})`).join(', ')}.`}
                </p>
              </>
            )}
          </div>

          <BuyPanel product={product} size={chosenSize} offer={offer} />

          {product.search_tags.length > 0 && (
            <div className="tags">
              {product.search_tags.map((tag) => (
                <span key={tag}>{tag}</span>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
