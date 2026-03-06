import { motion } from "framer-motion";
import {
  Coins,
  Cpu,
  Database,
  FolderOpen,
  Layers3,
  LoaderCircle,
  Plus,
  RefreshCcw,
  Save,
  Search,
  ShieldAlert,
  Trash2
} from "lucide-react";

const FIELD_GROUPS = [
  { id: "resources", label: "Resources" },
  { id: "base_attributes", label: "Base Attributes" },
  { id: "progression", label: "Progression" },
  { id: "progression_points", label: "Points" },
  { id: "combat", label: "Combat" }
];

const formatValue = (value, field) => {
  if (value === null || value === undefined) {
    return field?.current_mode === "auto" ? "AUTO" : "-";
  }
  if (field?.value_type === "f32") {
    return Number(value).toFixed(2).replace(/\\.00$/, "");
  }
  return String(value);
};

const draftKey = (recordId, fieldId) => `${recordId}::${fieldId}`;
const SAFE_CHARACTER_CLASSES = new Set(["party", "companion", "npc"]);
const isIdentityRisky = (record) =>
  Boolean(
    record &&
      record.kind === "character" &&
      (record.identity_status !== "resolved" ||
        record.template_status !== "resolved" ||
        !SAFE_CHARACTER_CLASSES.has(record.classification))
  );

const SemanticFieldRow = ({
  record,
  field,
  drafts,
  fieldConsents,
  onUpdateDraft,
  onToggleFieldConsent,
  onQueuePatch
}) => {
  const key = draftKey(record.record_id, field.field_id);
  const draft = drafts[key] ?? "";
  const disabled = !field.editable || record.classification === "environment";
  const placeholder = field.current_mode === "auto" ? "Set override..." : formatValue(field.value, field);

  return (
    <div className="semantic-field-row">
      <div className="semantic-field-head">
        <div>
          <p className="semantic-field-label">{field.label}</p>
          <p className="semantic-field-source mono faint">{field.source_path}</p>
        </div>
        <div className="semantic-field-badges">
          <span className={`semantic-badge semantic-badge-${field.status}`}>{field.status}</span>
          <span className="semantic-badge semantic-badge-muted">{field.value_type}</span>
        </div>
      </div>

      <div className="semantic-field-meta">
        <span className="mono strong">Current: {formatValue(field.value, field)}</span>
        {field.current_mode && <span className="mono faint">mode={field.current_mode}</span>}
      </div>

      <div className="semantic-field-actions">
        <input
          className="field field-center mono"
          value={draft}
          disabled={disabled}
          placeholder={placeholder}
          onChange={(e) => onUpdateDraft(record.record_id, field.field_id, e.target.value)}
        />
        <button
          type="button"
          className="btn-sub btn-neon-sub"
          disabled={disabled}
          onClick={() => onQueuePatch(record, field)}
        >
          <Save size={14} />
          Stage
        </button>
      </div>

      {field.status === "ambiguous" && (
        <label className="semantic-consent-row mono faint">
          <input
            type="checkbox"
            checked={Boolean(fieldConsents[key])}
            onChange={(e) => onToggleFieldConsent(record.record_id, field.field_id, e.target.checked)}
          />
          Allow patching this ambiguous field
        </label>
      )}

      {!!field.notes?.length && (
        <div className="semantic-field-notes mono faint">
          {field.notes.join(" ")}
        </div>
      )}
    </div>
  );
};

