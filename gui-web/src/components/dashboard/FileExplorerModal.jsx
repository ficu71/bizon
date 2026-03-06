import { useEffect, useMemo, useState } from "react";
import axios from "axios";
import { AnimatePresence, motion } from "framer-motion";
import { ChevronUp, File, Folder, RefreshCw, X } from "lucide-react";

const normalizePath = (value) => String(value || "").trim() || ".";

const getParentPath = (value) => {
  const raw = normalizePath(value);
  if (raw === "." || raw === "/") return raw;

  const normalized = raw.replace(/[/\\]+$/, "");
  const unixIdx = normalized.lastIndexOf("/");
  const winIdx = normalized.lastIndexOf("\\");
  const idx = Math.max(unixIdx, winIdx);

  if (idx <= 0) {
    if (/^[A-Za-z]:/.test(normalized)) {
      return `${normalized.slice(0, 2)}\\`;
    }
    return "/";
  }
  return normalized.slice(0, idx);
};

const normalizeEntries = (payload) => {
  if (!Array.isArray(payload)) return [];

  return payload
    .map((entry) => {
      if (typeof entry === "string") {
        const parts = entry.split(/[/\\]/).filter(Boolean);
        return {
          name: parts[parts.length - 1] || entry,
          path: entry,
          is_dir: false
        };
      }
      if (entry && typeof entry === "object") {
        return {
          name: String(entry.name || ""),
          path: String(entry.path || ""),
          is_dir: Boolean(entry.is_dir)
        };
      }
      return null;
    })
    .filter(Boolean)
    .sort((a, b) => {
      if (a.is_dir !== b.is_dir) {
        return a.is_dir ? -1 : 1;
      }
      return a.name.localeCompare(b.name);
    });
};

const FileExplorerModal = ({ open, apiBase, initialPath = ".", onClose, onSelectFile }) => {
  const [currentPath, setCurrentPath] = useState(normalizePath(initialPath));
  const [entries, setEntries] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    if (!open) return;
    setCurrentPath(normalizePath(initialPath));
  }, [open, initialPath]);

  useEffect(() => {
    if (!open) return;

    let cancelled = false;

    const load = async () => {
      setIsLoading(true);
      setError("");

      try {
        const response = await axios.get(`${apiBase}/list-files`, {
          params: {
            path: currentPath,
            pattern: "*",
            include_dirs: true
          }
        });

        if (cancelled) return;
        setEntries(normalizeEntries(response.data));
      } catch (err) {
        if (cancelled) return;
        setError(err.response?.data?.detail || err.message || "Failed to load directory");
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    };

    load();

    return () => {
      cancelled = true;
    };
  }, [apiBase, currentPath, open, reloadKey]);

  const canGoUp = useMemo(() => {
    const normalized = normalizePath(currentPath);
    if (normalized === "." || normalized === "/") return false;
    if (/^[A-Za-z]:[/\\]*$/.test(normalized)) return false;
    return true;
  }, [currentPath]);

  const handleEntryClick = (entry) => {
    if (entry.is_dir) {
      setCurrentPath(entry.path);
      return;
    }

    onSelectFile(entry.path);
    onClose();
  };

  const handleBackdropClick = (event) => {
    if (event.target === event.currentTarget) {
      onClose();
    }
  };

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          className="file-explorer-backdrop"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.18 }}
          onClick={handleBackdropClick}
        >
          <motion.div
            className="panel panel-cyber pixel-border file-explorer-modal"
            initial={{ opacity: 0, y: 14, scale: 0.985 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 12, scale: 0.99 }}
            transition={{ duration: 0.18 }}
          >
            <div className="card-head">
              <h2 className="card-title">File Explorer</h2>
              <p className="card-subtitle">Wybierz plik save bez ręcznego wpisywania ścieżki.</p>
            </div>

            <div className="file-explorer-toolbar">
              <button
                type="button"
                className="btn-sub btn-neon-sub"
                onClick={() => setCurrentPath(getParentPath(currentPath))}
                disabled={!canGoUp || isLoading}
              >
                <ChevronUp size={14} />
                Up
              </button>

              <button
                type="button"
                className="btn-sub btn-neon-sub"
                onClick={() => setReloadKey((prev) => prev + 1)}
                disabled={isLoading}
              >
                <RefreshCw size={14} />
                Refresh
              </button>

              <div className="file-explorer-path mono" title={currentPath}>
                {currentPath}
              </div>

              <button type="button" className="btn-sub btn-neon-sub" onClick={onClose}>
                <X size={14} />
                Zamknij
              </button>
            </div>

            <div className="file-explorer-list">
              {isLoading && <p className="mono faint">Loading directory...</p>}

              {!isLoading && error && <p className="mono text-red-300">{error}</p>}

              {!isLoading && !error && !entries.length && <p className="mono faint">No files in this location.</p>}

              {!isLoading && !error && entries.length > 0 && (
                <div className="file-explorer-list-inner">
                  {entries.map((entry) => (
                    <button
                      key={`${entry.path}-${entry.is_dir ? "dir" : "file"}`}
                      type="button"
                      className={`file-explorer-entry ${entry.is_dir ? "file-explorer-entry-dir" : "file-explorer-entry-file"}`}
                      onClick={() => handleEntryClick(entry)}
                    >
                      <span className="file-explorer-entry-icon">{entry.is_dir ? <Folder size={16} /> : <File size={16} />}</span>
                      <span className="file-explorer-entry-name">{entry.name}</span>
                      <span className="file-explorer-entry-meta mono faint">{entry.is_dir ? "DIR" : "FILE"}</span>
                    </button>
                  ))}
                </div>
              )}
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};

export default FileExplorerModal;
