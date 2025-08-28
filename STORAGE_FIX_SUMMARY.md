# Storage Location Persistence Fix

## Issue
Storage location was being saved correctly but not retrieved when fetching submissions by ID.

## Root Cause
The `get()` method in `SubmissionRepositoryImpl` was passing `SubmissionId` object directly instead of converting it to string when querying the database.

## Fix Applied

### 1. Fixed ID conversion in repository (`src/infrastructure/persistence/repositories/submission_repository.py`)

```python
# Before:
orm = session.get(SubmissionORM, id)  # id is SubmissionId object

# After:
orm = session.get(SubmissionORM, str(id))  # Convert to string
```

### 2. Also fixed sample queries:
```python
# Before:
stmt = select(SampleORM).where(SampleORM.submission_id == id)

# After:
stmt = select(SampleORM).where(SampleORM.submission_id == str(id))
```

### 3. Fixed in save method too:
```python
# Before:
stmt = select(SampleORM).where(SampleORM.submission_id == entity.id)

# After:
stmt = select(SampleORM).where(SampleORM.submission_id == str(entity.id))
```

## Verification
Local tests confirm the fix works:
- ✅ Domain → ORM mapping works
- ✅ ORM → Domain mapping works  
- ✅ Round-trip mapping works
- ✅ Database persistence works

## Deployment Status
⚠️ Fix needs to be deployed to OpenShift to take effect.

## Testing
Once deployed, test with:
```bash
python test_storage_fix.py
```

This will verify that storage location persists when retrieving by ID.
