import { Link } from 'react-router-dom'
import Crest from './Crest'
import HandsomeDan from './HandsomeDan'

export default function Footer() {
  return (
    <footer className="footer">
      <div className="footer__inner">
        <div className="footer__brand">
          <div className="footer__mark">
            <Crest size={36} />
            <HandsomeDan size={46} />
          </div>
          <p>
            Campus Customs has dressed Yale students, parents and alumni from a storefront in
            New Haven for longer than most undergraduates have been alive. Come and be one of
            them.
          </p>
        </div>

        <div className="footer__col">
          <h4>Shop</h4>
          <Link to="/products">All products</Link>
          <Link to="/products?category=Hoodies">Hoodies</Link>
          <Link to="/products?category=Sweatshirts">Sweatshirts</Link>
          <Link to="/products?category=T-Shirts">T-Shirts</Link>
        </div>

        <div className="footer__col">
          <h4>Visit</h4>
          <Link to="/about">About us</Link>
          <Link to="/login">Log in</Link>
          <Link to="/create-account">Create account</Link>
        </div>
      </div>
      <div className="footer__rule" />
      <p className="footer__note">
        A course project for MGT 409 &middot; Yale School of Management. Not affiliated with
        Yale University.
      </p>
    </footer>
  )
}
