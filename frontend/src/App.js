import { BrowserRouter as Router, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, AuthContext } from "./auth/AuthContext";
import Login from "./pages/Login";
import Register from "./pages/Register";
import ResumeForm from "./pages/ResumeForm";
import { useContext } from "react";
import Dashboard from "./pages/Dashboard";
import Header from "./components/Header";
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
            element={<ResumeForm key="hireyo" />}
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
