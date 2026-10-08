import { useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth'

export default function Login() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  // Send people back where they came from, or home.
  const next = (location.state as { from?: string } | null)?.from ?? '/'

  async function submit(event: React.FormEvent) {
    event.preventDefault()
    setError(null)
    setBusy(true)
    try {
      await login(email, password)
      navigate(next, { replace: true })
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : 'Could not sign in.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="page page--form">
      <div className="formcard">
        <span className="eyebrow">Returning customer</span>
        <h1>Log In</h1>
        <p className="formcard__lede">
          Sign in to use Handsome Dan's member discount.
        </p>

        <form onSubmit={submit}>
          <label>
            Email
            <input
              type="email"
              required
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="you@yale.edu"
              autoComplete="email"
            />
          </label>
          <label>
            Password
            <input
              type="password"
              required
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              autoComplete="current-password"
            />
          </label>
          <button type="submit" className="btn btn--block" disabled={busy}>
            {busy ? 'Signing in...' : 'Log in'}
          </button>
        </form>

        {error && (
          <p className="notice notice--error" role="alert">
            {error}
          </p>
        )}

        <p className="formcard__foot">
          No account yet? <Link to="/create-account">Create one</Link>.
        </p>
      </div>
    </div>
  )
}
