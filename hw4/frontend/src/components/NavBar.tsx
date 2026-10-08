import { NavLink, Link } from 'react-router-dom'
import { useState } from 'react'
import Crest from './Crest'
import { useAuth } from '../auth'

const PAGES = [
  { to: '/', label: 'Home', end: true },
  { to: '/products', label: 'Products' },
  { to: '/about', label: 'About Us' },
]

export default function NavBar() {
  const { user, logout } = useAuth()
  const [open, setOpen] = useState(false)
  const close = () => setOpen(false)

  return (
    <header className="nav">
      <div className="nav__inner">
        <Link to="/" className="nav__brand" onClick={close}>
          <Crest />
          <span className="nav__brand-text">
            <strong>Campus Customs</strong>
            <em>New Haven, Connecticut</em>
          </span>
        </Link>

        <button
          className="nav__toggle"
          aria-expanded={open}
          aria-label="Toggle navigation"
          onClick={() => setOpen(!open)}
        >
          <span />
          <span />
          <span />
        </button>

        <nav className={open ? 'nav__links nav__links--open' : 'nav__links'}>
          {PAGES.map((page) => (
            <NavLink
              key={page.to}
              to={page.to}
              end={page.end}
              onClick={close}
              className={({ isActive }) => (isActive ? 'nav__link nav__link--active' : 'nav__link')}
            >
              {page.label}
            </NavLink>
          ))}
          <span className="nav__divider" />
          {user ? (
            <>
              <span className="nav__user" title={user.email}>
                Hi, {user.first_name}
              </span>
              <button
                className="nav__link nav__link--quiet nav__logout"
                onClick={() => {
                  close()
                  void logout()
                }}
              >
                Log out
              </button>
            </>
          ) : (
            <>
              <NavLink to="/login" onClick={close} className="nav__link nav__link--quiet">
                Log in
              </NavLink>
              <NavLink to="/create-account" onClick={close} className="nav__cta">
                Create account
              </NavLink>
            </>
          )}
        </nav>
      </div>
    </header>
  )
}
