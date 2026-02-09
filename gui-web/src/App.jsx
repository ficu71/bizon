import React, { useState, useEffect } from 'react';
import axios from 'axios';
import {
  Search,
  Zap,
  FileSearch,
  Rocket,
  ChevronRight,
  Layers,
  AlertCircle,
  Database,
  Terminal,
  ExternalLink,
  Flame,
  Skull,
  TrendingUp,
  Trophy
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

const API_BASE = "http://localhost:8000";

const App = () => {
  const [activeTab, setActiveTab] = useState('scan');
  const [profiles, setProfiles] = useState([]);

  // Scan State
  const [saves, setSaves] = useState(['', '', '']);
  const [values, setValues] = useState(['', '', '']);
  const [width, setWidth] = useState(4);
  const [candidates, setCandidates] = useState([]);
  const [isScanning, setIsScanning] = useState(false);

  // Patch State
  const [patchFile, setPatchFile] = useState('');
  const [patchOffset, setPatchOffset] = useState('');
  const [patchValue, setPatchValue] = useState('');
  const [patchWidth, setPatchWidth] = useState(4);
  const [patchLog, setPatchLog] = useState([]);

  useEffect(() => {
    fetchProfiles();
  }, []);

  const fetchProfiles = async () => {
    try {
      const resp = await axios.get(`${API_BASE}/profiles`);
      setProfiles(resp.data);
    } catch (err) {
      console.error("Backend offline?", err);
    }
  };

  const handleScan = async () => {
    setIsScanning(true);
    try {
      const resp = await axios.post(`${API_BASE}/scan`, {
        saves: saves,
        values: values.map(v => parseInt(v || 0)),
        width: width,
        dtype: "auto"
      });
      setCandidates(resp.data);
    } catch (err) {
      alert("FAIL: " + (err.response?.data?.detail || err.message));
    } finally {
      setIsScanning(false);
    }
  };

  const handlePatch = async () => {
    try {
      const resp = await axios.post(`${API_BASE}/patch`, {
        filepath: patchFile,
        offset: patchOffset.startsWith('0x') ? parseInt(patchOffset, 16) : parseInt(patchOffset),
        width: patchWidth,
        value: parseInt(patchValue),
        backup: true
      });
      if (resp.data.status === 'success') {
        const logEntry = `DESTROYED ${patchFile.split('/').pop()} @ ${patchOffset} -> ${patchValue} (VERIFIED!)`;
        setPatchLog([logEntry, ...patchLog]);
      }
    } catch (err) {
      alert("CRITICAL ERROR: " + (err.response?.data?.detail || err.message));
    }
  };

  return (
    <div className="min-h-screen flex flex-col bg-[#050505] selection:bg-pink-500 selection:text-white">
      {/* GLITCH HEADER */}
      <header className="h-16 border-b-2 border-zinc-900 bg-black/80 backdrop-blur-md sticky top-0 z-50 flex items-center justify-between px-8">
        <div className="flex items-center space-x-4">
          <div className="flex items-center space-x-2">
            <Skull className="text-pink-500 animate-pulse" size={24} />
            <h1 className="font-black text-2xl tracking-tighter italic glitch-text" data-text="SAVE DESTROYER 3000">
              SAVE DESTROYER <span className="text-cyan-400">3000</span>
            </h1>
          </div>
          <div className="hidden md:flex space-x-1">
            <span className="text-[10px] bg-red-500/20 text-red-500 px-1 py-0.5 font-bold uppercase">Game Balance: BROKEN</span>
            <span className="text-[10px] bg-cyan-500/20 text-cyan-400 px-1 py-0.5 font-bold uppercase">Physics: OPTIONAL</span>
          </div>
        </div>

        <nav className="flex space-x-1">
          <TabButton icon={<FileSearch size={16} />} label="SCAN UNIVERSE" active={activeTab === 'scan'} onClick={() => setActiveTab('scan')} color="cyan" />
          <TabButton icon={<Zap size={16} />} label="YEET PATCH" active={activeTab === 'patch'} onClick={() => setActiveTab('patch')} color="pink" />
        </nav>
      </header>

      <div className="flex-1 flex flex-col p-8 space-y-8 max-w-7xl mx-auto w-full">
        <AnimatePresence mode="wait">
          {activeTab === 'scan' && (
            <motion.div
              key="scan"
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 20 }}
              className="space-y-8"
            >
              <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
                {/* LEFT: TARGETS */}
                <div className="lg:col-span-12 xl:col-span-7 space-y-6">
                  <SectionTitle icon={<Database size={20} />} title="TARGET SAVE DUMPS" />
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    {saves.map((s, i) => (
                      <div key={i} className="group flex flex-col space-y-2 bg-zinc-900/50 p-4 border-l-4 border-zinc-800 focus-within:border-cyan-500 transition-all">
                        <label className="text-[10px] font-black text-zinc-500 uppercase tracking-widest">
                          Silo {String.fromCharCode(65 + i)}
                        </label>
                        <input
                          className="bg-transparent border-none text-cyan-400 font-mono text-sm focus:ring-0 p-0"
                          placeholder="path/to/save.dat"
                          value={s}
                          onChange={(e) => {
                            const newSaves = [...saves];
                            newSaves[i] = e.target.value;
                            setSaves(newSaves);
                          }}
                        />
                      </div>
                    ))}
                  </div>

                  <SectionTitle icon={<Layers size={20} />} title="HACK PARAMETERS" />
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    <div className="md:col-span-2 grid grid-cols-3 gap-3">
                      {values.map((v, i) => (
                        <div key={i} className="space-y-1">
                          <label className="text-[10px] font-black text-zinc-500 uppercase">Val {String.fromCharCode(65 + i)}</label>
                          <input
                            className="w-full input-hacker text-center h-12 text-xl"
                            placeholder="69"
                            value={v}
                            onChange={(e) => {
                              const newVals = [...values];
                              newVals[i] = e.target.value;
                              setValues(newVals);
                            }}
                          />
                        </div>
                      ))}
                    </div>
                    <div className="space-y-1">
                      <label className="text-[10px] font-black text-zinc-500 uppercase">Memory Width</label>
                      <div className="flex h-12 border-2 border-zinc-800">
                        {[2, 4].map(w => (
                          <button
                            key={w}
                            onClick={() => setWidth(w)}
                            className={`flex-1 font-black ${width === w ? 'bg-cyan-500 text-black' : 'hover:bg-zinc-800 text-zinc-500'}`}
                          >
                            {w}B
                          </button>
                        ))}
                      </div>
                    </div>
                  </div>

                  <button
                    onClick={handleScan}
                    disabled={isScanning}
                    className="btn-hack w-full h-16 text-2xl flex items-center justify-center space-x-3"
                  >
                    {isScanning ? (
                      <span className="flex items-center space-x-2">
                        <div className="w-5 h-5 border-4 border-black border-t-transparent rounded-full animate-spin"></div>
                        <span>INFILTRATING...</span>
                      </span>
                    ) : (
                      <>
                        <Flame size={24} />
                        <span>INITIATE DESTRUCTION</span>
                      </>
                    )}
                  </button>
                </div>

                {/* RIGHT: LIVE STATUS */}
                <div className="lg:col-span-12 xl:col-span-5">
                  <div className="glass h-full p-6 border-2 border-pink-500/20 flex flex-col space-y-4">
                    <div className="flex items-center justify-between border-b border-white/10 pb-4">
                      <h3 className="font-black italic flex items-center space-x-2">
                        <TrendingUp className="text-pink-500" size={18} />
                        <span>STONKS ANALYZER</span>
                      </h3>
                      <span className="text-[10px] font-bold text-zinc-500">v2.0.4-BETA</span>
                    </div>

                    <div className="flex-1 space-y-4">
                      <div className="bg-emerald-500/10 p-4 border border-emerald-500/20 rounded">
                        <div className="flex items-center space-x-2 text-emerald-400 font-bold text-sm mb-1 text-glow">
                          <Trophy size={14} />
                          <span>ACHIEVEMENT UNLOCKED: STONKS MASTER</span>
                        </div>
                        <p className="text-[10px] text-emerald-400/60 uppercase">Wealth limit bypassed successfully.</p>
                      </div>

                      <div className="bg-black border border-white/5 p-4 font-mono text-[11px] text-zinc-400 leading-relaxed">
                        <p className="text-cyan-400 animate-pulse">{'>'} SYSTEM: READY TO HACK</p>
                        <p className="text-zinc-600 italic mt-2">// Ensure all save files are from the same game version to avoid reality collapse.</p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* CANDIDATES TABLE */}
              {candidates.length > 0 && (
                <section className="border-4 border-zinc-900 bg-black overflow-hidden shadow-[20px_20px_0px_rgba(39,39,42,1)]">
                  <div className="bg-zinc-900 p-4 flex justify-between items-center">
                    <h3 className="font-black uppercase tracking-widest italic text-xl">VULNERABILITIES DETECTED: {candidates.length}</h3>
                    <span className="bg-red-600 text-white px-3 py-1 text-xs font-black animate-bounce">TOP SIGHTINGS</span>
                  </div>
                  <div className="overflow-x-auto">
                    <table className="w-full text-left">
                      <thead className="text-[10px] font-black text-zinc-500 uppercase tracking-tighter border-b-2 border-zinc-900">
                        <tr>
                          <th className="px-6 py-4">MEMORY ADDR</th>
                          <th className="px-6 py-4">DESTRUCTION CONFIDENCE</th>
                          <th className="px-6 py-4">RAW HEX DUMP</th>
                          <th className="px-6 py-4 text-right">ACTION</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y-2 divide-zinc-900">
                        {candidates.slice(0, 15).map((c, i) => (
                          <tr key={i} className="hover:bg-cyan-500/5 transition-colors">
                            <td className="px-6 py-4 font-mono font-bold text-cyan-400 text-lg tracking-wider italic">0x{c.offset.toString(16).toUpperCase()}</td>
                            <td className="px-6 py-4">
                              <div className="flex items-center space-x-3">
                                <div className="flex-1 h-3 bg-zinc-900 border border-white/5 overflow-hidden">
                                  <motion.div
                                    initial={{ width: 0 }}
                                    animate={{ width: `${Math.min(100, (c.score / 600) * 100)}%` }}
                                    className={`h-full ${c.score > 400 ? 'bg-pink-500 neon-border-pink' : 'bg-cyan-500'}`}
                                  />
                                </div>
                                <span className="font-black text-sm italic">{c.score}</span>
                              </div>
                            </td>
                            <td className="px-6 py-4 text-[10px] font-mono text-zinc-600">{c.context_hex}</td>
                            <td className="px-6 py-4 text-right">
                              <button
                                onClick={() => {
                                  setPatchFile(saves[0]);
                                  setPatchOffset('0x' + c.offset.toString(16));
                                  setActiveTab('patch');
                                }}
                                className="bg-white text-black font-black px-4 py-2 text-xs hover:bg-cyan-500 transition-all active:scale-95 italic uppercase"
                              >
                                Load Silo
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </section>
              )}
            </motion.div>
          )}

          {activeTab === 'patch' && (
            <motion.div
              key="patch"
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 1.05 }}
              className="max-w-4xl mx-auto space-y-12"
            >
              <div className="text-center space-y-4">
                <h2 className="text-6xl font-black italic tracking-tighter uppercase glitch-text" data-text="BERRONK THE SYSTEM">
                  BERRONK THE <span className="text-pink-500">SYSTEM</span>
                </h2>
                <p className="text-zinc-500 font-bold uppercase tracking-widest">Reality is whatever you want it to be.</p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-12">
                <div className="space-y-8">
                  <div className="space-y-6">
                    <div className="space-y-1">
                      <label className="text-[10px] font-black text-zinc-500 uppercase tracking-widest">Silo to Infiltrate</label>
                      <input className="w-full input-hacker p-4" placeholder="path/to/file.sav" value={patchFile} onChange={e => setPatchFile(e.target.value)} />
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                      <div className="space-y-1">
                        <label className="text-[10px] font-black text-zinc-500 uppercase">Target Addr</label>
                        <input className="w-full input-hacker p-4 text-center italic" placeholder="0x69" value={patchOffset} onChange={e => setPatchOffset(e.target.value)} />
                      </div>
                      <div className="space-y-1">
                        <label className="text-[10px] font-black text-zinc-500 uppercase">New Reality Value</label>
                        <input className="w-full input-hacker p-4 text-center text-pink-500 font-bold" placeholder="999999" value={patchValue} onChange={e => setPatchValue(e.target.value)} />
                      </div>
                    </div>
                    <button onClick={handlePatch} className="btn-hack w-full h-20 text-3xl">GO GOD MODE!</button>
                  </div>

                  <div className="bg-pink-500/10 border-l-4 border-pink-500 p-6 space-y-2">
                    <div className="flex items-center space-x-2 text-pink-500 font-bold">
                      <AlertCircle size={18} />
                      <span className="uppercase text-sm">Destruction Warning</span>
                    </div>
                    <p className="text-[10px] text-pink-500/80 uppercase font-bold tracking-tighter">
                      Applying this patch will irreversibly alter the balance of power. Backup drones are automatically deployed.
                    </p>
                  </div>
                </div>

                <div className="flex flex-col">
                  <div className="bg-zinc-900 flex-1 p-6 font-mono text-[11px] relative overflow-hidden flex flex-col">
                    <div className="absolute top-0 right-0 p-2 text-[10px] text-zinc-800 font-black tracking-tighter rotate-90 origin-top-right">DEBUG_KERNELv7</div>
                    <h4 className="text-zinc-500 font-black mb-4 border-b border-zinc-800 pb-2">COMMAND OUTPUT</h4>
                    <div className="flex-1 overflow-y-auto space-y-2 custom-scrollbar pr-2">
                      {patchLog.length === 0 && <p className="text-zinc-700 italic">Waiting for injection command...</p>}
                      {patchLog.map((log, i) => (
                        <motion.div
                          initial={{ opacity: 0, x: -10 }}
                          animate={{ opacity: 1, x: 0 }}
                          key={i}
                          className="text-pink-500"
                        >
                          {'>'} {log}
                        </motion.div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      <footer className="h-10 border-t border-zinc-900 bg-black flex items-center justify-center px-8 text-[9px] font-bold text-zinc-600 uppercase tracking-widest">
        Designed for ultimate destruction • UESE v2.0.4 • (C) 20XX BIZON INDUSTRIES
      </footer>
    </div>
  );
};

const TabButton = ({ icon, label, active, onClick, color }) => (
  <button
    onClick={onClick}
    className={`flex items-center space-x-2 px-6 py-2 transition-all font-black italic tracking-tighter text-sm skew-x-[-12deg] border-b-4 ${active ? (color === 'cyan' ? 'border-cyan-500 text-cyan-400 bg-cyan-500/10' : 'border-pink-500 text-pink-500 bg-pink-500/10') : 'border-transparent text-zinc-500 hover:text-white'}`}
  >
    <span className="skew-x-[12deg]">{icon}</span>
    <span className="skew-x-[12deg]">{label}</span>
  </button>
);

const SectionTitle = ({ icon, title }) => (
  <div className="flex items-center space-x-3 mb-2">
    <div className="p-2 bg-zinc-900 border border-white/5 text-cyan-500">{icon}</div>
    <h3 className="font-black uppercase tracking-tighter text-lg italic text-glow-cyan">{title}</h3>
  </div>
);

export default App;
