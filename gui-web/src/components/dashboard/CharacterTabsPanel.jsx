import { motion } from "framer-motion";

const RISK_FILTERS = [
  { id: "all", label: "All" },
  { id: "safe", label: "Safe" },
  { id: "risky", label: "Risky" },
  { id: "unresolved", label: "Unresolved" }
];

const CLASS_FILTERS = [
  { id: "all", label: "Any Class" },
  { id: "party", label: "Party" },
  { id: "companion", label: "Companion" },
  { id: "npc", label: "NPC" },
  { id: "environment", label: "Environment" },
  { id: "unknown", label: "Unknown" }
];

const countByRisk = (records, filterId, classificationFilter) =>
  records.filter((record) => {
    if (classificationFilter !== "all" && record.classification !== classificationFilter) {
      return false;
    }
    if (filterId !== "all" && record.edit_status !== filterId) {
      return false;
    }
    return true;
  }).length;

const countByClass = (records, filterId, riskFilter) =>
  records.filter((record) => {
    if (riskFilter !== "all" && record.edit_status !== riskFilter) {
      return false;
    }
    if (filterId !== "all" && record.classification !== filterId) {
      return false;
    }
    return true;
  }).length;

const CharacterTabsPanel = ({
  allRecords,
  records,
  selectedRecordId,
  onChangeRecord,
  riskFilter,
  classificationFilter,
  onChangeRiskFilter,
  onChangeClassificationFilter,
  isLoading,
  patchFile
}) => (
  <section className="panel panel-cyber pixel-border panel-density character-tabs-panel character-selector">
    <div className="character-selector-head">
      <span className="character-selector-label">Naheulbeuk Records</span>
      <span className="character-selector-count mono faint">
        {records.length}/{allRecords.length} visible
      </span>
    </div>

    {!!allRecords.length && (
      <>
        <div className="character-filter-row">
          {RISK_FILTERS.map((filter) => (
            <button
              key={filter.id}
              type="button"
              className={`chip character-filter-chip ${riskFilter === filter.id ? "chip-active character-filter-chip-active" : ""}`}
              onClick={() => onChangeRiskFilter(filter.id)}
            >
              {filter.label} <span className="mono">{countByRisk(allRecords, filter.id, classificationFilter)}</span>
            </button>
          ))}
        </div>

        <div className="character-filter-row">
          {CLASS_FILTERS.map((filter) => (
            <button
              key={filter.id}
              type="button"
              className={`chip character-filter-chip ${classificationFilter === filter.id ? "chip-active character-filter-chip-active" : ""}`}
              onClick={() => onChangeClassificationFilter(filter.id)}
            >
              {filter.label} <span className="mono">{countByClass(allRecords, filter.id, riskFilter)}</span>
            </button>
          ))}
        </div>
      </>
    )}

    {!patchFile && <div className="mono faint">Choose a target save file to inspect semantic character records.</div>}
    {patchFile && isLoading && <div className="mono faint">Inspecting typed character blocks...</div>}

    {!!records.length && (
      <div className="character-selector-tabs">
        {records.map((record) => (
          <motion.button
            key={record.record_id}
            type="button"
            onClick={() => onChangeRecord(record.record_id)}
            className={`chip character-chip ${selectedRecordId === record.record_id ? "chip-active character-chip-active" : ""}`}
            whileTap={{ scale: 0.98 }}
            title={`${record.label} | ${record.identity_status} | ${record.edit_status} | confidence ${record.confidence}`}
          >
            <span className="character-chip-title">{record.label}</span>
            <span className="character-chip-meta mono">
              #{String(record.block_index || "?").padStart(2, "0")} {record.edit_status} | {record.classification}
              {record.group_size > 1 ? ` | x${record.group_size}` : ""}
            </span>
          </motion.button>
        ))}
      </div>
    )}

    {patchFile && !isLoading && !allRecords.length && (
      <div className="mono faint">No typed Naheulbeuk character records were resolved for this file.</div>
    )}

    {patchFile && !isLoading && !!allRecords.length && !records.length && (
      <div className="mono faint">No character records match the active filters.</div>
    )}
  </section>
);

export default CharacterTabsPanel;
