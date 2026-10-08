import { Link } from 'react-router-dom'
import HandsomeDan from '../components/HandsomeDan'

// yalebulldogblue.com has no About page to borrow a voice from, so this one is
// written from scratch in the same register as the rest of the site.
export default function About() {
  return (
    <>
      <section className="page-hero page-hero--dan">
        <div className="page-hero__copy">
          <span className="eyebrow eyebrow--light">Who we are</span>
          <h1>About Campus Customs</h1>
          <p>A print shop that happens to sell clothes, in a town that happens to have a university.</p>
        </div>
        <div className="page-hero__dan">
          <HandsomeDan size={132} waving />
        </div>
      </section>

      <div className="page page--narrow">
        <div className="prose">
          <h2>We Started With One Press</h2>
          <p>
            Campus Customs began the unglamorous way: a single press, a back room in New Haven,
            and an order for intramural shirts that had to be ready by Friday. It was ready by
            Friday. That is more or less the whole origin story, and it is still how we work.
          </p>
          <p>
            Since then we have printed for residential colleges, club teams, a cappella groups,
            reunion weekends, and a great many parents who wanted the word YALE across their
            chest before the drive home. The orders changed. The Friday deadline did not.
          </p>

          <h2>What Licensed Actually Means</h2>
          <p>
            Yale lets very few shops put its name on a garment, and we are one of them. That
            matters less for the paperwork than for what it rules out. No approximated shade of
            blue. No bulldog that is legally distinct from Handsome Dan. If a mark is on our
            shirt, it is the mark the University approved.
          </p>

          <h2>How We Pick the Rack</h2>
          <p>
            We do not carry everything. We carry what survives a New Haven winter and a
            laundry room with three working machines. Heavyweight fleece over thin fleece,
            cotton that keeps its shape, zips that still run in March. When a garment comes
            back to us pilled after one season, it comes off the rack.
          </p>
          <p>
            The result is a catalogue that is deliberately narrower than it could be: hoodies,
            crewnecks, tees, quarter-zips and jackets, in Yale blue and the greys that go with
            it. If you want it in neon, we are the wrong shop.
          </p>

          <h2>The Shop Assistant</h2>
          <p>
            The chat panel in the corner is staffed by a program, and we would rather say so
            than let you find out. It can read our catalogue and our stock counts, so it knows
            what is genuinely on the shelf in your size. It does not know your order history,
            and it will not pretend to. When it cannot answer, it says so and we pick it up.
          </p>

          <h2>Come In</h2>
          <p>
            The website is the whole catalogue, but a hood sits differently on different
            shoulders, and no photograph has ever settled a sizing argument. If you are near
            campus, come try it on.
          </p>
        </div>

        <div className="about__cta">
          <Link to="/products" className="btn">
            Browse the catalogue
          </Link>
          <Link to="/create-account" className="btn btn--ghost">
            Create an account
          </Link>
        </div>
      </div>
    </>
  )
}
