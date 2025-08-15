"""Unit tests for Sample domain entity."""

import pytest
from datetime import datetime
from src.domain.models.sample import Sample, Measurements, QCResult, ProcessingInfo
from src.domain.models.value_objects import (
    SampleId, WorkflowStatus, QCStatus, Concentration,
    Volume, QualityRatio, StorageLocation, QualityScore
)


class TestSample:
    """Test Sample entity."""
    
    def test_create_sample(self):
        """Test creating a sample."""
        sample = Sample(
            id=SampleId("test_sample_001"),
            submission_id="sub_001",
            name="Sample 1",
            measurements=Measurements(
                volume=Volume(50.0),
                qubit_concentration=Concentration(100.0)
            )
        )
        
        assert sample.id == "test_sample_001"
        assert sample.name == "Sample 1"
        assert sample.measurements.volume.value == 50.0
        assert sample.measurements.qubit_concentration.value == 100.0
    
    def test_apply_qc_passed(self):
        """Test QC with passing values."""
        sample = Sample(
            id=SampleId("test_sample_001"),
            submission_id="sub_001",
            name="Sample 1",
            measurements=Measurements(
                volume=Volume(50.0),
                qubit_concentration=Concentration(100.0),
                a260_a280=QualityRatio(1.85)
            )
        )
        
        result = sample.apply_qc(
            min_concentration=10.0,
            min_volume=20.0,
            min_quality_ratio=1.8
        )
        
        assert result.status == QCStatus.PASSED
        assert result.passed_concentration is True
        assert result.passed_volume is True
        assert result.passed_quality_ratio is True
        assert len(result.issues) == 0
    
    def test_apply_qc_failed(self):
        """Test QC with failing values."""
        sample = Sample(
            id=SampleId("test_sample_001"),
            submission_id="sub_001",
            name="Sample 1",
            measurements=Measurements(
                volume=Volume(5.0),  # Below threshold
                qubit_concentration=Concentration(5.0),  # Below threshold
                a260_a280=QualityRatio(1.5)  # Below threshold
            )
        )
        
        result = sample.apply_qc(
            min_concentration=10.0,
            min_volume=20.0,
            min_quality_ratio=1.8
        )
        
        assert result.status == QCStatus.FAILED
        assert result.passed_concentration is False
        assert result.passed_volume is False
        assert result.passed_quality_ratio is False
        assert len(result.issues) == 3
    
    def test_apply_qc_warning(self):
        """Test QC with warning (one issue)."""
        sample = Sample(
            id=SampleId("test_sample_001"),
            submission_id="sub_001",
            name="Sample 1",
            measurements=Measurements(
                volume=Volume(50.0),
                qubit_concentration=Concentration(5.0),  # Below threshold
                a260_a280=QualityRatio(1.85)
            )
        )
        
        result = sample.apply_qc(
            min_concentration=10.0,
            min_volume=20.0,
            min_quality_ratio=1.8
        )
        
        assert result.status == QCStatus.WARNING
        assert result.passed_concentration is False
        assert result.passed_volume is True
        assert result.passed_quality_ratio is True
        assert len(result.issues) == 1
    
    def test_update_status(self):
        """Test updating sample status."""
        sample = Sample(
            id=SampleId("test_sample_001"),
            submission_id="sub_001",
            name="Sample 1",
            measurements=Measurements()
        )
        
        assert sample.processing_info.status == WorkflowStatus.RECEIVED
        
        sample.processing_info.update_status(
            WorkflowStatus.PROCESSING,
            user="technician1"
        )
        
        assert sample.processing_info.status == WorkflowStatus.PROCESSING
        assert sample.processing_info.processed_by == "technician1"
        assert sample.processing_info.processing_date is not None
        assert len(sample.processing_info.notes) == 1
    
    def test_update_location(self):
        """Test updating sample location."""
        sample = Sample(
            id=SampleId("test_sample_001"),
            submission_id="sub_001",
            name="Sample 1",
            measurements=Measurements()
        )
        
        location = StorageLocation(
            freezer="A",
            shelf="3",
            box="12",
            position="A4"
        )
        
        sample.update_location(location, user="technician1")
        
        assert sample.processing_info.location == location
        assert len(sample.processing_info.notes) == 1
        assert "Location changed" in sample.processing_info.notes[0]
    
    def test_is_ready_for_sequencing(self):
        """Test checking if sample is ready for sequencing."""
        sample = Sample(
            id=SampleId("test_sample_001"),
            submission_id="sub_001",
            name="Sample 1",
            measurements=Measurements(
                volume=Volume(50.0),
                qubit_concentration=Concentration(100.0)
            )
        )
        
        # Not ready - no QC
        assert sample.is_ready_for_sequencing() is False
        
        # Apply QC
        sample.apply_qc()
        
        # Not ready - wrong status
        assert sample.is_ready_for_sequencing() is False
        
        # Update status
        sample.processing_info.update_status(WorkflowStatus.PROCESSING)
        
        # Now ready
        assert sample.is_ready_for_sequencing() is True
    
    def test_add_note(self):
        """Test adding notes to sample."""
        sample = Sample(
            id=SampleId("test_sample_001"),
            submission_id="sub_001",
            name="Sample 1",
            measurements=Measurements()
        )
        
        sample.processing_info.add_note("Test note", author="user1")
        sample.processing_info.add_note("Another note")
        
        assert len(sample.processing_info.notes) == 2
        assert "user1: Test note" in sample.processing_info.notes[0]
        assert "Another note" in sample.processing_info.notes[1]


class TestMeasurements:
    """Test Measurements value object."""
    
    def test_best_concentration_prefers_qubit(self):
        """Test that Qubit is preferred over Nanodrop."""
        measurements = Measurements(
            qubit_concentration=Concentration(100.0),
            nanodrop_concentration=Concentration(120.0)
        )
        
        assert measurements.best_concentration == measurements.qubit_concentration
    
    def test_best_concentration_fallback_to_nanodrop(self):
        """Test fallback to Nanodrop when Qubit is not available."""
        measurements = Measurements(
            nanodrop_concentration=Concentration(120.0)
        )
        
        assert measurements.best_concentration == measurements.nanodrop_concentration
    
    def test_best_concentration_none(self):
        """Test when no concentration is available."""
        measurements = Measurements()
        
        assert measurements.best_concentration is None
