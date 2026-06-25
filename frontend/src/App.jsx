import { Link, Route, Routes, useLocation } from "react-router-dom";
import DocumentsPage from "./pages/DocumentsPage.jsx";
import DocumentDetailPage from "./pages/DocumentDetailPage.jsx";

export default function App() {
  const location = useLocation();
  const isDocuments = location.pathname === "/" || location.pathname.startsWith("/documents");

  return (
    <div className="app">
      <header className="header">
        <div className="header-inner">
          <Link to="/" className="logo">
            <div className="logo-icon">◆</div>
            <span className="logo-text">Кристалл<span className="logo-accent">.НТР</span></span>
          </Link>
          <nav className="nav">
            <Link className={isDocuments ? "nav-link active" : "nav-link"} to="/">
              Документы
            </Link>
          </nav>
        </div>
      </header>
      <main className="main">
        <Routes>
          <Route path="/" element={<DocumentsPage />} />
          <Route path="/documents/:id" element={<DocumentDetailPage />} />
        </Routes>
      </main>
    </div>
  );
}
