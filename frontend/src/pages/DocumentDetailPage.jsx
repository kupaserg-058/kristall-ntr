import { useCallback, useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import StatusBadge from "../components/StatusBadge.jsx";
import { getDocument, getDocumentDirections, updateDirectionStatus } from "../api.js";

const FEDERAL_DIRECTIONS = [
  "Высокоэффективная и ресурсосберегающая энергетика",
  "Превентивная и персонализированная медицина, обеспечение здорового долголетия",
  "Высокопродуктивное и устойчивое к изменениям природной среды сельское хозяйство",
  "Безопасность получения, хранения, передачи и обработки информации",
  "Интеллектуальные транспортные и телекоммуникационные системы, включая автономные транспортные средства",
  "Укрепление социокультурной идентичности российского общества и повышение уровня его образования",
  "Адаптация к изменениям климата, сохранение и рациональное использование природных ресурсов",
];

const FEDERAL_SHORT = {
  "Высокоэффективная и ресурсосберегающая энергетика": "Энергетика",
  "Превентивная и персонализированная медицина, обеспечение здорового долголетия": "Медицина",
  "Высокопродуктивное и устойчивое к изменениям природной среды сельское хозяйство": "Сельское хоз-во",
  "Безопасность получения, хранения, передачи и обработки информации": "Инфобезопасность",
  "Интеллектуальные транспортные и телекоммуникационные системы, включая автономные транспортные средства": "Транспорт и связь",
  "Укрепление социокультурной идентичности российского общества и повышение уровня его образования": "Образование",
  "Адаптация к изменениям климата, сохранение и рациональное использование природных ресурсов": "Климат и ресурсы",
};

const DIRECTION_COLORS = [
  { bg: "#fff7ed", border: "#fed7aa", text: "#c2410c", dot: "#f97316" },
  { bg: "#f0fdf4", border: "#bbf7d0", text: "#15803d", dot: "#22c55e" },
  { bg: "#eff6ff", border: "#bfdbfe", text: "#1d4ed8", dot: "#3b82f6" },
  { bg: "#fdf4ff", border: "#e9d5ff", text: "#7e22ce", dot: "#a855f7" },
  { bg: "#fff1f2", border: "#fecdd3", text: "#be123c", dot: "#f43f5e" },
  { bg: "#f0f9ff", border: "#bae6fd", text: "#0369a1", dot: "#0ea5e9" },
  { bg: "#f7fee7", border: "#d9f99d", text: "#3f6212", dot: "#84cc16" },
];

function DirectionItem({ direction, onChangeStatus }) {
  const [expanded, setExpanded] = useState(false);
  const fragment = direction.fragment || "";
  const isLong = fragment.length > 120;
  const shown = expanded || !isLong ? fragment : `${fragment.slice(0, 120)}…`;

  return (
    <div className="dd-item">
      <div className="dd-item-header">
        <div className="dd-item-title">{direction.title}</div>
        <div className="dd-item-meta">
          <StatusBadge kind="confidence" value={direction.confidence} />
          <StatusBadge kind="verification" value={direction.verification_status} />
          <div className="dd-actions">
            {[
              { s: "confirmed", sym: "✓", cls: "act-confirm" },
              { s: "needs_clarification", sym: "?", cls: "act-clarify" },
              { s: "rejected", sym: "✗", cls: "act-reject" },
            ].map((a) => (
              <button
                key={a.s}
                className={`act-btn ${a.cls} ${direction.verification_status === a.s ? "active" : ""}`}
                onClick={() => onChangeStatus(direction.id, a.s)}
                title={a.s}
              >
                {a.sym}
              </button>
            ))}
          </div>
        </div>
      </div>
      {fragment && (
        <div
          className={`dd-fragment ${isLong ? "clickable" : ""}`}
          onClick={() => isLong && setExpanded((v) => !v)}
        >
          «{shown}»
          {isLong && <span className="dd-expand">{expanded ? " ↑" : " ↓"}</span>}
        </div>
      )}
    </div>
  );
}

export default function DocumentDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [doc, setDoc] = useState(null);
  const [directions, setDirections] = useState([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    try {
      const [d, dirs] = await Promise.all([getDocument(id), getDocumentDirections(id)]);
      setDoc(d);
      setDirections(dirs);
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => { load(); }, [load]);

  // Авто-поллинг если анализируется
  useEffect(() => {
    if (!doc || doc.status !== "analyzing") return;
    const t = setInterval(async () => {
      const fresh = await getDocument(id);
      setDoc(fresh);
      if (fresh.status !== "analyzing") {
        clearInterval(t);
        const dirs = await getDocumentDirections(id);
        setDirections(dirs);
      }
    }, 3000);
    return () => clearInterval(t);
  }, [doc?.status, id]);

  const onChangeStatus = async (dirId, status) => {
    await updateDirectionStatus(dirId, status);
    const dirs = await getDocumentDirections(id);
    setDirections(dirs);
  };

  if (loading) return <div className="main"><p className="muted">Загрузка…</p></div>;
  if (!doc) return <div className="main"><p className="muted">Документ не найден</p></div>;

  // Группировка по федеральным направлениям
  const groups = FEDERAL_DIRECTIONS.map((federal, idx) => ({
    federal,
    short: FEDERAL_SHORT[federal],
    color: DIRECTION_COLORS[idx],
    items: directions.filter((d) => d.federal_match === federal),
  })).filter((g) => g.items.length > 0);

  const unmatched = directions.filter((d) => !d.federal_match);
  const total = directions.length;
  const covered = groups.length;

  return (
    <div className="page">
      <button className="dd-back" onClick={() => navigate("/")}>
        ← Все документы
      </button>

      <div className="dd-header">
        <div className="dd-header-left">
          <h1 className="page-title" style={{ fontSize: 22 }}>{doc.original_name}</h1>
          <div className="dd-header-meta">
            <StatusBadge kind="docType" value={doc.doc_type} />
            <StatusBadge kind="docStatus" value={doc.status} />
            {doc.status === "done" && (
              <span className="dd-summary">
                {covered} из 7 направлений · {total} активностей
              </span>
            )}
          </div>
        </div>
        {doc.status === "analyzing" && (
          <div className="doc-analyzing">
            <span className="spinner" /> Идёт анализ…
          </div>
        )}
      </div>

      {doc.status === "error" && (
        <div className="doc-error" style={{ marginBottom: 24 }}>{doc.error_message}</div>
      )}

      {doc.status === "done" && directions.length === 0 && (
        <div style={{ textAlign: "center", padding: "60px 24px", color: "var(--text-3)" }}>
          <div style={{ fontSize: 32, marginBottom: 12 }}>🔍</div>
          <div style={{ fontWeight: 600, color: "var(--text-2)" }}>Направлений не найдено</div>
          <div style={{ marginTop: 4, fontSize: 13 }}>Попробуйте повторить анализ</div>
        </div>
      )}

      {groups.length > 0 && (
        <div className="dd-groups">
          {groups.map(({ federal, short, color, items }) => (
            <div key={federal} className="dd-group" style={{ "--g-bg": color.bg, "--g-border": color.border, "--g-text": color.text, "--g-dot": color.dot }}>
              <div className="dd-group-header">
                <span className="dd-group-dot" />
                <span className="dd-group-title">{federal}</span>
                <span className="dd-group-count">{items.length}</span>
              </div>
              <div className="dd-items">
                {items.map((d) => (
                  <DirectionItem key={d.id} direction={d} onChangeStatus={onChangeStatus} />
                ))}
              </div>
            </div>
          ))}

          {unmatched.length > 0 && (
            <div className="dd-group" style={{ "--g-bg": "var(--bg)", "--g-border": "var(--border)", "--g-text": "var(--text-2)", "--g-dot": "var(--text-3)" }}>
              <div className="dd-group-header">
                <span className="dd-group-dot" />
                <span className="dd-group-title">Не определено</span>
                <span className="dd-group-count">{unmatched.length}</span>
              </div>
              <div className="dd-items">
                {unmatched.map((d) => (
                  <DirectionItem key={d.id} direction={d} onChangeStatus={onChangeStatus} />
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
