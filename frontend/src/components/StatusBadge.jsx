const DOC_STATUS = {
  uploaded: { label: "Загружен", cls: "badge-grey" },
  analyzing: { label: "Анализ…", cls: "badge-blue" },
  done: { label: "Готово", cls: "badge-green" },
  error: { label: "Ошибка", cls: "badge-red" },
};

const DOC_TYPE = {
  federal: { label: "Федеральный", cls: "badge-blue" },
  regional: { label: "Региональный", cls: "badge-grey" },
};

const CONFIDENCE = {
  high: { label: "Высокая", cls: "badge-green" },
  medium: { label: "Средняя", cls: "badge-yellow" },
  low: { label: "Низкая", cls: "badge-grey" },
};

const VERIFICATION = {
  pending: { label: "Ожидает", cls: "badge-grey" },
  confirmed: { label: "Подтверждено", cls: "badge-green" },
  needs_clarification: { label: "Уточнить", cls: "badge-yellow" },
  rejected: { label: "Отклонено", cls: "badge-red" },
};

const MAPS = {
  docStatus: DOC_STATUS,
  docType: DOC_TYPE,
  confidence: CONFIDENCE,
  verification: VERIFICATION,
};

export default function StatusBadge({ kind, value }) {
  const map = MAPS[kind] || {};
  const entry = map[value] || { label: value, cls: "badge-grey" };
  return <span className={`badge ${entry.cls}`}>{entry.label}</span>;
}
