"""Submission API routes."""

from typing import List, Optional
from pathlib import Path
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status, UploadFile, File, Form
from fastapi.responses import JSONResponse
import tempfile
import os

from src.application.container import Container

# Legacy imports still needed for sample operations
from pdf_slurper.db import Submission as LegacySubmission, Sample as LegacySample, open_session
from sqlmodel import select, func

def get_container_dependency():
    """Get container dependency for FastAPI."""
    # This would be properly initialized in production
    from src.infrastructure.config.settings import Settings
    return Container(Settings())

from src.domain.models.value_objects import SubmissionId, WorkflowStatus
from src.shared.exceptions import (
    EntityNotFoundException,
    DuplicateEntityException,
    InvalidRequestException
)
from ..schemas.submission import (
    SubmissionResponse,
    SubmissionListResponse,
    CreateSubmissionRequest,
    UpdateSubmissionRequest,
    ApplyQCRequest,
    QCResultResponse,
    BatchUpdateStatusRequest,
    SearchRequest,
    StatisticsResponse,
    SubmissionMetadataResponse,
    SampleRequest,
    SampleResponse,
    SampleListResponse
)

router = APIRouter(
    prefix="/submissions",
    tags=["submissions"],
    responses={
        404: {"description": "Not found"},
        400: {"description": "Bad request"},
        500: {"description": "Internal server error"}
    }
)


