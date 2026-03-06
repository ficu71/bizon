import { motion } from "framer-motion";
import { Activity, Binary, Database, Gauge, ShieldCheck } from "lucide-react";

const statusLabel = {
  online: "ONLINE",
  offline: "OFFLINE",
  checking: "CHECK"
};

const HeaderMetric = ({ icon, label, value }) => (
  <div className="metric-chip">
    <span className="metric-chip-icon">{icon}</span>
    <div>
      <p className="metric-chip-label">{label}</p>
      <p className="metric-chip-value">{value}</p>
    </div>
  </div>
);

const HeaderBar = ({ backendState, profilesCount, candidatesCount, topScore, avgScore, apiBase, logoSrc }) => (
  <motion.header
    className="panel panel-cyber pixel-border dashboard-header"
    initial={{ opacity: 0, y: -10 }}
    animate={{ opacity: 1, y: 0 }}
    transition={{ duration: 0.3 }}
  >
    <div className="dashboard-brand-row">
      <div className="brand-mark brand-logo">
        <img src={logoSrc} alt="f1cu_71 logo" className="brand-logo-img" />
      </div>

      <div className="dashboard-brand-copy">
        <p className="kicker">Bizon Industries</p>
        <h1 className="brand-title glitch-title neon-text" data-text="BIZON SAVE CONTROL PLANE">
          BIZON SAVE CONTROL PLANE
        </h1>
      </div>

      <span className={`status-pill ${backendState === "online" ? "status-online" : backendState === "offline" ? "status-offline" : "status-warn"}`}>
        <Activity size={12} className={backendState === "checking" ? "animate-pulse" : ""} />
        API {statusLabel[backendState] || "CHECK"}
      </span>
    </div>

    <div className="header-metrics">
      <HeaderMetric icon={<Database size={14} />} label="Profiles" value={profilesCount} />
      <HeaderMetric icon={<Gauge size={14} />} label="Candidates" value={candidatesCount} />
      <HeaderMetric icon={<Binary size={14} />} label="Top Score" value={topScore} />
      <HeaderMetric icon={<ShieldCheck size={14} />} label="Avg Score" value={avgScore} />
      <HeaderMetric icon={<Activity size={14} />} label="Backend" value={apiBase.replace(/^https?:\/\//, "")} />
    </div>
  </motion.header>
);

export default HeaderBar;
