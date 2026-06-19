import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import StatusBadge from "./StatusBadge.jsx";
import { getDocument } from "../api.js";

export default function DocumentCard({ doc, onUpdate }) {
  const navigate = useNavigate();

  // Авто-поллинг каждые 3 секунды, пока документ анализируется
  useEffect(() => {
    if (doc.status !== "analyzing") return;
    const interval = setInterval(async () => {
      try {
        const fresh = await getDocument(doc.id);
        onUpdate(fresh);
        if (fresh.status !== "analyzing") {
          clearInterval(interval);
        }
      } catch {
        // временная ошибка сети — продолжаем поллинг
      }
    }, 3000);
    return () => clearInterval(interval);
  }, [doc.status, doc.id, onUpdate]);

  return (
    <div className="card doc-card">
      <div className="doc-card-head">
        <div className="doc-name" title={doc.original_name}>
          {doc.original_name}
        </div>
        <StatusBadge kind="docType" value={doc.doc_type} />
      </div>

      <div className="doc-card-meta">
        <StatusBadge kind="docStatus" value={doc.status} />
        <span className="doc-count">Направлений: {doc.directions_count}</span>
      </div>

      {doc.status === "analyzing" && (
        <div className="doc-analyzing">
          <span className="spinner" /> Идёт анализ документа…
        </div>
      )}

      {doc.status === "error" && doc.error_message && (
        <div className="doc-error">{doc.error_message}</div>
      )}

      {doc.status === "done" && (
        <button
          className="btn btn-secondary"
          onClick={() => navigate(`/directions?doc_id=${doc.id}`)}
        >
          Смотреть направления
        </button>
      )}
    </div>
  );
}