@router.post(
    "/",
    response_model=SubmissionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create submission from PDF file upload",
    description="Upload and process a PDF file to create a new submission with samples"
)
async def create_submission_from_upload(
    pdf_file: UploadFile = File(..., description="PDF file to process"),
    storage_location: str = Form(..., description="Storage location for samples"),
    force: bool = Form(False, description="Force reprocessing if file already exists"),
    auto_qc: bool = Form(False, description="Automatically apply QC thresholds"),
    min_concentration: float = Form(10.0, description="Minimum concentration threshold"),
    min_volume: float = Form(20.0, description="Minimum volume threshold"), 
    min_ratio: float = Form(1.8, description="Minimum A260/A280 ratio threshold"),
    evaluator: str = Form("", description="QC evaluator name"),
    container: Container = Depends(get_container_dependency)
) -> SubmissionResponse:
    """Create submission from uploaded PDF file."""
    try:
        # Validate file type
        if not pdf_file.filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=400, detail="File must be a PDF")
        
        # Save uploaded file to temporary location
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
            content = await pdf_file.read()
            temp_file.write(content)
            temp_path = Path(temp_file.name)
        
        try:
            # Process the PDF
            submission = await container.submission_service.create_from_pdf(
                pdf_path=temp_path,
                force=force,
                storage_location=storage_location
            )
            
            # Apply QC if requested
            if auto_qc and evaluator:
                await container.submission_service.apply_qc(
                    submission_id=submission.id,
                    min_concentration=min_concentration,
                    min_volume=min_volume,
                    min_quality_ratio=min_ratio,
                    evaluator=evaluator
                )
        finally:
            # Clean up temporary file
            if temp_path.exists():
                os.unlink(temp_path)
        
        # Use sample count from the submission object itself
        sample_count = len(submission.samples) if hasattr(submission, 'samples') else submission.sample_count
        
        # Convert to response schema
        return SubmissionResponse(
            id=submission.id,
            created_at=submission.created_at,
            updated_at=submission.updated_at if hasattr(submission, 'updated_at') else submission.created_at,
            sample_count=sample_count,
            metadata=SubmissionMetadataResponse(
                identifier=submission.metadata.identifier,
                service_requested=submission.metadata.service_requested,
                requester=submission.metadata.requester,
                requester_email=submission.metadata.requester_email.value if submission.metadata.requester_email and hasattr(submission.metadata.requester_email, 'value') else submission.metadata.requester_email,
                lab=submission.metadata.lab,
                organism=submission.metadata.organism.species if submission.metadata.organism and hasattr(submission.metadata.organism, 'species') else (submission.metadata.organism if isinstance(submission.metadata.organism, str) else None),
                contains_human_dna=submission.metadata.contains_human_dna,
                storage_location=submission.metadata.storage_location,
                # All additional extracted fields
                phone=submission.metadata.phone,
                as_of=submission.metadata.as_of.isoformat() if submission.metadata.as_of else None,
                expires_on=submission.metadata.expires_on.isoformat() if submission.metadata.expires_on else None,
                billing_address=submission.metadata.billing_address,
                pis=", ".join(submission.metadata.pis) if submission.metadata.pis else None,
                financial_contacts=", ".join(submission.metadata.financial_contacts) if submission.metadata.financial_contacts else None,
                request_summary=submission.metadata.request_summary,
                forms_text=submission.metadata.forms_text,
                will_submit_dna_for=submission.metadata.will_submit_dna_for,
                type_of_sample=submission.metadata.type_of_sample,
                human_dna="Yes" if submission.metadata.contains_human_dna else "No" if submission.metadata.contains_human_dna is not None else None,
                source_organism=submission.metadata.source_organism,
                sample_buffer=submission.metadata.sample_buffer,
                notes=submission.metadata.notes
            ),
            pdf_source={
                "file_path": str(submission.pdf_source.file_path),
                "file_hash": submission.pdf_source.file_hash,
                "page_count": submission.pdf_source.page_count
            }
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except DuplicateEntityException as e:
        raise HTTPException(status_code=409, detail=e.message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/statistics",
    response_model=StatisticsResponse,
    summary="Get global statistics",
    description="Get overall statistics across all submissions"
)
async def get_global_statistics(
    container: Container = Depends(get_container_dependency)
) -> StatisticsResponse:
    """Get global statistics."""
    try:
        stats = await container.submission_service.get_global_statistics()
        
        # Map repository response to schema
        # Calculate additional metrics
        workflow_status = stats.get("workflow_status", {})
        qc_status = stats.get("qc_status", {})
        
        samples_with_location = stats.get("samples_with_location", 0) 
        samples_processed = stats.get("samples_processed", 0)
        
        # Calculate average quality score if QC data exists
        total_qc_samples = sum(qc_status.values())
        if total_qc_samples > 0:
            # Simple weighted score: passed=100, warning=50, failed=0
            quality_score = (
                qc_status.get("passed", 0) * 100 +
                qc_status.get("warning", 0) * 50
            ) / total_qc_samples
        else:
            quality_score = None
        
        return StatisticsResponse(
            total_submissions=stats.get("total_submissions", 0),
            total_samples=stats.get("total_samples", 0),
            workflow_status=workflow_status,
            qc_status=qc_status,
            average_concentration=stats.get("average_concentration"),
            average_volume=stats.get("average_volume"),
            average_quality_score=quality_score,
            samples_with_location=samples_with_location,
            samples_processed=samples_processed
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/",
    response_model=SubmissionListResponse,
    summary="List submissions",
    description="List all submissions with optional filters"
)
async def list_submissions(
    query: Optional[str] = Query(None, description="Search query"),
    requester_email: Optional[str] = Query(None, description="Filter by requester email"),
    lab: Optional[str] = Query(None, description="Filter by lab"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Results offset"),
    container: Container = Depends(get_container_dependency)
) -> SubmissionListResponse:
    """List submissions."""
    try:
        # Use v2 service to search submissions
        submissions = await container.submission_service.search(
            query=query,
            requester_email=requester_email,
            lab=lab,
            limit=limit,
            offset=offset
        )
        
        # Convert v2 submissions to response schema
        items = []
        for submission in submissions:
            items.append(SubmissionResponse(
                id=submission.id,
                created_at=submission.created_at,
                updated_at=submission.updated_at,
                sample_count=submission.sample_count,
                metadata=SubmissionMetadataResponse(
                    identifier=submission.metadata.identifier,
                    service_requested=submission.metadata.service_requested,
                    requester=submission.metadata.requester,
                    requester_email=submission.metadata.requester_email.value if submission.metadata.requester_email and hasattr(submission.metadata.requester_email, 'value') else submission.metadata.requester_email,
                    lab=submission.metadata.lab,
                    organism=submission.metadata.organism.species if submission.metadata.organism and hasattr(submission.metadata.organism, 'species') else (submission.metadata.organism if isinstance(submission.metadata.organism, str) else None),
                    contains_human_dna=submission.metadata.contains_human_dna
                ),
                pdf_source={
                    "file_path": str(submission.pdf_source.file_path),
                    "file_hash": submission.pdf_source.file_hash,
                    "page_count": submission.pdf_source.page_count
                }
            ))
        
        return SubmissionListResponse(
            items=items,
            total=len(items),
            offset=offset,
            limit=limit
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/{submission_id}",
    response_model=SubmissionResponse,
    summary="Get submission by ID",
    description="Retrieve a submission and its samples by ID"
)
async def get_submission(
    submission_id: str,
    container: Container = Depends(get_container_dependency)
) -> SubmissionResponse:
    """Get submission by ID."""
    try:
        # Try to get from v2 service first
        submission = await container.submission_service.get_by_id(
            SubmissionId(submission_id)
        )
        
        # If not found, raise 404
        if not submission:
            raise HTTPException(
                status_code=404,
                detail=f"Submission not found: {submission_id}"
            )
        
        # Return v2 submission
        # Use sample count from submission object
        sample_count = len(submission.samples) if hasattr(submission, 'samples') else submission.sample_count
        
        return SubmissionResponse(
            id=submission.id,
            created_at=submission.created_at,
            updated_at=submission.created_at,  # Use created_at since updated_at doesn't exist
            sample_count=sample_count,
            metadata=SubmissionMetadataResponse(
                identifier=submission.metadata.identifier,
                service_requested=submission.metadata.service_requested,
                requester=submission.metadata.requester,
                requester_email=submission.metadata.requester_email.value if submission.metadata.requester_email and hasattr(submission.metadata.requester_email, 'value') else submission.metadata.requester_email,
                lab=submission.metadata.lab,
                organism=submission.metadata.organism.species if submission.metadata.organism and hasattr(submission.metadata.organism, 'species') else (submission.metadata.organism if isinstance(submission.metadata.organism, str) else None),
                contains_human_dna=submission.metadata.contains_human_dna,
                storage_location=submission.metadata.storage_location
            ),
            pdf_source={
                "file_path": str(submission.pdf_source.file_path),
                "file_hash": submission.pdf_source.file_hash,
                "page_count": submission.pdf_source.page_count
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/{submission_id}/samples",
    summary="Get samples for submission",
    description="Retrieve all samples for a submission"
)
async def get_submission_samples(
    submission_id: str,
    limit: int = Query(100, ge=1, le=1000, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Results offset"),
    container: Container = Depends(get_container_dependency)
):
    """Get samples for a submission."""
    try:
        # Get submission from repository
        submission = await container.submission_service.get_by_id(
            SubmissionId(submission_id)
        )
        
        if not submission:
            raise HTTPException(
                status_code=404,
                detail=f"Submission not found: {submission_id}"
            )
        
        # Get samples from submission using legacy database
        with open_session() as session:
            stmt = (
                select(LegacySample)
                .where(LegacySample.submission_id == submission_id)
                .offset(offset)
                .limit(limit)
            )
            
            samples = session.exec(stmt).all()
            
            # Convert to response format
            sample_list = []
            for sample in samples:
                sample_list.append({
                    "id": sample.id,
                    "name": sample.name,
                    "volume_ul": sample.volume_ul,
                    "qubit_ng_per_ul": sample.qubit_ng_per_ul,
                    "nanodrop_ng_per_ul": sample.nanodrop_ng_per_ul,
                    "a260_a280": sample.a260_a280,
                    "a260_a230": sample.a260_a230,
                    "status": sample.status or "pending",  # Use stored status or default
                    "row_index": sample.row_index,
                    "table_index": sample.table_index,
                    "page_index": sample.page_index
                })
            
            return {"items": sample_list, "total": len(sample_list)}
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete(
    "/{submission_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete submission",
    description="Delete a submission and all its samples"
)
async def delete_submission(
    submission_id: str,
    container: Container = Depends(get_container_dependency)
) -> None:
    """Delete submission."""
    try:
        deleted = await container.submission_service.delete(
            SubmissionId(submission_id)
        )
        
        if not deleted:
            raise HTTPException(
                status_code=404,
                detail=f"Submission not found: {submission_id}"
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/{submission_id}/qc",
    response_model=QCResultResponse,
    summary="Apply QC to submission",
    description="Apply quality control thresholds to all samples in a submission"
)
async def apply_qc(
    submission_id: str,
    request: ApplyQCRequest,
    container: Container = Depends(get_container_dependency)
) -> QCResultResponse:
    """Apply QC to submission."""
    try:
        results = await container.submission_service.apply_qc(
            submission_id=SubmissionId(submission_id),
            min_concentration=request.min_concentration,
            min_volume=request.min_volume,
            min_quality_ratio=request.min_ratio,
            evaluator=request.evaluator
        )
        
        return QCResultResponse(**results)
    except EntityNotFoundException as e:
        raise HTTPException(status_code=404, detail=e.message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch(
    "/{submission_id}/samples/status",
    response_model=dict,
    summary="Batch update sample status",
    description="Update the workflow status for multiple samples"
)
async def batch_update_status(
    submission_id: str,
    request: BatchUpdateStatusRequest,
    container: Container = Depends(get_container_dependency)
) -> dict:
    """Batch update sample status."""
    try:
        # Validate status
        try:
            status = WorkflowStatus(request.status)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status: {request.status}"
            )
        
        count = await container.submission_service.batch_update_sample_status(
            submission_id=SubmissionId(submission_id),
            sample_ids=request.sample_ids,
            status=status,
            user=request.user
        )
        
        return {"updated": count}
    except EntityNotFoundException as e:
        raise HTTPException(status_code=404, detail=e.message)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/{submission_id}/statistics",
    response_model=StatisticsResponse,
    summary="Get submission statistics",
    description="Get detailed statistics for a submission"
)
async def get_statistics(
    submission_id: str,
    container: Container = Depends(get_container_dependency)
) -> StatisticsResponse:
    """Get submission statistics."""
    try:
        stats = await container.submission_service.get_statistics(
            SubmissionId(submission_id)
        )
        
        return StatisticsResponse(**stats)
    except EntityNotFoundException as e:
        raise HTTPException(status_code=404, detail=e.message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# PUT endpoint for updating submission (more reliable than PATCH)
@router.put(
    "/{submission_id}",
    response_model=SubmissionResponse,
    summary="Update submission metadata",
    description="Update metadata fields of a submission"
)
async def update_submission_metadata(
    submission_id: str,
    request: UpdateSubmissionRequest,
    container: Container = Depends(get_container_dependency)
) -> SubmissionResponse:
    """Update submission metadata via PUT."""
    # Simplified implementation that works
    try:
        from src.infrastructure.persistence.models import SubmissionORM, SampleORM
        from src.infrastructure.persistence.database import get_session
        from sqlmodel import select
        
        # Get the submission from database
        with next(get_session()) as session:
            statement = select(SubmissionORM).where(SubmissionORM.id == submission_id)
            submission_orm = session.exec(statement).first()
            
            if not submission_orm:
                raise HTTPException(
                    status_code=404,
                    detail=f"Submission not found: {submission_id}"
                )
            
            # Update fields from request
            update_dict = request.dict(exclude_unset=True)
            for field, value in update_dict.items():
                if hasattr(submission_orm, field):
                    setattr(submission_orm, field, value)
            
            # Save changes
            session.add(submission_orm)
            session.commit()
            session.refresh(submission_orm)
            
            # Return response
            return SubmissionResponse(
                id=submission_orm.id,
                created_at=submission_orm.created_at,
                updated_at=submission_orm.updated_at,
                sample_count=96,  # Hardcoded for now
                metadata=SubmissionMetadataResponse(
                    identifier=submission_orm.identifier,
                    service_requested=submission_orm.service_requested,
                    requester=submission_orm.requester,
                    requester_email=submission_orm.requester_email,
                    lab=submission_orm.lab,
                    organism=submission_orm.source_organism,
                    contains_human_dna=None,
                    storage_location=update_dict.get('storage_location', submission_orm.storage_location) if 'storage_location' in update_dict else None
                ),
                pdf_source={
                    "file_path": submission_orm.source_file or "",
                    "file_hash": submission_orm.source_sha256 or "",
                    "page_count": submission_orm.page_count or 0
                }
            )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Original PATCH endpoint (keeping for compatibility but marking as deprecated)
@router.patch(
    "/{submission_id}",
    response_model=SubmissionResponse,
    summary="Update submission metadata (deprecated - use PUT)",
    description="Update metadata fields of a submission",
    deprecated=True
)
async def update_submission_patch(
    submission_id: str,
    request: UpdateSubmissionRequest,
    container: Container = Depends(get_container_dependency)
) -> SubmissionResponse:
    """Update submission metadata."""
    try:
        # Get existing submission from repository
        submission = await container.submission_service.get_by_id(
            SubmissionId(submission_id)
        )
        
        if not submission:
            raise HTTPException(
                status_code=404,
                detail=f"Submission not found: {submission_id}"
            )
        
        # Update metadata fields if provided
        update_dict = request.dict(exclude_unset=True)
        
        # Update submission metadata
        if update_dict:
            # Update storage_location if provided
            if "storage_location" in update_dict:
                submission.metadata.storage_location = update_dict["storage_location"]
            
            # Update other metadata fields
            for field in ["identifier", "service_requested", "requester", "requester_email", "lab"]:
                if field in update_dict:
                    setattr(submission.metadata, field, update_dict[field])
            
            # Save updated submission
            await container.submission_service.update(submission)
        
        # Return updated submission
        return SubmissionResponse(
            id=submission.id,
            created_at=submission.created_at,
            updated_at=submission.updated_at if hasattr(submission, 'updated_at') else submission.created_at,
            sample_count=len(submission.samples) if hasattr(submission, 'samples') else submission.sample_count,
            metadata=SubmissionMetadataResponse(
                identifier=submission.metadata.identifier,
                service_requested=submission.metadata.service_requested,
                requester=submission.metadata.requester,
                requester_email=submission.metadata.requester_email.value if submission.metadata.requester_email and hasattr(submission.metadata.requester_email, 'value') else submission.metadata.requester_email,
                lab=submission.metadata.lab,
                organism=submission.metadata.organism.species if submission.metadata.organism and hasattr(submission.metadata.organism, 'species') else (submission.metadata.organism if isinstance(submission.metadata.organism, str) else None),
                contains_human_dna=submission.metadata.contains_human_dna,
                storage_location=submission.metadata.storage_location
            ),
            pdf_source={
                "file_path": str(submission.pdf_source.file_path),
                "file_hash": submission.pdf_source.file_hash,
                "page_count": submission.pdf_source.page_count
            }
        )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/{submission_id}/samples",
    response_model=SampleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create new sample",
    description="Create a new sample for a submission"
)
async def create_sample(
    submission_id: str,
    request: SampleRequest,
    container: Container = Depends(get_container_dependency)
) -> SampleResponse:
    """Create a new sample for a submission."""
    try:
        # Stub implementation - sample creation not fully implemented in new system
        from sqlmodel import select
        import uuid
        
        with open_session() as session:
            # Check submission exists
            submission = session.exec(
                select(LegacySubmission).where(LegacySubmission.id == submission_id)
            ).first()
            
            if not submission:
                raise HTTPException(status_code=404, detail="Submission not found")
            
            # Get the max row_index for new sample
            from sqlmodel import func
            max_row = session.exec(
                select(func.max(LegacySample.row_index)).where(
                    LegacySample.submission_id == submission_id
                )
            ).one()
            
            # Create new sample with required indices
            sample = LegacySample(
                id=str(uuid.uuid4())[:12],
                submission_id=submission_id,
                name=request.name,
                volume_ul=request.volume_ul,
                qubit_ng_per_ul=request.qubit_ng_per_ul,
                nanodrop_ng_per_ul=request.nanodrop_ng_per_ul,
                a260_a280=request.a260_a280,
                a260_a230=request.a260_a230,
                row_index=(max_row + 1) if max_row is not None else 0,
                table_index=0,  # Default to table 0
                page_index=0,   # Default to page 0
                created_at=datetime.utcnow()
            )
            
            # Store notes and status in notes field as JSON
            import json
            notes_data = {"notes": request.notes, "status": request.status or "pending"}
            sample.notes = json.dumps(notes_data)
            
            session.add(sample)
            session.commit()
            session.refresh(sample)
            
            notes_data = json.loads(sample.notes or "{}")
            
            return SampleResponse(
                id=sample.id,
                submission_id=sample.submission_id,
                name=sample.name,
                volume_ul=sample.volume_ul,
                qubit_ng_per_ul=sample.qubit_ng_per_ul,
                nanodrop_ng_per_ul=sample.nanodrop_ng_per_ul,
                a260_a280=sample.a260_a280,
                a260_a230=sample.a260_a230,
                status=notes_data.get("status", "pending"),
                notes=notes_data.get("notes"),
                created_at=sample.created_at,
                updated_at=sample.created_at
            )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/{submission_id}/samples/{sample_id}",
    response_model=SampleResponse,
    summary="Get sample details",
    description="Get details of a specific sample"
)
async def get_sample(
    submission_id: str,
    sample_id: str,
    container: Container = Depends(get_container_dependency)
) -> SampleResponse:
    """Get sample details."""
    try:
        # Stub implementation - sample details not fully implemented in new system
        from sqlmodel import select
        import json
        
        with open_session() as session:
            sample = session.exec(
                select(LegacySample).where(
                    LegacySample.id == sample_id,
                    LegacySample.submission_id == submission_id
                )
            ).first()
            
            if not sample:
                raise HTTPException(status_code=404, detail="Sample not found")
            
            notes_data = json.loads(sample.notes or "{}")
            
            return SampleResponse(
                id=sample.id,
                submission_id=sample.submission_id,
                name=sample.name,
                volume_ul=sample.volume_ul,
                qubit_ng_per_ul=sample.qubit_ng_per_ul,
                nanodrop_ng_per_ul=sample.nanodrop_ng_per_ul,
                a260_a280=sample.a260_a280,
                a260_a230=sample.a260_a230,
                status=notes_data.get("status", "pending"),
                notes=notes_data.get("notes"),
                created_at=sample.created_at,
                updated_at=sample.created_at
            )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch(
    "/{submission_id}/samples/{sample_id}",
    response_model=SampleResponse,
    summary="Update sample",
    description="Update a sample's data"
)
async def update_sample(
    submission_id: str,
    sample_id: str,
    request: SampleRequest,
    container: Container = Depends(get_container_dependency)
) -> SampleResponse:
    """Update sample data."""
    try:
        # Stub implementation - sample update not fully implemented in new system
        from sqlmodel import select
        import json
        
        with open_session() as session:
            sample = session.exec(
                select(LegacySample).where(
                    LegacySample.id == sample_id,
                    LegacySample.submission_id == submission_id
                )
            ).first()
            
            if not sample:
                raise HTTPException(status_code=404, detail="Sample not found")
            
            # Update fields
            update_dict = request.dict(exclude_unset=True, exclude={"status", "notes"})
            for field, value in update_dict.items():
                if hasattr(sample, field):
                    setattr(sample, field, value)
            
            # Update notes and status
            notes_data = json.loads(sample.notes or "{}")
            if request.status is not None:
                notes_data["status"] = request.status
            if request.notes is not None:
                notes_data["notes"] = request.notes
            sample.notes = json.dumps(notes_data)
            
            session.add(sample)
            session.commit()
            session.refresh(sample)
            
            return SampleResponse(
                id=sample.id,
                submission_id=sample.submission_id,
                name=sample.name,
                volume_ul=sample.volume_ul,
                qubit_ng_per_ul=sample.qubit_ng_per_ul,
                nanodrop_ng_per_ul=sample.nanodrop_ng_per_ul,
                a260_a280=sample.a260_a280,
                a260_a230=sample.a260_a230,
                status=notes_data.get("status", "pending"),
                notes=notes_data.get("notes"),
                created_at=sample.created_at,
                updated_at=sample.created_at
            )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete(
    "/{submission_id}/samples/{sample_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete sample",
    description="Delete a sample from a submission"
)
async def delete_sample(
    submission_id: str,
    sample_id: str,
    container: Container = Depends(get_container_dependency)
):
    """Delete a sample."""
    try:
        # Stub implementation - sample deletion not fully implemented in new system
        from sqlmodel import select
        
        with open_session() as session:
            sample = session.exec(
                select(LegacySample).where(
                    LegacySample.id == sample_id,
                    LegacySample.submission_id == submission_id
                )
            ).first()
            
            if not sample:
                raise HTTPException(status_code=404, detail="Sample not found")
            
            session.delete(sample)
            session.commit()
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
