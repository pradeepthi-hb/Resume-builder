import React, { useContext, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { AuthContext } from "../auth/AuthContext";

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


  const styles = {
    header: {
      display: "flex",
      justifyContent: "space-between",
      alignItems: "center",
      padding: "15px 40px",
      backgroundColor: "#CBD5E1",
      color: "#334155",
      position: "relative"
    },
    logoText: {
      color: "#0F172A",
      textDecoration: "none",
      fontSize: "20px",
      fontWeight: "700"
    },
    nav: {
      display: "flex",
   
      gap: "20px",
      alignItems: "center",
      
    },
    link: {
      color: "#334155",
      textDecoration: "none"
    },
    button: {
      backgroundColor: "#DC2626",
      color: "white",
      border: "none",
      padding: "6px 12px",
      cursor: "pointer",
     
    }
  };

  return (
    <> 
      <style>
      {`
      .nav {
        display: flex;
        gap: 20px;
        align-items: center;
      }

      .hamburger {
        display: none;
      }

      @media (max-width: 768px) {

        .hamburger {
          display: block;
          font-size: 24px;
          cursor: pointer;
          color: white;
        }

        .nav {
          display: none;
          position: absolute;
          top: 60px;
          right: 20px;
          flex-direction: column;
          background: #1f2937;
          padding: 20px;
          gap: 15px;
          border-radius: 10px;
          width: 220px;
          box-shadow: 0 10px 25px rgba(0,0,0,0.3);
          z-index: 999;
        }

        .nav.open {
          display: flex;
        }
      }
      `}
      </style>
    <header style={styles.header}>
      <div style={styles.logo}>
        <Link to="/" style={styles.logoText}>
          Resume Builder
        </Link>
      </div>

      <div
        className="hamburger"
        onClick={() => setMenuOpen(!menuOpen)}
      >
        {menuOpen ? "✕" : "☰"}
      </div>

      <nav className={`nav ${menuOpen ? "open" : ""}`}
     >
        {isHireyoMode ? (
          <>
            {returnUrl ? (
              <a href={returnUrl} style={styles.link}>Return to Hireyo</a>
            ) : null}
          </>
        ) : token ? (
          <>
            <Link to="/" style={styles.link}>Dashboard</Link>
            <Link to="/resume/new" style={styles.link}>New Resume</Link>
            <button onClick={handleLogout} style={styles.button}>
              Logout
            </button>
          </>
        ) : (
          <>
            <Link to="/login" style={styles.link}>Login</Link>
            <Link to="/register" style={styles.link}>Register</Link>
          </>
        )}
      </nav>
    </header>
    </>
  );
}



export default Header;
