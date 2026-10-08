import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useLocation } from 'react-router-dom'
import { Link } from 'react-router-dom'
import { fetchChatHistory, fetchDiscount, noteDiscountInterest, sendChatMessage } from '../api'
import { useAuth } from '../auth'
import { useChatResults } from '../chatResults'
import HandsomeDan from './HandsomeDan'
import type { DiscountOffer, PageContext } from '../types'

interface Message {
  role: 'user' | 'assistant'
  content: string
  /** How many products this answer put on the page, for the inline note. */
  shown?: number
}

/** Exactly as specified: named for a signed-in shopper, general for a guest. */
const greetingFor = (firstName?: string): Message => ({
  role: 'assistant',
  content: firstName
    ? `Hi ${firstName}. Welcome back to Campus Customs — ask us about a garment, a colour or a size.`
    : 'Welcome to Yale Campus Customs. Ask us about a garment, a colour or a size.',
})

export default function ChatWidget() {
  const { user } = useAuth()
  const { show: showResults, clear: clearResults } = useChatResults()
  const location = useLocation()
  const [open, setOpen] = useState(false)
  const [messages, setMessages] = useState<Message[]>([greetingFor()])
  const [draft, setDraft] = useState('')
  const [thinking, setThinking] = useState(false)
  const [restored, setRestored] = useState(false)
  const [offer, setOffer] = useState<DiscountOffer | null>(null)
  const [danSays, setDanSays] = useState<string | null>(null)
  const [interestNoted, setInterestNoted] = useState(false)
  const scrollRef = useRef<HTMLDivElement>(null)

  /**
   * The page the shopper is reading, sent with every message so that "do you
   * have this in pink?" has a referent. Derived from the URL, so it is always
   * what they are actually looking at.
   */
  const page: PageContext = useMemo(() => {
    const onProduct = location.pathname.match(/^\/products\/(.+)$/)
    return {
      path: location.pathname,
      product_id: onProduct ? decodeURIComponent(onProduct[1]) : null,
      category: new URLSearchParams(location.search).get('category'),
    }
  }, [location.pathname, location.search])

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages, thinking, open])

  // Reload a signed-in shopper's conversation; a guest starts fresh every time
  // because nothing was ever stored for them.
  useEffect(() => {
    let cancelled = false
    setRestored(false)

    if (!user) {
      setMessages([greetingFor()])
      setOffer(null)
      setDanSays(null)
      clearResults()
      return
    }

    // Handsome Dan's standing offer. He makes a new one every now and then —
    // the backend decides, so he cannot be farmed by reopening the panel.
    fetchDiscount()
      .then((state) => {
        if (cancelled) return
        setOffer(state.offer)
        setDanSays(state.greeting)
        setInterestNoted(Boolean(state.offer?.interested_at))
      })
      .catch(() => undefined)

    fetchChatHistory()
      .then((history) => {
        if (cancelled) return
        const prior: Message[] = history.turns.map((turn) => ({
          role: turn.role,
          content: turn.content,
          shown: turn.products.length || undefined,
        }))
        setMessages([greetingFor(user.first_name), ...prior])
        setRestored(prior.length > 0)
      })
      .catch(() => {
        if (!cancelled) setMessages([greetingFor(user.first_name)])
      })

    return () => {
      cancelled = true
    }
  }, [user?.id, clearResults])

  const submit = useCallback(
    async (event: React.FormEvent) => {
      event.preventDefault()
      const text = draft.trim()
      if (!text || thinking) return

      setMessages((prev) => [...prev, { role: 'user', content: text }])
      setDraft('')
      setThinking(true)
      try {
        const reply = await sendChatMessage(text, page)
        setMessages((prev) => [
          ...prev,
          { role: 'assistant', content: reply.reply, shown: reply.products.length || undefined },
        ])

        // Matches go to the page, not into the conversation. The panel stays
        // open — it sits in the corner, the band runs full width at the top.
        if (reply.products.length > 0) {
          showResults({
            title: reply.result_title ?? 'From your conversation',
            query: text,
            products: reply.products,
          })
        } else {
          clearResults()
        }
      } catch {
        setMessages((prev) => [
          ...prev,
          { role: 'assistant', content: "We couldn't reach the shop just now. Please try again." },
        ])
      } finally {
        setThinking(false)
      }
    },
    [draft, thinking, page, showResults, clearResults],
  )

  return (
    <div className="chat">
      {open && (
        <section className="chat__panel" aria-label="Shop assistant">
          <header className="chat__header">
            <div>
              <strong>Shop Assistant</strong>
              <span>Campus Customs</span>
            </div>
            <button onClick={() => setOpen(false)} aria-label="Close chat">
              &times;
            </button>
          </header>

          <div className="chat__log" ref={scrollRef}>
            <div className="chat__dan">
              <HandsomeDan size={64} waving />
              <div className="chat__dan-words">
                <strong>Handsome Dan</strong>
                {user ? (
                  <span>
                    {danSays ?? `Good to see you again, ${user.first_name}.`}
                  </span>
                ) : (
                  <span>
                    Welcome in. Members get a discount from me every now and then
                    &mdash; ten percent off, just for being one of ours.
                  </span>
                )}
              </div>
            </div>

            {!user && (
              <div className="chat__join">
                <Link to="/create-account" className="btn btn--block" onClick={() => setOpen(false)}>
                  Join for member discounts
                </Link>
                <Link to="/login" onClick={() => setOpen(false)}>
                  Already a member? Log in
                </Link>
              </div>
            )}

            {user && offer && (
              <div className="perk">
                <span className="perk__badge">{offer.percent}% off</span>
                <p className="perk__code">
                  Your code: <strong>{offer.code}</strong>
                </p>
                {interestNoted ? (
                  <p className="perk__noted">Noted — we will keep it in mind.</p>
                ) : (
                  <button
                    className="perk__more"
                    onClick={() => {
                      setInterestNoted(true)
                      void noteDiscountInterest()
                    }}
                  >
                    Tell me more
                  </button>
                )}
              </div>
            )}

            {restored && <p className="chat__restored">Your previous conversation</p>}
            {messages.map((message, index) => (
              <div key={index} className="chat__turn">
                <p className={`chat__msg chat__msg--${message.role}`}>{message.content}</p>
                {Boolean(message.shown) && (
                  <p className="chat__shown">
                    {message.shown === 1
                      ? '1 garment shown on the page.'
                      : `${message.shown} garments shown on the page.`}
                  </p>
                )}
              </div>
            ))}
            {thinking && (
              <p className="chat__msg chat__msg--assistant chat__typing">
                <span />
                <span />
                <span />
              </p>
            )}
          </div>

          <form className="chat__form" onSubmit={submit}>
            <input
              value={draft}
              onChange={(event) => setDraft(event.target.value)}
              placeholder="What hoodies do you have?"
              aria-label="Message the shop assistant"
            />
            <button type="submit" disabled={!draft.trim() || thinking}>
              Send
            </button>
          </form>
        </section>
      )}

      <button
        className="chat__launcher"
        onClick={() => setOpen(!open)}
        aria-label={open ? 'Close shop assistant' : 'Open shop assistant'}
      >
        {open ? '×' : 'Ask us'}
      </button>
    </div>
  )
}
