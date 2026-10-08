import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'

export interface User {
  id: number
  name: string
  email: string
  first_name: string
  last_name: string
  created_at: string
}

interface AuthState {
  user: User | null
  ready: boolean
  login: (email: string, password: string) => Promise<void>
  register: (fields: RegisterFields) => Promise<void>
  logout: () => Promise<void>
}

export interface RegisterFields {
  first_name: string
  last_name: string
  email: string
  password: string
  confirm_password: string
}

const TOKEN_KEY = 'campus-customs-token'
const AuthContext = createContext<AuthState | null>(null)

/** Turn a FastAPI error response into the sentence the form should show. */
async function readError(response: Response): Promise<string> {
  try {
    const body = await response.json()
    if (typeof body.detail === 'string') return body.detail
  } catch {
    /* fall through to the generic message */
  }
  return 'Something went wrong. Please try again.'
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [ready, setReady] = useState(false)

  // Restore the session on load. A token from a previous server run no longer
  // resolves, so it is cleared rather than left to fail on every request.
  useEffect(() => {
    const token = localStorage.getItem(TOKEN_KEY)
    if (!token) {
      setReady(true)
      return
    }
    fetch('/api/auth/me', { headers: { Authorization: `Bearer ${token}` } })
      .then(async (response) => {
        if (!response.ok) throw new Error('stale token')
        const body = await response.json()
        setUser(body.user)
      })
      .catch(() => localStorage.removeItem(TOKEN_KEY))
      .finally(() => setReady(true))
  }, [])

  const authenticate = useCallback(async (path: string, payload: unknown) => {
    const response = await fetch(path, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
    if (!response.ok) throw new Error(await readError(response))
    const body = await response.json()
    localStorage.setItem(TOKEN_KEY, body.token)
    setUser(body.user)
  }, [])

  const login = useCallback(
    (email: string, password: string) => authenticate('/api/auth/login', { email, password }),
    [authenticate],
  )

  const register = useCallback(
    (fields: RegisterFields) => authenticate('/api/auth/register', fields),
    [authenticate],
  )

  const logout = useCallback(async () => {
    const token = localStorage.getItem(TOKEN_KEY)
    localStorage.removeItem(TOKEN_KEY)
    setUser(null)
    if (token) {
      await fetch('/api/auth/logout', {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      }).catch(() => undefined)
    }
  }, [])

  const value = useMemo(
    () => ({ user, ready, login, register, logout }),
    [user, ready, login, register, logout],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthState {
  const context = useContext(AuthContext)
  if (!context) throw new Error('useAuth must be used inside AuthProvider')
  return context
}

/** The token, for callers outside React (the chat panel in Problem 5). */
export const readToken = () => localStorage.getItem(TOKEN_KEY)
