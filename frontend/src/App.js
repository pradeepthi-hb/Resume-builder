import { BrowserRouter as Router, Routes, Route, Navigate, useLocation } from "react-router-dom";
import { AuthProvider, AuthContext } from "./auth/AuthContext";
import Login from "./pages/Login";
import Register from "./pages/Register";
import ResumeForm from "./pages/ResumeForm";
import { useContext, useEffect, useState } from "react";
import Dashboard from "./pages/Dashboard";
import Header from "./components/Header";
import api from "./api/axios";
import { ToastContainer } from "react-toastify";
import "react-toastify/dist/ReactToastify.css";
import "./theme.css";

function ProtectedRoute({ children }) {
  const { token } = useContext(AuthContext);
  return token ? children : <Navigate to="/login" />;
}

function PublicRoute({ children }) {
  const { token } = useContext(AuthContext);
  return token ? <Navigate to="/" /> : children;
}

const toHttpUrl = (value) => {
  try {
    const url = new URL(value || "");
    return /^https?:$/.test(url.protocol) ? url.toString() : null;
  } catch {
    return null;
  }
};

const firstValidUrl = (query, keys) => keys.map((k) => toHttpUrl(query.get(k))).find(Boolean);

const parseBoolLike = (value) => {
  if (typeof value === "boolean") return value;
  const text = String(value ?? "").trim().toLowerCase();
  if (["1", "true", "yes", "y", "on"].includes(text)) return true;
  if (["0", "false", "no", "n", "off"].includes(text)) return false;
  return null;
};

function buildHireyoRedirectTargets(search) {
  const query = new URLSearchParams(search);
  const returnUrl = toHttpUrl(query.get("return_url"));
  const fromReturn = (path) => (returnUrl ? new URL(path, returnUrl).toString() : null);

  return {
    login: firstValidUrl(query, ["hireyo_login_url", "login_url"]) || fromReturn("/login") || "/login",
    companyDashboard:
      firstValidUrl(query, ["hireyo_company_dashboard_url", "company_dashboard_url"]) ||
      returnUrl ||
      fromReturn("/dashboard") ||
      "/",
  };
}

function IntegrationRouteGuard({ children }) {
  const { token, logout } = useContext(AuthContext);
  const location = useLocation();
  const [redirectTarget, setRedirectTarget] = useState(undefined);

  useEffect(() => {
    let active = true;
    const query = new URLSearchParams(location.search);
    const launchToken = (query.get("token") || "").trim();
    const queryCandidateEmail = (query.get("candidate_email") || "").trim().toLowerCase();
    const { login, companyDashboard } = buildHireyoRedirectTargets(location.search);
    const finish = (target, shouldLogout = false) => {
      if (!active) return;
      if (shouldLogout) logout();
      setRedirectTarget(target);
    };

    (async () => {
      if (!launchToken) return finish(login);

      let launchCandidateEmail = queryCandidateEmail;
      let launchRole = "";
      let launchIsVerified = true;
      try {
        const sessionRes = await api.get(`/integrations/hireyo/session${location.search}`);
        const sessionData = sessionRes?.data || {};
        launchCandidateEmail = String(
          sessionData.candidate_email || launchCandidateEmail || ""
        ).trim().toLowerCase();
        launchRole = String(
          sessionData.launch_role ||
          query.get("role") ||
          query.get("candidate_role") ||
          query.get("user_role") ||
          ""
        ).trim().toLowerCase();
        if (!launchRole && launchCandidateEmail) {
          launchRole = "candidate";
        }
        const verifiedFromSession = parseBoolLike(sessionData.launch_is_verified);
        const verifiedFromQuery = parseBoolLike(
          query.get("is_verified") ||
          query.get("verified") ||
          query.get("candidate_verified") ||
          query.get("user_verified")
        );
        launchIsVerified =
          verifiedFromSession !== null
            ? verifiedFromSession
            : verifiedFromQuery !== null
              ? verifiedFromQuery
              : true;
      } catch {
        return finish(login, true);
      }

      // In Hireyo integration mode, launch session identity is authoritative.
      if (!launchIsVerified) return finish(login, true);
      if (launchRole === "company") return finish(companyDashboard, true);
      if (launchRole === "candidate") {
        // Optional hygiene: clear mismatched local RB token, but do not block launch access.
        if (token && launchCandidateEmail) {
          try {
            const response = await api.get("/auth/me", {
              headers: { Authorization: `Bearer ${token}` },
            });
            const userEmail = String(response?.data?.email || "").trim().toLowerCase();
            if (userEmail && userEmail !== launchCandidateEmail) {
              logout();
            }
          } catch {
            logout();
          }
        }
        return finish(null);
      }

      return finish(login, true);
    })();

    return () => {
      active = false;
    };
  }, [token, logout, location.search]);

  if (redirectTarget === undefined) return null;
  if (redirectTarget) {
    if (redirectTarget.startsWith("http://") || redirectTarget.startsWith("https://")) {
      window.location.replace(redirectTarget);
      return null;
    }
    return <Navigate to={redirectTarget} replace />;
  }
  return children;
}

export default function App() {
  return (
    <AuthProvider>
      <Router>
        <Header/>
        <Routes>
          {/* Public routes */}
          <Route
            path="/login"
            element={
              <PublicRoute>
                <Login />
              </PublicRoute>
            }
          />
          <Route
            path="/register"
            element={
              <PublicRoute>
                <Register />
              </PublicRoute>
            }
          />

          <Route
            path="/integrations/hireyo"
            element={
              <IntegrationRouteGuard>
                <ResumeForm key="hireyo" />
              </IntegrationRouteGuard>
            }
          />

          {/* Protected route */}
          <Route
            path="/"
            element={
              <ProtectedRoute>
                <Dashboard />
              </ProtectedRoute>
            }
          />

          <Route
            path="/resume/new"
            element={
              <ProtectedRoute>
                <ResumeForm key="new" />
              </ProtectedRoute>
            }
          />

          <Route
            path="/resume/:id"
            element={
              <ProtectedRoute>
                <ResumeForm key="edit" />
              </ProtectedRoute>
            }
          />

          <Route
            path="/resume/:id/download"
            element={
              <ProtectedRoute>
                <ResumeForm key="download" />
              </ProtectedRoute>
            }
          />

          {/* Default */}
          <Route path="*" element={<Navigate to="/login" />} />
        </Routes>
        <ToastContainer
          position="top-right"
          autoClose={3000}
          hideProgressBar={false}
          newestOnTop
          closeOnClick
          pauseOnHover
          draggable
          theme="colored"
        />
      </Router>
    </AuthProvider>
  );
}
