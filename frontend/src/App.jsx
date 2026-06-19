import { Link, Route, Routes, useLocation } from "react-router-dom";
import DocumentsPage from "./pages/DocumentsPage.jsx";
import DirectionsPage from "./pages/DirectionsPage.jsx";

export default function App() {
  const location = useLocation();
  const isDirections = location.pathname.startsWith("/directions");

  return (
    <div className="app">
      <header className="header">
        <div className="header-inner">
          <div className="logo">
            <span className="logo-mark">◆</span> Кристалл<span className="logo-accent">.НТР</span>
          </div>
          <nav className="nav">
            <Link className={!isDirections ? "nav-link active" : "nav-link"} to="/">
              Документы
            </Link>
            <Link
              className={isDirections ? "nav-link active" : "nav-link"}
              to="/directions"
            >
              Направления
            </Link>
          </nav>
        </div>
      </header>
      <main className="main">
        <Routes>
          <Route path="/" element={<DocumentsPage />} />
          <Route path="/directions" element={<DirectionsPage />} />
        </Routes>
      </main>
    </div>
  );
}
