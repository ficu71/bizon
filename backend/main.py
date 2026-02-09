#!/usr/bin/env python3
from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Tuple
from pathlib import Path
import os

from uese.core.universal_scanner import UniversalScanner, ScanCandidate
from uese.core.patch_engine import PatchEngine
from uese.core.profile_manager import ProfileManager, GameProfile

app = FastAPI(title="UESE Backend API")

# Enable CORS for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

scanner = UniversalScanner()
patcher = PatchEngine()
profile_manager = ProfileManager()

class ScanRequest(BaseModel):
    saves: List[str]
    values: List[int]
    width: int = 4
    dtype: str = "auto"
    exclude: List[str] = ["png", "entropy"]

class PatchRequest(BaseModel):
    filepath: str
    offset: int
    width: int
    value: int
    backup: bool = True

class DeltaScanRequest(BaseModel):
    saves: List[str]
    deltas: List[int]
    width: int = 4
    dtype: str = "auto"

@app.get("/profiles")
async def list_profiles():
    return profile_manager.list_profiles()

@app.get("/profiles/{game_id}")
async def get_profile(game_id: str):
    profile = profile_manager.load_profile(game_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return {
        "game_id": profile.game_id,
        "name": profile.name,
        "engine": profile.engine,
        "fields": profile.fields,
        "save_pattern": profile.save_pattern
    }

@app.post("/scan")
async def scan_saves(req: ScanRequest):
    try:
        save_paths = [Path(s) for s in req.saves]
        for p in save_paths:
            if not p.exists():
                raise HTTPException(status_code=400, detail=f"File not found: {p}")
        
        candidates = scanner.scan_saves(
            save_paths[0], save_paths[1], save_paths[2],
            values=tuple(req.values),
            width=req.width,
            dtype=req.dtype,
            exclude=req.exclude
        )
        return candidates
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/patch")
async def patch_save(req: PatchRequest):
    try:
        p = Path(req.filepath)
        success = patcher.patch_value(
            filepath=p,
            offset=req.offset,
            width=req.width,
            value=req.value,
            backup=req.backup
        )
        if success:
            verified = patcher.verify_patch(p, req.offset, req.value, req.width)
            return {"status": "success", "verified": verified}
        return {"status": "failed"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/list-files")
async def list_files(path: str = ".", pattern: str = "*"):
    try:
        root = Path(path).expanduser()
        if not root.exists():
            return []
        files = list(root.glob(pattern))
        return [str(f.absolute()) for f in files if f.is_file()]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
