"""EpiSwarm Studio v2 - Case Files API endpoints."""

from __future__ import annotations
import io
from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, PlainTextResponse, Response
from pydantic import BaseModel, Field

from episwarm.service.case_file import CaseFileService, CaseFileManifest

router = APIRouter(prefix="/case-files", tags=["v2-case-files"])
case_file_service = CaseFileService()


class CreateCaseFileRequest(BaseModel):
    title: str
    description: str = ""
    author: str = "Regional Health Authority"


class DuplicateCaseFileRequest(BaseModel):
    new_title: str


class UpdateSectionRequest(BaseModel):
    data: Dict[str, Any]
    user: str = "health_authority_officer"


class LockCaseFileRequest(BaseModel):
    run_id: str


@router.get("", response_model=List[Dict[str, Any]])
def list_case_files():
    """List all available Case Files with metadata and completion percentages."""
    return case_file_service.list_case_files()


@router.post("", response_model=Dict[str, Any])
def create_case_file(req: CreateCaseFileRequest):
    """Create a new empty Case File for an official intake session."""
    manifest = case_file_service.create_case_file(title=req.title, description=req.description, author=req.author)
    return manifest.model_dump()


@router.get("/estimate", response_model=Dict[str, Any])
def estimate_parameters(region_name: str = "Metropolitan Area", population: int = 500000):
    """Propose empirical distributions with citations as Class C assumptions for intake."""
    return case_file_service.estimate_parameters(region_name=region_name, population=population)


@router.get("/templates/{template_name}")
def download_template(template_name: str):
    """Provide downloadable CSV templates for areas, households, hospitals, and commute matrix."""
    templates = {
        "areas.csv": "area_id,area_name,population,density_sq_km,risk_tier\narea_1,Central,125000,4500,low\narea_2,North,85000,2800,low\n",
        "hospitals.csv": "hospital_name,area_id,acute_beds,icu_beds,staff_count\nSt Jude Regional,area_1,450,45,320\nNorth General,area_2,280,24,180\n",
        "commute_matrix.csv": "origin_id,destination_id,commute_volume,transit_mode\narea_1,area_2,14200,rail\narea_2,area_1,15800,rail\n",
    }
    if template_name not in templates:
        raise HTTPException(status_code=404, detail=f"Template '{template_name}' not found. Available: {list(templates.keys())}")
    return PlainTextResponse(content=templates[template_name], media_type="text/csv", headers={"Content-Disposition": f"attachment; filename={template_name}"})


@router.get("/{case_id}", response_model=Dict[str, Any])
def get_case_file(case_id: str):
    """Retrieve complete Case File manifest with all 8 intake sections and evidence ledger."""
    try:
        manifest = case_file_service.get_case_file(case_id)
        return manifest.model_dump()
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.put("/{case_id}/sections/{section_key}", response_model=Dict[str, Any])
def update_section(case_id: str, section_key: str, req: UpdateSectionRequest):
    """Update one of the 8 intake sections, logging author provenance and updating completeness."""
    try:
        manifest = case_file_service.update_section(case_id, section_key, req.data, user=req.user)
        return manifest.model_dump()
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{case_id}/duplicate", response_model=Dict[str, Any])
def duplicate_case_file(case_id: str, req: DuplicateCaseFileRequest):
    """Duplicate a Case File (e.g. branch from a reference demo into an authority's local file)."""
    try:
        new_manifest = case_file_service.duplicate_case_file(case_id, new_title=req.new_title)
        return new_manifest.model_dump()
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{case_id}/lock", response_model=Dict[str, Any])
def lock_case_file(case_id: str, req: LockCaseFileRequest):
    """Lock a Case File version to freeze inputs for an official simulation run."""
    try:
        manifest = case_file_service.lock_version(case_id, run_id=req.run_id)
        return manifest.model_dump()
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{case_id}/upload")
async def upload_case_data(
    case_id: str,
    section_key: str = Form(...),
    column_mapping: str = Form("{}"),
    file: UploadFile = File(...)
):
    """Upload CSV data file, hash it, attach to case file, and mark with user_supplied evidence class."""
    import json
    try:
        content = await file.read()
        mapping = json.loads(column_mapping)
        res = case_file_service.attach_user_csv(
            case_id=case_id,
            section_key=section_key,
            filename=file.filename or "uploaded.csv",
            content_bytes=content,
            column_mapping=mapping
        )
        return res
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{case_id}/export")
def export_bundle(case_id: str):
    """Export complete Case File as a verified zip bundle with SHA-256 checksums."""
    try:
        zip_path = case_file_service.export_bundle(case_id)
        return FileResponse(
            path=str(zip_path),
            filename=f"{case_id}_bundle.zip",
            media_type="application/zip"
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

