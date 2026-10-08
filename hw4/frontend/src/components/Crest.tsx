/** Campus Customs mark. Drawn in CSS/SVG rather than shipped as an image. */
export default function Crest({ size = 34 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 40 46" aria-hidden="true" className="crest">
      <path
        d="M2 2h36v26c0 9-9 14-18 16C11 42 2 37 2 28V2z"
        fill="currentColor"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinejoin="round"
      />
      <path d="M2 2h36v26c0 9-9 14-18 16C11 42 2 37 2 28V2z" fill="none" stroke="#c9b273" strokeWidth="1.5" />
      <text
        x="20"
        y="27"
        textAnchor="middle"
        fontFamily="Georgia, 'Times New Roman', serif"
        fontSize="19"
        fontWeight="700"
        fill="#ffffff"
      >
        CC
      </text>
    </svg>
  )
}
