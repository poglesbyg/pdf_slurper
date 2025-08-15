"""Submission API routes."""

from typing import List, Optional
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, status, UploadFile, File, Form
from fastapi.responses import JSONResponse
import tempfile
import os

from src.application.container import Container

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
    ApplyQCRequest,
    QCResultResponse,
    BatchUpdateStatusRequest,
    SearchRequest,
    StatisticsResponse,
    SubmissionMetadataResponse
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
                force=force
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
        
        # Convert to response schema
        return SubmissionResponse(
            id=submission.id,
            created_at=submission.created_at,
            updated_at=submission.updated_at,
            sample_count=submission.sample_count,
            metadata=SubmissionMetadataResponse(
                identifier=submission.metadata.identifier,
                service_requested=submission.metadata.service_requested,
                requester=submission.metadata.requester,
                requester_email=submission.metadata.requester_email.value if submission.metadata.requester_email else None,
                lab=submission.metadata.lab,
                organism=submission.metadata.organism.full_name if submission.metadata.organism else None,
                contains_human_dna=submission.metadata.contains_human_dna
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
        workflow_status = stats.get("status_counts", {})
        qc_status = stats.get("qc_status_counts", {})
        
        samples_with_location = 0  # Would need a query for samples with location field set
        samples_processed = workflow_status.get("completed", 0) + workflow_status.get("sequenced", 0)
        
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
        submissions = await container.submission_service.search(
            query=query,
            requester_email=requester_email,
            lab=lab,
            limit=limit,
            offset=offset
        )
        
        # Convert to response schema
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
                    requester_email=submission.metadata.requester_email.value if submission.metadata.requester_email else None,
                    lab=submission.metadata.lab,
                    organism=submission.metadata.organism.full_name if submission.metadata.organism else None,
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
        submission = await container.submission_service.get_by_id(
            SubmissionId(submission_id)
        )
        
        if not submission:
            raise HTTPException(
                status_code=404,
                detail=f"Submission not found: {submission_id}"
            )
        
        return SubmissionResponse(
            id=submission.id,
            created_at=submission.created_at,
            updated_at=submission.updated_at,
            sample_count=submission.sample_count,
            metadata=SubmissionMetadataResponse(
                identifier=submission.metadata.identifier,
                service_requested=submission.metadata.service_requested,
                requester=submission.metadata.requester,
                requester_email=submission.metadata.requester_email.value if submission.metadata.requester_email else None,
                lab=submission.metadata.lab,
                organism=submission.metadata.organism.full_name if submission.metadata.organism else None,
                contains_human_dna=submission.metadata.contains_human_dna
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
