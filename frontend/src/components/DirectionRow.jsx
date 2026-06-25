import { useState } from "react";
import StatusBadge from "./StatusBadge.jsx";

const ACTIONS = [
  { status: "confirmed", symbol: "✓", title: "Подтвердить", cls: "act-confirm" },
  { status: "needs_clarification", symbol: "?", title: "Требует уточнения", cls: "act-clarify" },
  { status: "rejected", symbol: "✗", title: "Отклонить", cls: "act-reject" },
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

export default function DirectionRow({ direction, onChangeStatus }) {
  const [expanded, setExpanded] = useState(false);

  const fragment = direction.fragment || "";
  const isLong = fragment.length > 100;
  const shown = expanded || !isLong ? fragment : `${fragment.slice(0, 100)}…`;

  const federalShort = direction.federal_match
    ? FEDERAL_SHORT[direction.federal_match] || direction.federal_match
    : null;

  return (
    <tr>
      <td className="cell-title">{direction.title}</td>
      <td>
        {federalShort ? (
          <span title={direction.federal_match} className="badge badge-blue" style={{ cursor: "help" }}>
            {federalShort}
          </span>
        ) : (
          <span className="muted" style={{ fontSize: 12 }}>—</span>
        )}
      </td>
      <td className="cell-doc">{direction.document_name || "—"}</td>
      <td
        className={isLong ? "cell-fragment clickable" : "cell-fragment"}
        onClick={() => isLong && setExpanded((v) => !v)}
        title={isLong ? (expanded ? "Свернуть" : "Развернуть") : ""}
      >
        {shown || <span className="muted">—</span>}
        {isLong && (
          <span style={{ marginLeft: 4, color: "var(--accent)", fontSize: 11 }}>
            {expanded ? "↑" : "↓"}
          </span>
        )}
      </td>
      <td>
        <StatusBadge kind="confidence" value={direction.confidence} />
      </td>
      <td>
        <StatusBadge kind="verification" value={direction.verification_status} />
      </td>
      <td>
        <div className="actions">
          {ACTIONS.map((a) => (
            <button
              key={a.status}
              className={`act-btn ${a.cls} ${direction.verification_status === a.status ? "active" : ""}`}
              title={a.title}
              onClick={() => onChangeStatus(direction.id, a.status)}
            >
              {a.symbol}
            </button>
          ))}
        </div>
      </td>
    </tr>
  );
}
