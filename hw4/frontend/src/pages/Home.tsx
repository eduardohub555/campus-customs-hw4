import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { fetchProducts } from '../api'
import ProductCard from '../components/ProductCard'
import HandsomeDan from '../components/HandsomeDan'
import type { Product } from '../types'

// Yale Club NYC runs a slow rotating hero. Three catalogue photos stand in for
// the carousel so the home page shows real stock rather than stock photography.
const HERO_IMAGES = [
  '/media/products/basic-hoodie-big-yale.jpg',
  '/media/products/2025-yale-vs-harvard-t-shirt.jpg',
  '/media/products/baseball-left-chest-crewneck.jpg',
]

const PILLARS = [
  {
    title: 'The Real Blue',
    body: 'Every garment carries the marks Yale actually approved. When you wear it, nobody has to wonder whether it is the real thing — and neither do you.',
  },
  {
    title: 'Your Corner of Campus',
    body: 'Branford to Pauli Murray, every varsity team, every graduate school. Whatever you belong to here, there is something with your name on it.',
  },
  {
    title: 'Made to Be Lived In',
    body: 'Heavyweight fleece, honest cotton, seams that outlast a February on Elm Street. The one you reach for first, for years.',
  },
]

export default function Home() {
  const [slide, setSlide] = useState(0)
  const [featured, setFeatured] = useState<Product[]>([])

  useEffect(() => {
    const timer = setInterval(() => setSlide((n) => (n + 1) % HERO_IMAGES.length), 5000)
    return () => clearInterval(timer)
  }, [])

  useEffect(() => {
    fetchProducts()
      .then((all) => setFeatured(all.filter((p) => p.total_stock > 0).slice(0, 4)))
      .catch(() => setFeatured([]))
  }, [])

  return (
    <>
      <section className="hero">
        {HERO_IMAGES.map((src, index) => (
          <div
            key={src}
            className={index === slide ? 'hero__slide hero__slide--on' : 'hero__slide'}
            style={{ backgroundImage: `url(${src})` }}
          />
        ))}
        <div className="hero__scrim" />
        <div className="hero__copy">
          <span className="eyebrow eyebrow--light">Est. in New Haven</span>
          <h1>Wear the Blue You Earned</h1>
          <p>
            You worked for this one. Yale apparel for the students who live here, the parents
            who come back, and the alumni who never quite left.
          </p>
          <Link to="/products" className="btn btn--light">
            Find yours
          </Link>
        </div>
        <div className="hero__dots">
          {HERO_IMAGES.map((src, index) => (
            <button
              key={src}
              className={index === slide ? 'hero__dot hero__dot--on' : 'hero__dot'}
              onClick={() => setSlide(index)}
              aria-label={`Show slide ${index + 1}`}
            />
          ))}
        </div>
      </section>

      <section className="band band--statement">
        <div className="band__dan">
          <HandsomeDan size={84} waving />
        </div>
        <p>
          A block from Old Campus, we have spent decades putting Yale on cotton and fleece.
          Not souvenirs &mdash; the jumper you live in, for the people who actually walk
          these streets.
        </p>
        <span className="band__sign">&mdash; Handsome Dan, keeping an eye on the door</span>
      </section>

      <section className="section">
        <div className="section__head">
          <span className="eyebrow">Why Campus Customs</span>
          <h2>Why People Keep Coming Back</h2>
        </div>
        <div className="pillars">
          {PILLARS.map((pillar) => (
            <article key={pillar.title} className="pillar">
              <h3>{pillar.title}</h3>
              <p>{pillar.body}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="section section--tint">
        <div className="section__head">
          <span className="eyebrow">Shop by category</span>
          <h2>What Are You Reaching For?</h2>
        </div>
        <div className="categories">
          {['Hoodies', 'Sweatshirts', 'T-Shirts', 'Quarter-Zips', 'Jackets'].map((category) => (
            <Link key={category} to={`/products?category=${encodeURIComponent(category)}`}>
              {category}
            </Link>
          ))}
        </div>
      </section>

      {featured.length > 0 && (
        <section className="section">
          <div className="section__head">
            <span className="eyebrow">On the shelf today</span>
            <h2>Handsome Dan&rsquo;s Picks</h2>
          </div>
          <div className="grid">
            {featured.map((product) => (
              <ProductCard key={product.product_id} product={product} />
            ))}
          </div>
          <div className="section__foot">
            <Link to="/products" className="btn">
              See everything we have
            </Link>
          </div>
        </section>
      )}

      <section className="band band--navy">
        <HandsomeDan size={96} waving />
        <h2>Come by the Store</h2>
        <p>
          Everything is here online, but a hood sits differently on different shoulders.
          The lights are on most days until six, and Dan is usually by the door.
        </p>
        <Link to="/about" className="btn btn--light">
          About us
        </Link>
      </section>
    </>
  )
}
