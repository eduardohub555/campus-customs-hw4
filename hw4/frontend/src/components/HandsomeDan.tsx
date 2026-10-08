/**
 * Handsome Dan, the Yale bulldog, built from HTML and CSS.
 *
 * No image file and nothing generated: every part below is a div shaped with
 * border-radius, so he scales cleanly and costs one component to ship.
 */
export default function HandsomeDan({
  size = 72,
  waving = false,
}: {
  size?: number
  waving?: boolean
}) {
  return (
    <div
      className={waving ? 'dan dan--waving' : 'dan'}
      style={{ '--dan-size': `${size}px` } as React.CSSProperties}
      role="img"
      aria-label="Handsome Dan, the Yale bulldog"
    >
      <div className="dan__ear dan__ear--left" />
      <div className="dan__ear dan__ear--right" />
      <div className="dan__head">
        <div className="dan__brow dan__brow--left" />
        <div className="dan__brow dan__brow--right" />
        <div className="dan__eye dan__eye--left" />
        <div className="dan__eye dan__eye--right" />
        <div className="dan__muzzle">
          <div className="dan__nose" />
          <div className="dan__lip dan__lip--left" />
          <div className="dan__lip dan__lip--right" />
        </div>
      </div>
      <div className="dan__collar">
        <div className="dan__tag">Y</div>
      </div>
    </div>
  )
}
