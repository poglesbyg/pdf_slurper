#!/usr/bin/env python3
"""
Local test to verify storage location mapping logic
"""

import sys
sys.path.insert(0, '.')

from datetime import datetime
from pathlib import Path

# Import the components we're testing
from src.infrastructure.persistence.models import SubmissionORM, SampleORM
from src.infrastructure.persistence.mappers import DomainMapper
from src.domain.models.submission import Submission, SubmissionMetadata, PDFSource
from src.domain.models.value_objects import SubmissionId
from sqlmodel import SQLModel, create_engine, Session

def test_storage_mapping():
    """Test that storage location is properly mapped between ORM and domain models."""
    print("\n" + "="*60)
    print("🔬 TESTING STORAGE LOCATION MAPPING (LOCAL)")
    print("="*60)
    
    # Test 1: Domain to ORM mapping
    print("\n1️⃣ Testing Domain → ORM mapping...")
    
    # Create a domain submission with storage location
    test_storage = "Local Test Storage Location"
    metadata = SubmissionMetadata(
        identifier="TEST-001",
        service_requested="Test Service",
        requester="Test User",
        lab="Test Lab",
        storage_location=test_storage
    )
    
    pdf_source = PDFSource(
        file_path=Path("/tmp/test.pdf"),
        file_hash="testhash123",
        file_size=1000,
        modification_time=datetime.now(),
        page_count=5
    )
    
    submission = Submission(
        id=SubmissionId("test-id-123"),
        metadata=metadata,
        pdf_source=pdf_source,
        samples=[],
        created_at=datetime.now()
    )
    
    # Map to ORM
    mapper = DomainMapper()
    orm = mapper.submission_to_orm(submission)
    
    print(f"   Domain storage_location: {submission.metadata.storage_location}")
    print(f"   ORM storage_location: {orm.storage_location}")
    
    if orm.storage_location == test_storage:
        print("   ✅ Domain → ORM mapping works!")
    else:
        print("   ❌ Domain → ORM mapping failed!")
    
    # Test 2: ORM to Domain mapping
    print("\n2️⃣ Testing ORM → Domain mapping...")
    
    # Create an ORM object with storage location
    orm_with_storage = SubmissionORM(
        id="test-id-456",
        created_at=datetime.now(),
        updated_at=datetime.now(),
        source_file="/tmp/test2.pdf",
        source_sha256="hash456",
        source_size=2000,
        source_mtime=datetime.now().timestamp(),
        page_count=10,
        identifier="TEST-002",
        service_requested="Test Service 2",
        requester="Test User 2",
        lab="Test Lab 2",
        storage_location="ORM Test Storage Location"  # This is what we're testing
    )
    
    # Map to domain
    domain_submission = mapper.submission_from_orm(orm_with_storage, [])
    
    print(f"   ORM storage_location: {orm_with_storage.storage_location}")
    print(f"   Domain storage_location: {domain_submission.metadata.storage_location}")
    
    if domain_submission.metadata.storage_location == orm_with_storage.storage_location:
        print("   ✅ ORM → Domain mapping works!")
    else:
        print("   ❌ ORM → Domain mapping failed!")
    
    # Test 3: Round-trip test
    print("\n3️⃣ Testing round-trip (Domain → ORM → Domain)...")
    
    original_storage = "Round Trip Test Location"
    original_metadata = SubmissionMetadata(
        identifier="ROUND-TRIP",
        storage_location=original_storage
    )
    
    original_submission = Submission(
        id=SubmissionId("round-trip-id"),
        metadata=original_metadata,
        pdf_source=pdf_source,
        samples=[],
        created_at=datetime.now()
    )
    
    # Convert to ORM
    orm_round_trip = mapper.submission_to_orm(original_submission)
    
    # Convert back to domain
    final_submission = mapper.submission_from_orm(orm_round_trip, [])
    
    print(f"   Original storage: {original_storage}")
    print(f"   ORM storage: {orm_round_trip.storage_location}")
    print(f"   Final storage: {final_submission.metadata.storage_location}")
    
    if final_submission.metadata.storage_location == original_storage:
        print("   ✅ Round-trip mapping works!")
        return True
    else:
        print("   ❌ Round-trip mapping failed!")
        return False

def test_database_persistence():
    """Test that storage location persists in the database."""
    print("\n4️⃣ Testing database persistence...")
    
    # Create a temporary SQLite database
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    
    test_id = "db-test-123"
    test_storage = "Database Test Storage"
    
    # Save to database
    with Session(engine) as session:
        orm = SubmissionORM(
            id=test_id,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            source_file="/tmp/db_test.pdf",
            source_sha256="dbhash123",
            source_size=3000,
            source_mtime=datetime.now().timestamp(),
            page_count=15,
            identifier="DB-TEST",
            storage_location=test_storage
        )
        session.add(orm)
        session.commit()
        print(f"   Saved with storage: {test_storage}")
    
    # Read from database
    with Session(engine) as session:
        retrieved = session.get(SubmissionORM, test_id)
        if retrieved:
            print(f"   Retrieved storage: {retrieved.storage_location}")
            if retrieved.storage_location == test_storage:
                print("   ✅ Database persistence works!")
                return True
            else:
                print("   ❌ Database persistence failed!")
                return False
        else:
            print("   ❌ Failed to retrieve from database!")
            return False

def main():
    """Run all local tests."""
    print("\n🚀 Running local storage location tests...")
    
    # Test mapping
    mapping_ok = test_storage_mapping()
    
    # Test database
    db_ok = test_database_persistence()
    
    print("\n" + "="*60)
    if mapping_ok and db_ok:
        print("✅ ALL LOCAL TESTS PASSED!")
        print("\nThe storage location mapping is working correctly.")
        print("The issue might be that the fix hasn't been deployed to OpenShift yet.")
    else:
        print("❌ SOME LOCAL TESTS FAILED!")
        print("\nThere are still issues with the storage location mapping.")
    print("="*60 + "\n")
    
    return 0 if (mapping_ok and db_ok) else 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