const StatsEditorPanel = ({
  patchFile,
  selectedProfile,
  profiles,
  profileFieldCount,
  semanticModel,
  semanticLoading,
  selectedRecord,
  semanticDrafts,
  semanticQueue,
  semanticFieldConsents,
  semanticIdentityConsents,
  economyRecords,
  isSemanticPatching,
  expertBatchRows,
  expertCharacters,
  onSelectProfile,
  onRefreshSemantic,
  onUpdateSemanticDraft,
  onToggleSemanticFieldConsent,
  onToggleSemanticIdentityConsent,
  onQueueSemanticPatch,
  onRemoveSemanticPatch,
  onApplySemanticPatches,
  onOpenPatchPicker,
  showExpertTools = false,
  onLoadProfileFields,
  onImportTopCandidates,
  onAddRow,
  onUpdateRow,
  onRemoveRow
}) => (
  <section className="panel panel-cyber pixel-border card-stack panel-density stats-editor-panel">
    <div className="card-head">
      <h2 className="card-title">
        <Cpu size={16} />
        Typed Naheulbeuk Editor
      </h2>
      <p className="card-subtitle">Semantic record selection, stat-level editing, preview queue, and expert raw fallback.</p>
    </div>

    <div className="semantic-toolbar">
      <div className="semantic-toolbar-copy">
        <p className="mono faint">Target file</p>
        <p className="semantic-target-path mono">{patchFile || "No target save selected"}</p>
      </div>
      <div className="semantic-toolbar-actions">
        <button type="button" className="btn-sub btn-neon-sub" onClick={onOpenPatchPicker}>
          <FolderOpen size={14} />
          Choose Save
        </button>
        <button type="button" className="btn-sub btn-neon-sub" onClick={onRefreshSemantic} disabled={!patchFile || semanticLoading}>
          {semanticLoading ? <LoaderCircle size={14} className="animate-spin" /> : <RefreshCcw size={14} />}
          Refresh Inspect
        </button>
      </div>
    </div>

    {!!semanticModel?.warnings?.length && (
      <div className="semantic-warning-stack">
        {semanticModel.warnings.map((warning, index) => (
          <div key={`${warning}-${index}`} className="semantic-warning-row">
            <ShieldAlert size={14} />
            <p>{warning}</p>
          </div>
        ))}
      </div>
    )}

    {selectedRecord ? (
      <div className="semantic-record-card">
        <div className="semantic-record-head">
          <div>
            <h3>{selectedRecord.label}</h3>
            <p className="mono faint">
              {selectedRecord.record_id} | {selectedRecord.identity_status} | confidence {selectedRecord.confidence}
            </p>
            <p className="mono faint">
              template {selectedRecord.template_id ?? "n/a"} | {selectedRecord.template_name || "unresolved"} | {selectedRecord.template_status} | {selectedRecord.template_resolution_source || "unresolved"} | {selectedRecord.template_source_detail || "n/a"}
            </p>
            <p className="mono faint">
              role {selectedRecord.structure_signature} | group {selectedRecord.group_id || "n/a"} | size {selectedRecord.group_size || 1}
            </p>
            {selectedRecord.scene_hint && (
              <p className="mono faint">
                scene {selectedRecord.scene_hint.class_name} | {selectedRecord.scene_hint.game_object_name || "n/a"} | {selectedRecord.scene_hint.scene_path}
              </p>
            )}
          </div>
          <div className="semantic-record-meta">
            <span className={`semantic-badge semantic-badge-${selectedRecord.edit_status === "safe" ? "resolved" : selectedRecord.edit_status === "risky" ? "ambiguous" : "unresolved"}`}>
              {selectedRecord.edit_status}
            </span>
            <span className="semantic-badge semantic-badge-muted">{selectedRecord.classification}</span>
            <span className="semantic-badge semantic-badge-resolved">{selectedRecord.fields.length} fields</span>
          </div>
        </div>

        {selectedRecord.classification === "environment" && (
          <div className="semantic-warning-row">
            <ShieldAlert size={14} />
            <p>Scene/environment records are inspect-only in semantic mode. Use Expert Mode if you intentionally want raw offset patching.</p>
          </div>
        )}

        {selectedRecord.classification !== "environment" && isIdentityRisky(selectedRecord) && (
          <label className="semantic-consent-row mono faint">
            <input
              type="checkbox"
              checked={Boolean(semanticIdentityConsents[selectedRecord.record_id])}
              onChange={(e) => onToggleSemanticIdentityConsent(selectedRecord.record_id, e.target.checked)}
            />
            Allow patching this inferred or unresolved character record
          </label>
        )}

        <div className="semantic-groups">
          {FIELD_GROUPS.map((group) => {
            const items = selectedRecord.fields.filter((field) => field.category === group.id);
            if (!items.length) {
              return null;
            }

            return (
              <div key={group.id} className="semantic-group-card">
                <h4>{group.label}</h4>
                <div className="semantic-field-stack">
                  {items.map((field) => (
                    <SemanticFieldRow
                      key={`${selectedRecord.record_id}-${field.field_id}`}
                      record={selectedRecord}
                      field={field}
                      drafts={semanticDrafts}
                      fieldConsents={semanticFieldConsents}
                      onUpdateDraft={onUpdateSemanticDraft}
                      onToggleFieldConsent={onToggleSemanticFieldConsent}
                      onQueuePatch={onQueueSemanticPatch}
                    />
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    ) : (
      <div className="semantic-empty mono faint">
        Select a parsed character record to edit semantic stats.
      </div>
    )}

    {!!economyRecords.length && (
      <div className="semantic-group-card">
        <div className="semantic-economy-head">
          <h4>
            <Coins size={15} />
            Economy Slots
          </h4>
          <p className="mono faint">Gold remains unresolved per-owner, so it is exposed as standalone economy slots.</p>
        </div>

        <div className="semantic-economy-grid">
          {economyRecords.map((record) => {
            const field = record.fields[0];
            return (
              <div key={record.record_id} className="semantic-economy-row">
                <div>
                  <p className="semantic-field-label">{record.label}</p>
                  <p className="mono faint">current {formatValue(field.value, field)}</p>
                </div>
                <input
                  className="field field-center mono"
                  value={semanticDrafts[draftKey(record.record_id, field.field_id)] ?? ""}
                  placeholder={formatValue(field.value, field)}
                  onChange={(e) => onUpdateSemanticDraft(record.record_id, field.field_id, e.target.value)}
                />
                <label className="semantic-consent-row mono faint">
                  <input
                    type="checkbox"
                    checked={Boolean(semanticFieldConsents[draftKey(record.record_id, field.field_id)])}
                    onChange={(e) => onToggleSemanticFieldConsent(record.record_id, field.field_id, e.target.checked)}
                  />
                  Allow ambiguous patch
                </label>
                <button type="button" className="btn-sub btn-neon-sub" onClick={() => onQueueSemanticPatch(record, field)}>
                  <Save size={14} />
                  Stage
                </button>
              </div>
            );
          })}
        </div>
      </div>
    )}

    <div className="semantic-group-card">
      <div className="semantic-queue-head">
        <h4>Patch Preview Queue</h4>
        <button type="button" className="btn-sub btn-neon-sub" disabled={!semanticQueue.length || isSemanticPatching} onClick={onApplySemanticPatches}>
          {isSemanticPatching ? <LoaderCircle size={14} className="animate-spin" /> : <Save size={14} />}
          Apply Semantic Batch
        </button>
      </div>

      <div className="semantic-queue-list">
        {semanticQueue.map((item) => (
          <motion.div
            key={item.id}
            className="semantic-queue-row"
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.16 }}
          >
            <div>
              <p className="semantic-field-label">
                {item.record_label} {"->"} {item.field_label}
              </p>
              <p className="mono faint">
                {formatValue(item.old_value, item.field)} {"=>"} {item.value}
                {item.allow_ambiguous ? " | allow_ambiguous" : ""}
                {item.allow_identity_ambiguous ? " | allow_identity_ambiguous" : ""}
              </p>
              <p className="mono faint">
                spans: {item.field.spans.map((span) => span.payload_offset_hex || `0x${Number(span.payload_offset).toString(16).toUpperCase()}`).join(", ") || "n/a"}
              </p>
            </div>
            <button type="button" className="btn-sub btn-neon-sub btn-neon-danger" onClick={() => onRemoveSemanticPatch(item.id)}>
              <Trash2 size={14} />
            </button>
          </motion.div>
        ))}
        {!semanticQueue.length && <div className="mono faint">No semantic patches staged yet.</div>}
      </div>
    </div>

    {showExpertTools && (
    <div className="semantic-group-card">
      <div className="card-head">
        <h3 className="card-title">
          <Layers3 size={16} />
          Expert Offset Queue
        </h3>
        <p className="card-subtitle">Legacy raw offset matrix for profile offsets and candidate imports.</p>
      </div>

      <div className="batch-toolbar">
        <label className="field-wrap">
          <span className="field-label">Profile</span>
          <select className="field field-select" value={selectedProfile} onChange={(e) => onSelectProfile(e.target.value)}>
            {!profiles.length && <option value="">No profiles</option>}
            {profiles.map((profileId) => (
              <option key={profileId} value={profileId}>
                {profileId}
              </option>
            ))}
          </select>
        </label>

        <div className="batch-meta mono faint">fields in profile: {profileFieldCount}</div>

        <div className="batch-actions">
          <button type="button" className="btn-sub btn-neon-sub" onClick={onLoadProfileFields}>
            <Database size={14} />
            Load Profile Fields
          </button>
          <button type="button" className="btn-sub btn-neon-sub" onClick={onImportTopCandidates}>
            <Search size={14} />
            Import Top Candidates
          </button>
          <button type="button" className="btn-sub btn-neon-sub" onClick={() => onAddRow({ character: "global" })}>
            <Plus size={14} />
            Add Row
          </button>
        </div>
      </div>

      <div className="batch-grid-wrap">
        <div className="batch-grid-head">
          <span>Field</span>
          <span>Offset</span>
          <span>Width</span>
          <span>Value</span>
          <span className="text-right">Action</span>
        </div>

        <div className="batch-grid-body">
          {expertBatchRows.map((row) => (
            <motion.div
              key={row.id}
              className="batch-grid-row"
              initial={{ opacity: 0.75, y: 3 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.18 }}
            >
              <input
                className="field"
                value={row.label}
                placeholder="gold"
                onChange={(e) => onUpdateRow(row.id, "label", e.target.value)}
              />
              <input
                className="field mono"
                value={row.offset}
                placeholder="0x1A4"
                onChange={(e) => onUpdateRow(row.id, "offset", e.target.value)}
              />
              <div className="chip-row">
                {[2, 4].map((w) => (
                  <button
                    key={`${row.id}-${w}`}
                    type="button"
                    className={`chip chip-mini ${Number(row.width) === w ? "chip-active" : ""}`}
                    onClick={() => onUpdateRow(row.id, "width", w)}
                  >
                    {w}B
                  </button>
                ))}
              </div>
              <input
                className="field field-center mono"
                value={row.value}
                placeholder="9999"
                onChange={(e) => onUpdateRow(row.id, "value", e.target.value)}
              />
              <div className="text-right flex gap-2 justify-end">
                <select
                  className="field field-select text-xs max-w-[120px]"
                  value={row.character || "global"}
                  onChange={(e) => onUpdateRow(row.id, "character", e.target.value)}
                >
                  {expertCharacters.map((character) => (
                    <option key={character} value={character}>
                      {character}
                    </option>
                  ))}
                  {!expertCharacters.includes(row.character) && <option value={row.character}>{row.character}</option>}
                </select>
                <button type="button" className="btn-sub btn-neon-sub btn-neon-danger" onClick={() => onRemoveRow(row.id)}>
                  <Trash2 size={14} />
                </button>
              </div>
            </motion.div>
          ))}
          {!expertBatchRows.length && <div className="p-8 text-center mono faint">No expert offset rows queued.</div>}
        </div>
      </div>
    </div>
    )}
  </section>
);

export default StatsEditorPanel;
