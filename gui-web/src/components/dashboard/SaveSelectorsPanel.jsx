import { motion } from "framer-motion";
import { Activity, Files, FolderOpen, Radar } from "lucide-react";

const yeetHover = {
  x: [0, -1, 1, 0],
  y: [0, 1, -1, 0],
  transition: { duration: 0.24 }
};

const SaveSelectorsPanel = ({
  saves,
  values,
  width,
  isScanning,
  onOpenSavePicker,
  onChangeValue,
  onChangeWidth,
  onScan
}) => (
  <section className="panel panel-cyber pixel-border card-stack panel-density save-selectors-panel">
    <div className="card-head">
      <h2 className="card-title">
        <Files size={16} />
        Expert Scan Inputs
      </h2>
      <p className="card-subtitle">Expert Mode only: compare three snapshots from one slot to hunt raw offsets.</p>
    </div>

    <div className="space-y-3">
      {saves.map((path, idx) => (
        <div key={idx} className="field-wrap">
          <span className="field-label">Save {String.fromCharCode(65 + idx)}</span>
          <div className="save-picker-row">
            <div className={`save-picker-path mono ${path ? "" : "save-picker-empty"}`} title={path || "Nie wybrano pliku"}>
              {path || "Nie wybrano pliku"}
            </div>
            <button type="button" className="btn-sub btn-neon-sub" onClick={() => onOpenSavePicker(idx)}>
              <FolderOpen size={14} />
              Wybierz plik
            </button>
          </div>
        </div>
      ))}
    </div>

    <div className="grid gap-4 lg:grid-cols-[1fr_auto]">
      <div className="grid grid-cols-3 gap-3">
        {values.map((value, idx) => (
          <label key={idx} className="field-wrap">
            <span className="field-label">Value {String.fromCharCode(65 + idx)}</span>
            <input
              className="field field-center"
              inputMode="numeric"
              value={value}
              placeholder="111"
              onChange={(e) => onChangeValue(idx, e.target.value)}
            />
          </label>
        ))}
      </div>

      <div className="field-wrap min-w-[136px]">
        <span className="field-label">Width</span>
        <div className="chip-row">
          {[2, 4].map((w) => (
            <button
              key={w}
              type="button"
              onClick={() => onChangeWidth(w)}
              className={`chip ${width === w ? "chip-active" : ""}`}
            >
              {w}B
            </button>
          ))}
        </div>
      </div>
    </div>

    <motion.button
      type="button"
      className="btn-main btn-neon-main yeet-btn"
      onClick={onScan}
      disabled={isScanning}
      whileHover={!isScanning ? yeetHover : undefined}
      whileTap={!isScanning ? { scale: 0.98 } : undefined}
    >
      {isScanning ? <Activity size={18} className="animate-spin" /> : <Radar size={18} />}
      {isScanning ? "SCANNING CHAOS MATRIX" : "YEET THE SAVES"}
    </motion.button>
  </section>
);

export default SaveSelectorsPanel;
