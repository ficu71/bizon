import React, { useEffect, useMemo, useState } from "react";
import axios from "axios";
import { AnimatePresence, motion } from "framer-motion";
import { FolderOpen, RefreshCcw, ShieldCheck, TriangleAlert } from "lucide-react";
import "./App.css";
import logo from "./assets/f1cu_71.png";
import ActionsPanel from "./components/dashboard/ActionsPanel";
import CandidateMatrixPanel from "./components/dashboard/CandidateMatrixPanel";
import CharacterTabsPanel from "./components/dashboard/CharacterTabsPanel";
import FileExplorerModal from "./components/dashboard/FileExplorerModal";
import HeaderBar from "./components/dashboard/HeaderBar";
import SaveSelectorsPanel from "./components/dashboard/SaveSelectorsPanel";
import StatsEditorPanel from "./components/dashboard/StatsEditorPanel";

const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";
const FX_LEVEL = (import.meta.env.VITE_FX_LEVEL || "balanced").toLowerCase() === "aggressive" ? "aggressive" : "balanced";

const parseOffset = (raw) => {
  const input = String(raw || "").trim().toLowerCase();
  if (!input) return NaN;
  return input.startsWith("0x") ? parseInt(input, 16) : parseInt(input, 10);
};

const nowStamp = () => new Date().toLocaleTimeString();

const makeRow = (seed = {}) => ({
  id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
  label: seed.label ?? "",
  offset: seed.offset ?? "",
  width: seed.width ?? 4,
  value: seed.value ?? "",
  character: seed.character ?? "global"
});

const inferWidthFromType = (type) => {
  const t = String(type || "").toLowerCase();
  return t.includes("16") ? 2 : 4;
};

const inferProfileRows = (profile) => {
  const fields = profile?.fields;
  if (!fields || typeof fields !== "object") return [];

  return Object.entries(fields).map(([name, info]) => {
    const rawOffset = info?.offset;
    const offset = Number.isInteger(rawOffset) ? `0x${rawOffset.toString(16).toUpperCase()}` : "";
    return makeRow({
      label: name,
      offset,
      width: inferWidthFromType(info?.type),
      value: "",
      character: info?.character || "global"
    });
  });
};

const draftKey = (recordId, fieldId) => `${recordId}::${fieldId}`;
const SAFE_CHARACTER_CLASSES = new Set(["party", "companion", "npc"]);
const isSemanticIdentityRisky = (record) =>
  Boolean(
    record &&
      record.kind === "character" &&
      (record.identity_status !== "resolved" ||
        record.template_status !== "resolved" ||
        !SAFE_CHARACTER_CLASSES.has(record.classification))
  );
const recordMatchesFilters = (record, riskFilter, classificationFilter) => {
  if (riskFilter !== "all" && record.edit_status !== riskFilter) {
    return false;
  }
  if (classificationFilter !== "all" && record.classification !== classificationFilter) {
    return false;
  }
  return true;
};

