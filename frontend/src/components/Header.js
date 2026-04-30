import React, { useContext, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { AuthContext } from "../auth/AuthContext";
import "./Header.css";

function Header() {
  const { token, logout } = useContext(AuthContext);
  const navigate = useNavigate();
  const location = useLocation();
  const [menuOpen, setMenuOpen] = useState(false);
  const isHireyoMode = location.pathname.startsWith("/integrations/hireyo");
  const returnUrl = new URLSearchParams(location.search).get("return_url");

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <header className="app-header">
      <div className="app-logo">
        <Link to="/" className="app-logo-text">
          Resume Builder
        </Link>
      </div>

      <button
        type="button"
        className="menu-toggle"
        onClick={() => setMenuOpen(!menuOpen)}
        aria-label="Toggle navigation menu"
      >
        {menuOpen ? "Close" : "Menu"}
      </button>

      <nav className={`app-nav ${menuOpen ? "open" : ""}`}>
        {isHireyoMode ? (
          <>
            {returnUrl ? (
              <a href={returnUrl} className="app-nav-link">Return to Hireyo</a>
            ) : null}
          </>
        ) : token ? (
          <>
            <Link to="/" className="app-nav-link">Dashboard</Link>
            <Link to="/resume/new" className="app-nav-link">New Resume</Link>
            <button onClick={handleLogout} className="app-logout-btn">
              Logout
            </button>
          </>
        ) : (
          <>
            <Link to="/login" className="app-nav-link">Login</Link>
            <Link to="/register" className="app-nav-link">Register</Link>
          </>
        )}
      </nav>
    </header>
  );
}

export default Header;
