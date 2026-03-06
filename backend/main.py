#!/usr/bin/env python3
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from pathlib import Path

from uese.core.naheulbeuk_app import (
    NaheulbeukAppError,
    apply_naheulbeuk_semantic_patches,
    get_naheulbeuk_doctor_report,
    get_naheulbeuk_record,
    inspect_naheulbeuk as inspect_naheulbeuk_payload,
    list_naheulbeuk_records,
)
from uese.core.naheulbeuk_semantic import (
    SemanticPatchInput,
)
from uese.core.universal_scanner import UniversalScanner
from uese.core.patch_engine import PatchEngine
from uese.core.profile_manager import ProfileManager

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

class BatchPatchItem(BaseModel):
    offset: int
    width: int
    value: int
    label: Optional[str] = None
    character: Optional[str] = None

class BatchPatchRequest(BaseModel):
    filepath: str
    patches: List[BatchPatchItem]
    backup: bool = True


class SemanticPatchItem(BaseModel):
    record_id: str
    field_id: str
    value: float | int
    allow_ambiguous: bool = False
    allow_identity_ambiguous: bool = False


class SemanticPatchRequest(BaseModel):
    filepath: str
    record_id: str
    field_id: str
    value: float | int
    allow_ambiguous: bool = False
    allow_identity_ambiguous: bool = False
    backup: bool = True
    output_path: Optional[str] = None


class SemanticBatchPatchRequest(BaseModel):
    filepath: str
    patches: List[SemanticPatchItem]
    backup: bool = True
    output_path: Optional[str] = None

class DeltaScanRequest(BaseModel):
    saves: List[str]
    deltas: List[int]
    width: int = 4
    dtype: str = "auto"

class FileListEntry(BaseModel):
    name: str
    path: str
    is_dir: bool


def _raise_app_error(exc: NaheulbeukAppError) -> None:
    raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

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


@app.get("/naheulbeuk/inspect")
async def inspect_naheulbeuk(filepath: str):
    try:
        return inspect_naheulbeuk_payload(filepath)
    except NaheulbeukAppError as exc:
        _raise_app_error(exc)


@app.get("/naheulbeuk/doctor")
async def naheulbeuk_doctor(filepath: Optional[str] = None):
    try:
        return get_naheulbeuk_doctor_report(filepath)
    except NaheulbeukAppError as exc:
        _raise_app_error(exc)


@app.get("/naheulbeuk/characters")
async def list_naheulbeuk_characters(
    filepath: str,
    risk: str = "all",
    classification: str = "all",
):
    try:
        return list_naheulbeuk_records(filepath, risk=risk, classification=classification)
    except NaheulbeukAppError as exc:
        _raise_app_error(exc)


@app.get("/naheulbeuk/character/{character_id}")
async def get_naheulbeuk_character(character_id: str, filepath: str):
    try:
        return get_naheulbeuk_record(filepath, character_id)
    except NaheulbeukAppError as exc:
        _raise_app_error(exc)

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
        raise HTTPException(status_code=500, detail=str(e)) from e

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
        raise HTTPException(status_code=500, detail=str(e)) from e

@app.post("/patch-batch")
async def patch_save_batch(req: BatchPatchRequest):
    try:
        if not req.patches:
            raise HTTPException(status_code=400, detail="No patches provided")

        p = Path(req.filepath)
        if not p.exists():
            raise HTTPException(status_code=400, detail=f"File not found: {p}")

        results = []
        backup_done = False

        for i, patch in enumerate(req.patches):
            success = False
            verified = False
            error = None
            try:
                success = patcher.patch_value(
                    filepath=p,
                    offset=patch.offset,
                    width=patch.width,
                    value=patch.value,
                    backup=(req.backup and not backup_done)
                )
                if req.backup and not backup_done and success:
                    backup_done = True
                if success:
                    verified = patcher.verify_patch(p, patch.offset, patch.value, patch.width)
            except Exception as patch_error:
                error = str(patch_error)

            results.append({
                "index": i,
                "offset": patch.offset,
                "width": patch.width,
                "value": patch.value,
                "label": patch.label,
                "character": patch.character,
                "status": "success" if success else "failed",
                "verified": verified,
                "error": error
            })

        failed = [r for r in results if r["status"] != "success"]
        return {
            "status": "partial_failed" if failed else "success",
            "count": len(results),
            "failed_count": len(failed),
            "results": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/naheulbeuk/patch-semantic")
async def patch_naheulbeuk_semantic(req: SemanticPatchRequest):
    try:
        result = apply_naheulbeuk_semantic_patches(
            req.filepath,
            [
                SemanticPatchInput(
                    record_id=req.record_id,
                    field_id=req.field_id,
                    value=req.value,
                    allow_ambiguous=req.allow_ambiguous,
                    allow_identity_ambiguous=req.allow_identity_ambiguous,
                )
            ],
            backup=req.backup,
            output_path=Path(req.output_path).expanduser() if req.output_path else None,
        )
        return result
    except NaheulbeukAppError as exc:
        _raise_app_error(exc)


@app.post("/naheulbeuk/patch-batch-semantic")
async def patch_naheulbeuk_semantic_batch(req: SemanticBatchPatchRequest):
    try:
        if not req.patches:
            raise HTTPException(status_code=400, detail="No semantic patches provided")

        result = apply_naheulbeuk_semantic_patches(
            req.filepath,
            [
                SemanticPatchInput(
                    record_id=item.record_id,
                    field_id=item.field_id,
                    value=item.value,
                    allow_ambiguous=item.allow_ambiguous,
                    allow_identity_ambiguous=item.allow_identity_ambiguous,
                )
                for item in req.patches
            ],
            backup=req.backup,
            output_path=Path(req.output_path).expanduser() if req.output_path else None,
        )
        return result
    except HTTPException:
        raise
    except NaheulbeukAppError as exc:
        _raise_app_error(exc)

@app.get("/list-files")
async def list_files(path: str = ".", pattern: str = "*", include_dirs: bool = False):
    try:
        root = Path(path).expanduser()
        if not root.exists():
            return []

        if root.is_file():
            root = root.parent

        if not root.is_dir():
            return []

        if include_dirs:
            entries = []
            for item in sorted(root.iterdir(), key=lambda f: (not f.is_dir(), f.name.lower())):
                if item.is_dir() or (item.is_file() and item.match(pattern)):
                    entries.append({
                        "name": item.name,
                        "path": str(item.absolute()),
                        "is_dir": item.is_dir()
                    })
            return entries

        files = list(root.glob(pattern))
        return [str(f.absolute()) for f in files if f.is_file()]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