const App = () => {
  const [profiles, setProfiles] = useState([]);
  const [selectedProfile, setSelectedProfile] = useState("");
  const [profileDetails, setProfileDetails] = useState(null);
  const [backendState, setBackendState] = useState("checking");

  const [saves, setSaves] = useState(["", "", ""]);
  const [values, setValues] = useState(["", "", ""]);
  const [width, setWidth] = useState(4);
  const [candidates, setCandidates] = useState([]);
  const [isScanning, setIsScanning] = useState(false);

  const [patchFile, setPatchFile] = useState("");
  const [patchOffset, setPatchOffset] = useState("");
  const [patchValue, setPatchValue] = useState("");
  const [patchWidth, setPatchWidth] = useState(4);
  const [isPatching, setIsPatching] = useState(false);

  const [batchRows, setBatchRows] = useState([makeRow()]);
  const [isBatchPatching, setIsBatchPatching] = useState(false);

  const [semanticModel, setSemanticModel] = useState(null);
  const [semanticDoctor, setSemanticDoctor] = useState(null);
  const [semanticDoctorLoading, setSemanticDoctorLoading] = useState(false);
  const [semanticLoading, setSemanticLoading] = useState(false);
  const [selectedRecordId, setSelectedRecordId] = useState("");
  const [recordRiskFilter, setRecordRiskFilter] = useState("safe");
  const [recordClassFilter, setRecordClassFilter] = useState("all");
  const [semanticDrafts, setSemanticDrafts] = useState({});
  const [semanticQueue, setSemanticQueue] = useState([]);
  const [semanticFieldConsents, setSemanticFieldConsents] = useState({});
  const [semanticIdentityConsents, setSemanticIdentityConsents] = useState({});
  const [isSemanticPatching, setIsSemanticPatching] = useState(false);

  const [patchLog, setPatchLog] = useState([]);
  const [errorMessage, setErrorMessage] = useState("");

  const [matrixPulseKey, setMatrixPulseKey] = useState(0);
  const [glitchBurstKey, setGlitchBurstKey] = useState(0);

  const [savePickerOpen, setSavePickerOpen] = useState(false);
  const [savePickerIndex, setSavePickerIndex] = useState(0);
  const [patchPickerOpen, setPatchPickerOpen] = useState(false);

  const expertCharacters = useMemo(() => {
    const set = new Set(batchRows.map((row) => row.character || "global"));
    return Array.from(set).sort((a, b) => {
      if (a === "global") return -1;
      if (b === "global") return 1;
      return a.localeCompare(b);
    });
  }, [batchRows]);

  const semanticCharacters = useMemo(() => semanticModel?.characters || [], [semanticModel]);
  const economyRecords = useMemo(() => semanticModel?.economy || [], [semanticModel]);
  const visibleSemanticCharacters = useMemo(
    () =>
      semanticCharacters.filter((record) =>
        recordMatchesFilters(record, recordRiskFilter, recordClassFilter)
      ),
    [semanticCharacters, recordRiskFilter, recordClassFilter]
  );

  const selectedRecord = useMemo(
    () =>
      visibleSemanticCharacters.find((record) => record.record_id === selectedRecordId) ||
      visibleSemanticCharacters[0] ||
      null,
    [visibleSemanticCharacters, selectedRecordId]
  );

  useEffect(() => {
    const fetchProfiles = async () => {
      try {
        const resp = await axios.get(`${API_BASE}/profiles`);
        const list = Array.isArray(resp.data) ? resp.data : [];
        setProfiles(list);
        setSelectedProfile((prev) => prev || (list.includes("naheulbeuk") ? "naheulbeuk" : list[0] || ""));
        setBackendState("online");
      } catch (err) {
        setBackendState("offline");
        setErrorMessage(`Backend offline: ${err.response?.data?.detail || err.message}`);
      }
    };

    fetchProfiles();
  }, []);

  useEffect(() => {
    if (!selectedProfile) {
      setProfileDetails(null);
      return;
    }

    const fetchProfileDetails = async () => {
      try {
        const resp = await axios.get(`${API_BASE}/profiles/${selectedProfile}`);
        setProfileDetails(resp.data || null);
      } catch (err) {
        setErrorMessage(`Profile load failed: ${err.response?.data?.detail || err.message}`);
      }
    };

    fetchProfileDetails();
  }, [selectedProfile]);

  const loadSemanticDoctor = async (targetPath = patchFile, { silent = false } = {}) => {
    if (!silent) {
      setSemanticDoctorLoading(true);
    }

    try {
      const resp = await axios.get(`${API_BASE}/naheulbeuk/doctor`, {
        params: targetPath ? { filepath: String(targetPath || "").trim() } : {}
      });
      setSemanticDoctor(resp.data || null);
    } catch (err) {
      setSemanticDoctor(null);
      setErrorMessage(err.response?.data?.detail || err.message);
    } finally {
      if (!silent) {
        setSemanticDoctorLoading(false);
      }
    }
  };

  useEffect(() => {
    loadSemanticDoctor("", { silent: true });
  }, []);

  useEffect(() => {
    if (!visibleSemanticCharacters.length) {
      setSelectedRecordId("");
      return;
    }

    if (!visibleSemanticCharacters.some((record) => record.record_id === selectedRecordId)) {
      setSelectedRecordId(visibleSemanticCharacters[0].record_id);
    }
  }, [visibleSemanticCharacters, selectedRecordId]);

  const candidateStats = useMemo(() => {
    if (!candidates.length) {
      return { topScore: 0, avgScore: 0 };
    }
    const scores = candidates.map((candidate) => Number(candidate.score || 0));
    const topScore = Math.max(...scores);
    const avgScore = Math.round(scores.reduce((a, b) => a + b, 0) / scores.length);
    return { topScore, avgScore };
  }, [candidates]);

  const profileFieldCount = useMemo(() => {
    const fields = profileDetails?.fields;
    if (!fields || typeof fields !== "object") return 0;
    return Object.keys(fields).length;
  }, [profileDetails]);

  const loadSemanticInspect = async (targetPath = patchFile, { silent = false } = {}) => {
    const resolvedPath = String(targetPath || "").trim();
    if (!resolvedPath) {
      setSemanticModel(null);
      loadSemanticDoctor("", { silent: true });
      return;
    }

    if (selectedProfile && selectedProfile !== "naheulbeuk") {
      setSemanticModel(null);
      return;
    }

    if (!silent) {
      setSemanticLoading(true);
    }

    try {
      const resp = await axios.get(`${API_BASE}/naheulbeuk/inspect`, {
        params: { filepath: resolvedPath }
      });
      setSemanticModel(resp.data || null);
      setPatchLog((prev) => [`${nowStamp()} typed inspect refreshed for ${resolvedPath}`, ...prev].slice(0, 40));
      loadSemanticDoctor(resolvedPath, { silent: true });
    } catch (err) {
      setSemanticModel(null);
      setErrorMessage(err.response?.data?.detail || err.message);
    } finally {
      if (!silent) {
        setSemanticLoading(false);
      }
    }
  };

  useEffect(() => {
    if (!patchFile.trim() || (selectedProfile && selectedProfile !== "naheulbeuk")) {
      setSemanticModel(null);
      loadSemanticDoctor("", { silent: true });
      return;
    }

    loadSemanticInspect(patchFile, { silent: false });
  }, [patchFile, selectedProfile]);

  const handleScan = async () => {
    setErrorMessage("");

    if (saves.some((path) => !path.trim())) {
      setErrorMessage("Fill all 3 save file paths before scanning.");
      return;
    }

    const parsedValues = values.map((value) => Number(value));
    if (parsedValues.some((value) => Number.isNaN(value))) {
      setErrorMessage("Values A/B/C must be valid numbers.");
      return;
    }

    setIsScanning(true);
    try {
      const resp = await axios.post(`${API_BASE}/scan`, {
        saves,
        values: parsedValues,
        width,
        dtype: "auto"
      });

      const list = Array.isArray(resp.data) ? resp.data : [];
      setCandidates(list);
      setMatrixPulseKey((prev) => prev + 1);
      setGlitchBurstKey((prev) => prev + 1);
      setPatchLog((prev) => [`${nowStamp()} scan finished: ${list.length} candidates`, ...prev].slice(0, 40));
    } catch (err) {
      setErrorMessage(err.response?.data?.detail || err.message);
    } finally {
      setIsScanning(false);
    }
  };

  const handlePatch = async () => {
    setErrorMessage("");

    const offset = parseOffset(patchOffset);
    const value = Number(patchValue);

    if (!patchFile.trim()) {
      setErrorMessage("Patch file path is required.");
      return;
    }
    if (Number.isNaN(offset)) {
      setErrorMessage("Offset must be decimal or 0x hex.");
      return;
    }
    if (Number.isNaN(value)) {
      setErrorMessage("Patch value must be a valid number.");
      return;
    }

    setIsPatching(true);
    try {
      const resp = await axios.post(`${API_BASE}/patch`, {
        filepath: patchFile,
        offset,
        width: patchWidth,
        value,
        backup: true
      });

      if (resp.data?.status === "success") {
        const verified = resp.data?.verified ? "verified" : "unverified";
        setPatchLog((prev) => [`${nowStamp()} raw patch ${offset.toString(16).toUpperCase()} => ${value} (${verified})`, ...prev].slice(0, 40));
        setGlitchBurstKey((prev) => prev + 1);
      } else {
        setErrorMessage("Patch request returned failed status.");
      }
    } catch (err) {
      setErrorMessage(err.response?.data?.detail || err.message);
    } finally {
      setIsPatching(false);
    }
  };

  const updateBatchRow = (rowId, key, value) => {
    setBatchRows((prev) => prev.map((row) => (row.id === rowId ? { ...row, [key]: value } : row)));
  };

  const addBatchRow = (seed) => {
    setBatchRows((prev) => [...prev, makeRow(seed)]);
  };

  const removeBatchRow = (rowId) => {
    setBatchRows((prev) => {
      const next = prev.filter((row) => row.id !== rowId);
      return next.length ? next : [makeRow()];
    });
  };

  const loadCandidateIntoPatch = (candidate) => {
    const offsetHex = `0x${Number(candidate.offset).toString(16).toUpperCase()}`;
    setPatchFile(saves[0] || patchFile);
    setPatchOffset(offsetHex);
    setPatchWidth(width);
    setPatchLog((prev) => [`${nowStamp()} candidate loaded ${offsetHex}`, ...prev].slice(0, 40));
  };

  const queueCandidateInBatch = (candidate) => {
    const offsetHex = `0x${Number(candidate.offset).toString(16).toUpperCase()}`;
    setPatchFile((prev) => prev || saves[0] || "");
    addBatchRow({
      label: `candidate_${offsetHex}`,
      offset: offsetHex,
      width,
      value: ""
    });
    setPatchLog((prev) => [`${nowStamp()} queued ${offsetHex} in expert batch`, ...prev].slice(0, 40));
  };

  const importTopCandidates = () => {
    if (!candidates.length) {
      setErrorMessage("No candidates available. Run a scan first.");
      return;
    }

    const top = candidates.slice(0, 12);
    const nextRows = top.map((candidate) => {
      const offsetHex = `0x${Number(candidate.offset).toString(16).toUpperCase()}`;
      return makeRow({
        label: `top_${candidate.score}_${offsetHex}`,
        offset: offsetHex,
        width,
        value: ""
      });
    });

    setBatchRows((prev) => [...prev, ...nextRows]);
    setPatchFile((prev) => prev || saves[0] || "");
    setPatchLog((prev) => [`${nowStamp()} imported ${nextRows.length} top candidates`, ...prev].slice(0, 40));
  };

  const loadProfileFields = () => {
    const rows = inferProfileRows(profileDetails);
    if (!rows.length) {
      setErrorMessage("Selected profile has no fields.");
      return;
    }
    setBatchRows(rows);
    setPatchLog((prev) => [`${nowStamp()} loaded ${rows.length} profile fields`, ...prev].slice(0, 40));
  };

  const normalizeBatchRows = () => {
    const rows = batchRows.filter((row) => {
      const filled = String(row.offset).trim() || String(row.value).trim() || String(row.label).trim();
      return Boolean(filled);
    });

    if (!rows.length) {
      throw new Error("Add at least one batch row.");
    }

    return rows.map((row, index) => {
      const offset = parseOffset(row.offset);
      if (Number.isNaN(offset)) {
        throw new Error(`Row ${index + 1}: invalid offset.`);
      }

      const value = Number(row.value);
      if (Number.isNaN(value)) {
        throw new Error(`Row ${index + 1}: invalid value.`);
      }

      const parsedWidth = Number(row.width);
      if (![2, 4].includes(parsedWidth)) {
        throw new Error(`Row ${index + 1}: width must be 2 or 4.`);
      }

      return {
        label: row.label,
        offset,
        width: parsedWidth,
        value,
        character: row.character || "global"
      };
    });
  };

  const handleBatchPatch = async () => {
    setErrorMessage("");

    if (!patchFile.trim()) {
      setErrorMessage("Target file is required for batch patching.");
      return;
    }

    let normalized;
    try {
      normalized = normalizeBatchRows();
    } catch (err) {
      setErrorMessage(err.message);
      return;
    }

    setIsBatchPatching(true);
    try {
      const resp = await axios.post(`${API_BASE}/patch-batch`, {
        filepath: patchFile,
        patches: normalized.map((row) => ({
          offset: row.offset,
          width: row.width,
          value: row.value,
          label: row.label,
          character: row.character
        })),
        backup: true
      });

      const failedCount = Number(resp.data?.failed_count || 0);
      const total = Number(resp.data?.count || normalized.length);
      setPatchLog((prev) => [`${nowStamp()} expert batch patch ${total - failedCount}/${total} successful`, ...prev].slice(0, 40));
      setGlitchBurstKey((prev) => prev + 1);

      const failedResults = Array.isArray(resp.data?.results) ? resp.data.results.filter((item) => item.status !== "success") : [];
      if (failedResults.length) {
        failedResults.slice(0, 8).forEach((item) => {
          setPatchLog((prev) => [
            `${nowStamp()} failed offset 0x${Number(item.offset).toString(16).toUpperCase()} (${item.error || "unknown error"})`,
            ...prev
          ].slice(0, 40));
        });
        setErrorMessage(`Batch finished with ${failedResults.length} failed rows.`);
      }
    } catch (err) {
      setErrorMessage(err.response?.data?.detail || err.message);
    } finally {
      setIsBatchPatching(false);
    }
  };

  const handleUpdateSemanticDraft = (recordId, fieldId, value) => {
    setSemanticDrafts((prev) => ({
      ...prev,
      [draftKey(recordId, fieldId)]: value
    }));
  };

  const handleToggleSemanticFieldConsent = (recordId, fieldId, checked) => {
    setSemanticFieldConsents((prev) => ({
      ...prev,
      [draftKey(recordId, fieldId)]: checked
    }));
  };

  const handleToggleSemanticIdentityConsent = (recordId, checked) => {
    setSemanticIdentityConsents((prev) => ({
      ...prev,
      [recordId]: checked
    }));
  };

  const handleQueueSemanticPatch = (record, field) => {
    if (record.classification === "environment") {
      setErrorMessage(`Semantic patching is disabled for scene/environment record ${record.label}. Use Expert Mode for raw offsets.`);
      return;
    }

    const fieldConsentKey = draftKey(record.record_id, field.field_id);
    const raw = semanticDrafts[fieldConsentKey];
    if (raw === undefined || raw === "") {
      setErrorMessage(`Enter a new value for ${field.label} before staging.`);
      return;
    }

    const parsed = field.value_type === "f32" ? Number(raw) : parseInt(raw, 10);
    if (Number.isNaN(parsed)) {
      setErrorMessage(`Invalid value for ${field.label}.`);
      return;
    }

    if (field.status === "ambiguous" && !semanticFieldConsents[fieldConsentKey]) {
      setErrorMessage(`Explicit consent is required before patching ambiguous field ${field.label}.`);
      return;
    }

    if (isSemanticIdentityRisky(record) && !semanticIdentityConsents[record.record_id]) {
      setErrorMessage(`Explicit consent is required before patching inferred record ${record.label}.`);
      return;
    }

    const nextItem = {
      id: fieldConsentKey,
      record_id: record.record_id,
      record_label: record.label,
      field_id: field.field_id,
      field_label: field.label,
      field,
      old_value: field.value,
      value: parsed,
      allow_ambiguous: field.status === "ambiguous",
      allow_identity_ambiguous: isSemanticIdentityRisky(record)
    };

    setSemanticQueue((prev) => {
      const filtered = prev.filter((item) => item.id !== nextItem.id);
      return [...filtered, nextItem];
    });
    setPatchLog((prev) => [`${nowStamp()} staged semantic patch ${record.label} -> ${field.field_id} = ${parsed}`, ...prev].slice(0, 40));
  };

  const handleRemoveSemanticPatch = (itemId) => {
    setSemanticQueue((prev) => prev.filter((item) => item.id !== itemId));
  };

  const handleApplySemanticPatches = async () => {
    setErrorMessage("");

    if (!patchFile.trim()) {
      setErrorMessage("Target file is required for semantic patching.");
      return;
    }
    if (!semanticQueue.length) {
      setErrorMessage("Stage at least one semantic patch first.");
      return;
    }

    setIsSemanticPatching(true);
    try {
      const resp = await axios.post(`${API_BASE}/naheulbeuk/patch-batch-semantic`, {
        filepath: patchFile,
        patches: semanticQueue.map((item) => ({
          record_id: item.record_id,
          field_id: item.field_id,
          value: item.value,
          allow_ambiguous: item.allow_ambiguous,
          allow_identity_ambiguous: item.allow_identity_ambiguous
        })),
        backup: true
      });

      const results = Array.isArray(resp.data?.results) ? resp.data.results : [];
      const verifiedCount = results.filter((item) => item.verified).length;
      setPatchLog((prev) => [`${nowStamp()} semantic batch ${verifiedCount}/${results.length || semanticQueue.length} verified`, ...prev].slice(0, 40));
      setSemanticQueue([]);
      setGlitchBurstKey((prev) => prev + 1);
      await loadSemanticInspect(patchFile, { silent: true });

      if (resp.data?.status !== "success") {
        setErrorMessage("Semantic patch batch finished with verification issues.");
      }
    } catch (err) {
      setErrorMessage(err.response?.data?.detail || err.message);
    } finally {
      setIsSemanticPatching(false);
    }
  };

  const handleSaveChange = (index, value) => {
    setSaves((prev) => {
      const next = [...prev];
      next[index] = value;
      return next;
    });
    if (index === 0 && !String(patchFile || "").trim()) {
      setPatchFile(value);
    }
  };

  const handleValueChange = (index, value) => {
    setValues((prev) => {
      const next = [...prev];
      next[index] = value;
      return next;
    });
  };

  const openSavePicker = (index) => {
    setSavePickerIndex(index);
    setSavePickerOpen(true);
  };

  const closeSavePicker = () => setSavePickerOpen(false);
  const closePatchPicker = () => setPatchPickerOpen(false);

  return (
    <div className="app-shell crt-mask" data-fx-level={FX_LEVEL}>
      <div className="ambient ambient-a" />
      <div className="ambient ambient-b" />
      <div className="ambient ambient-c" />

      <main className="main-wrap dashboard-grid">
        <div className="dashboard-area-header">
          <HeaderBar
            backendState={backendState}
            profilesCount={profiles.length}
            candidatesCount={candidates.length}
            topScore={candidateStats.topScore}
            avgScore={candidateStats.avgScore}
            apiBase={API_BASE}
            logoSrc={logo}
          />
        </div>

        <AnimatePresence>
          {errorMessage && (
            <motion.div
              className="panel panel-cyber pixel-border warning-row dashboard-warning"
              initial={{ opacity: 0, y: -4 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -6 }}
              transition={{ duration: 0.2 }}
            >
              <TriangleAlert size={16} />
              <p>{errorMessage}</p>
            </motion.div>
          )}
        </AnimatePresence>

        <div className="dashboard-area-saves">
          <section className="panel panel-cyber pixel-border card-stack panel-density workflow-panel">
            <div className="card-head">
              <h2 className="card-title">
                <ShieldCheck size={16} />
                Naheulbeuk Workflow
              </h2>
              <p className="card-subtitle">Choose one save, inspect typed records, then patch only through the semantic queue.</p>
            </div>

            <div className="workflow-toolbar">
              <div className="workflow-copy">
                <p className="mono faint">Target save</p>
                <p className="semantic-target-path mono">{patchFile || "No target save selected"}</p>
              </div>

              <div className="workflow-actions">
                <button type="button" className="btn-sub btn-neon-sub" onClick={() => setPatchPickerOpen(true)}>
                  <FolderOpen size={14} />
                  Choose Save
                </button>
                <button
                  type="button"
                  className="btn-sub btn-neon-sub"
                  onClick={() => {
                    loadSemanticDoctor(patchFile, { silent: false });
                    if (patchFile) {
                      loadSemanticInspect(patchFile, { silent: false });
                    }
                  }}
                  disabled={semanticLoading || semanticDoctorLoading}
                >
                  <RefreshCcw size={14} className={semanticLoading || semanticDoctorLoading ? "animate-spin" : ""} />
                  Refresh
                </button>
              </div>
            </div>

            {semanticDoctor && (
              <div className={`workflow-status workflow-status-${semanticDoctor.status}`}>
                <p className="workflow-status-title">
                  Doctor: {semanticDoctor.status} | {semanticDoctor.mode}
                </p>
                <p className="mono faint">
                  data root: {semanticDoctor.data_root || "not discovered"} | env: {semanticDoctor.game_dir_env}
                </p>
                {!!semanticDoctor.probe_save && semanticDoctor.probe_save.status === "ok" && (
                  <p className="mono faint">
                    probe: {semanticDoctor.probe_save.character_count} character records | {semanticDoctor.probe_save.safe_count} safe | {semanticDoctor.probe_save.risky_count} risky | {semanticDoctor.probe_save.unresolved_count} unresolved
                  </p>
                )}
              </div>
            )}

            {!!semanticDoctor?.warnings?.length && (
              <div className="workflow-warning-list">
                {semanticDoctor.warnings.map((warning, index) => (
                  <p key={`${warning}-${index}`} className="mono faint">
                    {warning}
                  </p>
                ))}
              </div>
            )}
          </section>
        </div>

        <div className="dashboard-area-chars">
          <CharacterTabsPanel
            allRecords={semanticCharacters}
            records={visibleSemanticCharacters}
            selectedRecordId={selectedRecord?.record_id || ""}
            onChangeRecord={setSelectedRecordId}
            riskFilter={recordRiskFilter}
            classificationFilter={recordClassFilter}
            onChangeRiskFilter={setRecordRiskFilter}
            onChangeClassificationFilter={setRecordClassFilter}
            isLoading={semanticLoading}
            patchFile={patchFile}
          />
        </div>

        <div className="dashboard-area-matrix matrix-stack">
          <StatsEditorPanel
            patchFile={patchFile}
            selectedProfile={selectedProfile}
            profiles={profiles}
            profileFieldCount={profileFieldCount}
            semanticModel={semanticModel}
            semanticLoading={semanticLoading}
            selectedRecord={selectedRecord}
            semanticDrafts={semanticDrafts}
            semanticQueue={semanticQueue}
            semanticFieldConsents={semanticFieldConsents}
            semanticIdentityConsents={semanticIdentityConsents}
            economyRecords={economyRecords}
            isSemanticPatching={isSemanticPatching}
            expertBatchRows={batchRows}
            expertCharacters={expertCharacters}
            onSelectProfile={setSelectedProfile}
            onRefreshSemantic={() => loadSemanticInspect(patchFile, { silent: false })}
            onUpdateSemanticDraft={handleUpdateSemanticDraft}
            onToggleSemanticFieldConsent={handleToggleSemanticFieldConsent}
            onToggleSemanticIdentityConsent={handleToggleSemanticIdentityConsent}
            onQueueSemanticPatch={handleQueueSemanticPatch}
            onRemoveSemanticPatch={handleRemoveSemanticPatch}
            onApplySemanticPatches={handleApplySemanticPatches}
            onOpenPatchPicker={() => setPatchPickerOpen(true)}
            showExpertTools={false}
            onLoadProfileFields={loadProfileFields}
            onImportTopCandidates={importTopCandidates}
            onAddRow={addBatchRow}
            onUpdateRow={updateBatchRow}
            onRemoveRow={removeBatchRow}
          />
        </div>

        <div className="dashboard-area-actions">
          <section className="panel panel-cyber pixel-border card-stack panel-density workflow-side-panel">
            <div className="card-head">
              <h2 className="card-title">
                <RefreshCcw size={16} />
                Session State
              </h2>
              <p className="card-subtitle">Mainline semantic editing is the supported path. Raw scan and offset patching live in Expert Mode below.</p>
            </div>

            <div className="workflow-side-metrics">
              <div className="metric-card">
                <div className="metric-head">
                  <span className="metric-label">Selected Record</span>
                </div>
                <p className="metric-value">{selectedRecord?.label || "None"}</p>
                <p className="metric-helper mono">{selectedRecord?.record_id || "Choose a target save and record."}</p>
              </div>

              <div className="metric-card">
                <div className="metric-head">
                  <span className="metric-label">Queue</span>
                </div>
                <p className="metric-value">{semanticQueue.length}</p>
                <p className="metric-helper mono">staged semantic patch{semanticQueue.length === 1 ? "" : "es"}</p>
              </div>

              <div className="metric-card">
                <div className="metric-head">
                  <span className="metric-label">Record Visibility</span>
                </div>
                <p className="metric-value">{visibleSemanticCharacters.length}</p>
                <p className="metric-helper mono">visible out of {semanticCharacters.length} typed records</p>
              </div>
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
                <p className="mono faint">No semantic activity yet. Pick a save, inspect records, then stage a patch.</p>
              )}
            </div>
          </section>
        </div>
      </main>

      <details className="expert-shell">
        <summary>Expert Mode: raw scan and offset patching</summary>
        <div className="expert-grid">
          <SaveSelectorsPanel
            saves={saves}
            values={values}
            width={width}
            isScanning={isScanning}
            onOpenSavePicker={openSavePicker}
            onChangeValue={handleValueChange}
            onChangeWidth={setWidth}
            onScan={handleScan}
          />

          <CandidateMatrixPanel
            candidates={candidates}
            onLoadCandidate={loadCandidateIntoPatch}
            onQueueCandidate={queueCandidateInBatch}
            pulseKey={matrixPulseKey}
          />

          <ActionsPanel
            patchFile={patchFile}
            patchOffset={patchOffset}
            patchValue={patchValue}
            patchWidth={patchWidth}
            isPatching={isPatching}
            isBatchPatching={isBatchPatching}
            patchLog={patchLog}
            parseOffset={parseOffset}
            onChangePatchFile={setPatchFile}
            onChangePatchOffset={setPatchOffset}
            onChangePatchValue={setPatchValue}
            onChangePatchWidth={setPatchWidth}
            onOpenPatchPicker={() => setPatchPickerOpen(true)}
            onPatch={handlePatch}
            onBatchPatch={handleBatchPatch}
            glitchBurstKey={glitchBurstKey}
          />
        </div>
      </details>

      <FileExplorerModal
        open={savePickerOpen}
        apiBase={API_BASE}
        initialPath={saves[savePickerIndex] || "."}
        onClose={closeSavePicker}
        onSelectFile={(path) => handleSaveChange(savePickerIndex, path)}
      />

      <FileExplorerModal
        open={patchPickerOpen}
        apiBase={API_BASE}
        initialPath={patchFile || saves[0] || "."}
        onClose={closePatchPicker}
        onSelectFile={setPatchFile}
      />

      <footer className="footer-bar">
        <span>UESE backend on {API_BASE}</span>
        <span>Typed Naheulbeuk semantic editor + expert raw mode</span>
      </footer>
    </div>
  );
};

export default App;
