import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import StatusBadge from "./StatusBadge.jsx";
import { deleteDocument, getDocument } from "../api.js";

export default function DocumentCard({ doc, onUpdate, onDelete }) {
  const navigate = useNavigate();
  const [deleting, setDeleting] = useState(false);

  const handleDelete = async (e) => {
    e.stopPropagation();
    if (!confirm(`Удалить «${doc.original_name}»?`)) return;
    setDeleting(true);
    try {
      await deleteDocument(doc.id);
      onDelete(doc.id);
    } catch {
      setDeleting(false);
    }
  };

  useEffect(() => {
    if (doc.status !== "analyzing") return;
    const interval = setInterval(async () => {
      try {
        const fresh = await getDocument(doc.id);
        onUpdate(fresh);
        if (fresh.status !== "analyzing") clearInterval(interval);
      } catch {}
    }, 3000);
    return () => clearInterval(interval);
  }, [doc.status, doc.id, onUpdate]);

  const ext = doc.original_name?.split(".").pop()?.toUpperCase() || "—";

  return (
    <div className="card doc-card">
      <div className="doc-card-body">
        <div className="doc-card-head">
          <div className="doc-name" title={doc.original_name}>
            {doc.original_name}
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 6, flexShrink: 0 }}>
            <StatusBadge kind="docType" value={doc.doc_type} />
            <button
              className="doc-delete-btn"
              onClick={handleDelete}
              disabled={deleting}
              title="Удалить документ"
            >
              {deleting ? "…" : "×"}
            </button>
          </div>
        </div>

        <div className="doc-card-meta">
          <StatusBadge kind="docStatus" value={doc.status} />
          <span className="doc-count">
            {doc.directions_count > 0
              ? `${doc.directions_count} направл.`
              : "Нет направлений"}
          </span>
        </div>

        {doc.status === "analyzing" && (
          <div className="doc-analyzing">
            <span className="spinner" />
            Анализируется…
          </div>
        )}

        {doc.status === "error" && doc.error_message && (
          <div className="doc-error">{doc.error_message}</div>
        )}
      </div>

      {doc.status === "done" && doc.directions_count > 0 && (
        <div className="doc-card-footer">
          <button
            className="btn btn-secondary btn-sm"
            style={{ width: "100%" }}
            onClick={() => navigate(`/directions?doc_id=${doc.id}`)}
          >
            Смотреть направления →
          </button>
        </div>
      )}
    </div>
  );
}
