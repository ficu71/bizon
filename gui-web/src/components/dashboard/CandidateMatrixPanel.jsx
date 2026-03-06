import { AnimatePresence, motion } from "framer-motion";
import { ChevronsRight, CopyCheck, Layers3 } from "lucide-react";

const CandidateMatrixPanel = ({ candidates, onLoadCandidate, onQueueCandidate, pulseKey }) => (
  <section className="panel panel-cyber pixel-border card-stack panel-density matrix-panel">
    <div className="card-head">
      <h2 className="card-title">
        <ChevronsRight size={16} />
        Expert Candidate Matrix
      </h2>
      <p className="card-subtitle">Expert Mode only: load scanned offsets into the raw patch flow.</p>
    </div>

    <AnimatePresence mode="popLayout">
      <motion.div
        key={`candidate-matrix-${pulseKey}`}
        className="candidate-scroll"
        initial={{ opacity: 0.9, scale: 0.997 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0.95 }}
        transition={{ duration: 0.24 }}
      >
        <table className="candidate-table">
          <thead>
            <tr>
              <th>Offset</th>
              <th>Score</th>
              <th>Context Hex</th>
              <th className="text-right">Action</th>
            </tr>
          </thead>
          <tbody>
            {candidates.slice(0, 60).map((candidate, idx) => (
              <tr key={`${candidate.offset}-${idx}`}>
                <td className="mono strong">0x{Number(candidate.offset).toString(16).toUpperCase()}</td>
                <td>
                  <div className="score-wrap">
                    <div className="score-track">
                      <motion.div
                        initial={{ width: 0 }}
                        animate={{ width: `${Math.min(100, (Number(candidate.score || 0) / 600) * 100)}%` }}
                        transition={{ type: "spring", stiffness: 210, damping: 20 }}
                        className="score-fill"
                      />
                    </div>
                    <span className="mono">{candidate.score}</span>
                  </div>
                </td>
                <td className="mono faint">{candidate.context_hex || "-"}</td>
                <td className="text-right">
                  <div className="action-row">
                    <button type="button" className="btn-sub btn-neon-sub" onClick={() => onLoadCandidate(candidate)}>
                      <CopyCheck size={14} />
                      Load
                    </button>
                    <button type="button" className="btn-sub btn-neon-sub" onClick={() => onQueueCandidate(candidate)}>
                      <Layers3 size={14} />
                      Queue
                    </button>
                  </div>
                </td>
              </tr>
            ))}
            {!candidates.length && (
              <tr>
                <td colSpan={4} className="empty-row">
                  Run a scan to populate candidate offsets.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </motion.div>
    </AnimatePresence>
  </section>
);

export default CandidateMatrixPanel;
