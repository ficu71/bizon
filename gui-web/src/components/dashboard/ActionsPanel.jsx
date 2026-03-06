import { motion } from "framer-motion";
import { Activity, FolderOpen, Layers3, Terminal, TriangleAlert, Wrench } from "lucide-react";

const yeetHover = {
  x: [0, -1, 1, 0],
  y: [0, 1, -1, 0],
  transition: { duration: 0.24 }
};

const ActionsPanel = ({
  patchFile,
  patchOffset,
  patchValue,
  patchWidth,
  isPatching,
  isBatchPatching,
  patchLog,
  parseOffset,
  onChangePatchOffset,
  onChangePatchValue,
  onChangePatchWidth,
  onOpenPatchPicker,
  onPatch,
  onBatchPatch,
  glitchBurstKey
}) => (
  <section className="actions-stack">
    <motion.div
      className="panel panel-cyber pixel-border card-stack panel-density"
      key={`patch-glitch-${glitchBurstKey}`}
      initial={{ opacity: 0.97 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.2 }}
    >
      <div className="card-head">
        <h2 className="card-title">
          <Wrench size={16} />
          Expert Raw Patch
        </h2>
        <p className="card-subtitle">Expert Mode only: patch raw offsets directly when semantic editing is not the right tool.</p>
      </div>

      <label className="field-wrap">
        <span className="field-label">Target File</span>
        <div className="save-picker-row">
          <div className={`save-picker-path mono ${patchFile ? "" : "save-picker-empty"}`} title={patchFile || "Nie wybrano pliku"}>
            {patchFile || "Nie wybrano pliku"}
          </div>
          <button type="button" className="btn-sub btn-neon-sub" onClick={onOpenPatchPicker}>
            <FolderOpen size={14} />
            Wybierz plik
          </button>
        </div>
      </label>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <label className="field-wrap">
          <span className="field-label">Offset (hex or dec)</span>
          <input
            className="field field-center"
            value={patchOffset}
            placeholder="0x1A4"
            onChange={(e) => onChangePatchOffset(e.target.value)}
          />
        </label>
        <label className="field-wrap">
          <span className="field-label">New Value</span>
          <input
            className="field field-center"
            inputMode="numeric"
            value={patchValue}
            placeholder="999999"
            onChange={(e) => onChangePatchValue(e.target.value)}
          />
        </label>
      </div>

      <div className="grid gap-4 md:grid-cols-[auto_1fr] md:items-end">
        <div className="field-wrap min-w-[140px]">
          <span className="field-label">Width</span>
          <div className="chip-row">
            {[2, 4].map((w) => (
              <button
                key={w}
                type="button"
                onClick={() => onChangePatchWidth(w)}
                className={`chip ${patchWidth === w ? "chip-active" : ""}`}
              >
                {w}B
              </button>
            ))}
          </div>
        </div>

        <div className="mono faint text-sm md:text-right">offset dec: {Number.isNaN(parseOffset(patchOffset)) ? "-" : parseOffset(patchOffset)}</div>
      </div>

      <motion.button
        type="button"
        className="btn-main btn-neon-main yeet-btn"
        onClick={onPatch}
        disabled={isPatching}
        whileHover={!isPatching ? yeetHover : undefined}
        whileTap={!isPatching ? { scale: 0.98 } : undefined}
      >
        {isPatching ? <Activity size={18} className="animate-spin" /> : <Terminal size={18} />}
        {isPatching ? "BREAKING THE GAME" : "BREAK THE GAME"}
      </motion.button>

      <motion.button
        type="button"
        className="btn-main btn-neon-main yeet-btn"
        onClick={onBatchPatch}
        disabled={isBatchPatching}
        whileHover={!isBatchPatching ? yeetHover : undefined}
        whileTap={!isBatchPatching ? { scale: 0.98 } : undefined}
      >
        {isBatchPatching ? <Activity size={18} className="animate-spin" /> : <Layers3 size={18} />}
        {isBatchPatching ? "PATCHING MASS CHAOS" : "MASS CHAOS PATCH"}
      </motion.button>
    </motion.div>

    <div className="panel panel-cyber pixel-border card-stack panel-density">
      <div className="card-head">
        <h2 className="card-title">
          <Terminal size={16} />
          Command Stream
        </h2>
        <p className="card-subtitle">Latest semantic and expert-mode events.</p>
      </div>

      <div className="terminal-box">
        {patchLog.length ? (
          patchLog.map((entry, idx) => (
            <motion.p
              key={`${entry}-${idx}`}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.2 }}
              className="mono"
            >
              {">"} {entry}
            </motion.p>
          ))
        ) : (
          <p className="mono faint">No events yet. Run scan or patch.</p>
        )}
      </div>

      <div className="hint-box">
        <TriangleAlert size={16} />
        <p>This operation modifies binary data directly. Backup remains enabled.</p>
      </div>
    </div>
  </section>
);

export default ActionsPanel;
