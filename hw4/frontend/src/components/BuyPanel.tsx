import { useState } from 'react'
import { Link } from 'react-router-dom'
import { buyProduct, formatPrice } from '../api'
import { useAuth } from '../auth'
import type { DiscountOffer, Product, PurchaseReceipt } from '../types'

const STARS = [1, 2, 3, 4, 5]

/**
 * Buying a garment, with the rating asked for on the way.
 *
 * The rating is collected *before* the order completes — "how would you rate
 * the product you are about to buy" — and saved against the purchase, so every
 * rating in the database belongs to someone who actually bought the thing.
 * Answering is optional; being asked is not.
 */
export default function BuyPanel({
  product,
  size,
  offer,
}: {
  product: Product
  size: string | null
  offer: DiscountOffer | null
}) {
  const { user } = useAuth()
  const [open, setOpen] = useState(false)
  const [stars, setStars] = useState<number | null>(null)
  const [hovered, setHovered] = useState<number | null>(null)
  const [useDiscount, setUseDiscount] = useState(true)
  const [busy, setBusy] = useState(false)
  const [receipt, setReceipt] = useState<PurchaseReceipt | null>(null)
  const [error, setError] = useState<string | null>(null)

  const discounted = offer ? Math.round(product.price * (100 - offer.percent)) / 100 : null
  const payable = useDiscount && discounted !== null ? discounted : product.price

  async function complete() {
    if (!size) return
    setBusy(true)
    setError(null)
    try {
      setReceipt(
        await buyProduct({
          product_id: product.product_id,
          size,
          stars,
          use_discount: Boolean(offer) && useDiscount,
        }),
      )
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : 'Could not complete the order.')
    } finally {
      setBusy(false)
    }
  }

  if (receipt) {
    return (
      <div className="buy buy--done">
        <h3>Thank you.</h3>
        <p>
          {receipt.product_name} in {receipt.size}, {formatPrice(receipt.price_paid)}
          {receipt.discount_code && (
            <>
              {' '}
              <span className="buy__saved">
                ({formatPrice(receipt.list_price)} less {offer?.percent}% with {receipt.discount_code})
              </span>
            </>
          )}
          .
        </p>
        {receipt.stars ? (
          <p className="buy__rated">
            You rated it {'★'.repeat(receipt.stars)}
            <span className="buy__rated-dim">{'★'.repeat(5 - receipt.stars)}</span> — thank you,
            it helps the next shopper.
          </p>
        ) : (
          <p className="buy__rated">No rating given. That is quite all right.</p>
        )}
      </div>
    )
  }

  if (!open) {
    return (
      <div className="buy">
        <button
          className="btn btn--block"
          disabled={!size || product.total_stock === 0}
          onClick={() => setOpen(true)}
        >
          {product.total_stock === 0
            ? 'Sold out'
            : size
              ? `Buy in ${size}`
              : 'Choose a size to buy'}
        </button>
      </div>
    )
  }

  if (!user) {
    return (
      <div className="buy buy--join">
        <h3>Members only, for now</h3>
        <p>
          Members buy with Handsome Dan's discount &mdash; ten percent off, every
          now and then, for belonging to Yale.
        </p>
        <Link to="/create-account" className="btn btn--block">
          Create an account
        </Link>
        <Link to="/login" className="buy__quiet">
          Already a member? Log in
        </Link>
        <button className="buy__quiet buy__cancel" onClick={() => setOpen(false)}>
          Not now
        </button>
      </div>
    )
  }

  return (
    <div className="buy buy--open">
      <h3>Before we wrap it</h3>
      <p className="buy__ask">
        How would you rate the {product.name}?
      </p>

      <div className="stars" role="radiogroup" aria-label="Rate this product from 1 to 5 stars">
        {STARS.map((value) => {
          const lit = (hovered ?? stars ?? 0) >= value
          return (
            <button
              key={value}
              type="button"
              role="radio"
              aria-checked={stars === value}
              aria-label={`${value} star${value > 1 ? 's' : ''}`}
              className={lit ? 'star star--lit' : 'star'}
              onMouseEnter={() => setHovered(value)}
              onMouseLeave={() => setHovered(null)}
              onClick={() => setStars(stars === value ? null : value)}
            >
              {'★'}
            </button>
          )
        })}
        <span className="stars__label">
          {stars ? `${stars} of 5` : 'Optional'}
        </span>
      </div>

      {offer && (
        <label className="buy__discount">
          <input
            type="checkbox"
            checked={useDiscount}
            onChange={(event) => setUseDiscount(event.target.checked)}
          />
          Use Handsome Dan's {offer.percent}% code {offer.code}
        </label>
      )}

      <p className="buy__total">
        {size} &middot; {formatPrice(payable)}
        {payable !== product.price && (
          <s className="buy__was">{formatPrice(product.price)}</s>
        )}
      </p>

      {error && <p className="notice notice--error">{error}</p>}

      <div className="buy__actions">
        <button className="btn btn--block" onClick={complete} disabled={busy}>
          {busy ? 'Completing...' : 'Complete order'}
        </button>
        <button className="buy__quiet buy__cancel" onClick={() => setOpen(false)} disabled={busy}>
          Cancel
        </button>
      </div>
    </div>
  )
}
