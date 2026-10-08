import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth'

// Mirrors the checks in backend/auth.py. The backend re-runs all of them; this
// only lets the shopper see what is still missing as they type.
const RULES: { label: string; test: (value: string) => boolean }[] = [
  { label: 'At least 8 characters', test: (value) => value.length >= 8 },
  { label: 'At least one number', test: (value) => /\d/.test(value) },
  {
    label: 'At least one special character, such as a period',
    test: (value) => /[^A-Za-z0-9\s]/.test(value),
  },
]

const EMPTY = {
  first_name: '',
  last_name: '',
  email: '',
  password: '',
  confirm_password: '',
}

export default function CreateAccount() {
  const { register } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState(EMPTY)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const update = (field: keyof typeof form) => (event: React.ChangeEvent<HTMLInputElement>) =>
    setForm({ ...form, [field]: event.target.value })

  // Compared exactly, so a difference in capitalisation is a mismatch. The
  // backend checks this again; this only saves a round trip.
  const mismatch =
    form.confirm_password.length > 0 && form.password !== form.confirm_password

  const unmetRule = RULES.find((rule) => !rule.test(form.password))

  async function submit(event: React.FormEvent) {
    event.preventDefault()
    setError(null)
    if (mismatch) {
      setError('The two passwords do not match.')
      return
    }
    if (unmetRule) {
      setError(`Password needs: ${unmetRule.label.toLowerCase()}.`)
      return
    }
    setBusy(true)
    try {
      await register(form)
      navigate('/', { replace: true })
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : 'Could not create the account.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="page page--form">
      <div className="formcard">
        <span className="eyebrow">New here</span>
        <h1>Create Account</h1>
        <p className="formcard__lede">
          Members get a discount from Handsome Dan every now and then &mdash; ten
          percent off, for belonging to Yale.
        </p>

        <form onSubmit={submit}>
          <div className="formcard__row">
            <label>
              First name
              <input
                required
                value={form.first_name}
                onChange={update('first_name')}
                autoComplete="given-name"
              />
            </label>
            <label>
              Last name
              <input
                required
                value={form.last_name}
                onChange={update('last_name')}
                autoComplete="family-name"
              />
            </label>
          </div>

          <label>
            Email
            <input
              type="email"
              required
              value={form.email}
              onChange={update('email')}
              placeholder="you@yale.edu"
              autoComplete="email"
            />
          </label>

          <label>
            Password
            <input
              type="password"
              required
              minLength={8}
              value={form.password}
              onChange={update('password')}
              autoComplete="new-password"
            />
            <ul className="rules">
              {RULES.map((rule) => (
                <li
                  key={rule.label}
                  className={rule.test(form.password) ? 'rules__met' : undefined}
                >
                  {rule.label}
                </li>
              ))}
            </ul>
            <small>Capitalisation counts.</small>
          </label>

          <label>
            Confirm password
            <input
              type="password"
              required
              value={form.confirm_password}
              onChange={update('confirm_password')}
              autoComplete="new-password"
              aria-invalid={mismatch}
            />
            {mismatch && <small className="mismatch">The two passwords do not match.</small>}
          </label>

          <button
            type="submit"
            className="btn btn--block"
            disabled={busy || mismatch || Boolean(unmetRule)}
          >
            {busy ? 'Creating account...' : 'Create account'}
          </button>
        </form>

        {error && (
          <p className="notice notice--error" role="alert">
            {error}
          </p>
        )}

        <p className="formcard__foot">
          Already have an account? <Link to="/login">Log in</Link>.
        </p>
      </div>
    </div>
  )
}
