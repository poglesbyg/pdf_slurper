# PDF Slurper - Full CRUD API Documentation

## Overview
The PDF Slurper application now has complete CRUD (Create, Read, Update, Delete) functionality for both submissions and individual samples.

## API Endpoints

### Submissions

#### 1. Create Submission (from PDF upload)
- **POST** `/api/v1/submissions/`
- **Body**: FormData with:
  - `pdf_file`: PDF file to process
  - `storage_location`: Where samples are stored (required)
  - `force`: Boolean to force reprocessing
  - `auto_qc`: Apply QC thresholds automatically
  - Additional QC parameters

#### 2. List Submissions
- **GET** `/api/v1/submissions/`
- **Query Parameters**:
  - `query`: Search text
  - `lab`: Filter by lab
  - `requester_email`: Filter by email
  - `limit`: Max results (default: 100)
  - `offset`: Pagination offset

#### 3. Get Submission Details
- **GET** `/api/v1/submissions/{submission_id}`

#### 4. Update Submission Metadata
- **PATCH** `/api/v1/submissions/{submission_id}`
- **Body**: JSON with any of:
  ```json
  {
    "identifier": "string",
    "service_requested": "string",
    "requester": "string",
    "requester_email": "string",
    "lab": "string",
    "organism": "string",
    "storage_location": "string",
    "contains_human_dna": boolean
  }
  ```

#### 5. Delete Submission
- **DELETE** `/api/v1/submissions/{submission_id}`

### Samples

#### 1. Create Sample
- **POST** `/api/v1/submissions/{submission_id}/samples`
- **Body**: JSON with:
  ```json
  {
    "name": "string (required)",
    "volume_ul": number,
    "qubit_ng_per_ul": number,
    "nanodrop_ng_per_ul": number,
    "a260_a280": number,
    "a260_a230": number,
    "status": "pending|processing|completed|failed",
    "notes": "string"
  }
  ```

#### 2. List Samples for a Submission
- **GET** `/api/v1/submissions/{submission_id}/samples`
- **Query Parameters**:
  - `limit`: Max results
  - `offset`: Pagination offset

#### 3. Get Sample Details
- **GET** `/api/v1/submissions/{submission_id}/samples/{sample_id}`

#### 4. Update Sample
- **PATCH** `/api/v1/submissions/{submission_id}/samples/{sample_id}`
- **Body**: JSON with any fields from create (all optional)

#### 5. Delete Sample
- **DELETE** `/api/v1/submissions/{submission_id}/samples/{sample_id}`

### Additional Operations

#### Apply QC to All Samples
- **POST** `/api/v1/submissions/{submission_id}/qc`
- **Body**:
  ```json
  {
    "min_concentration": 10.0,
    "min_volume": 20.0,
    "min_ratio": 1.8,
    "evaluator": "string"
  }
  ```

#### Batch Update Sample Status
- **PATCH** `/api/v1/submissions/{submission_id}/samples/status`
- **Body**:
  ```json
  {
    "sample_ids": ["id1", "id2"],
    "status": "new_status",
    "user": "optional_user"
  }
  ```

#### Get Statistics
- **GET** `/api/v1/submissions/statistics` - Global statistics
- **GET** `/api/v1/submissions/{submission_id}/statistics` - Submission-specific statistics

## Web UI Features

### Submission Management
- **View All Submissions**: `/submissions`
  - Search and filter submissions
  - Quick view of key metadata
  - Delete submissions directly from list

- **Submission Details**: `/submission/{submission_id}`
  - View complete submission metadata
  - **Edit Mode**: Click "Edit" button to modify:
    - Identifier
    - Service requested
    - Requester name and email
    - Laboratory
    - Storage location
  - Export data as JSON or CSV
  - Delete submission

### Sample Management
From the Submission Details page:

- **Add Sample**: Click "Add Sample" button
  - Fill in sample details in modal form
  - Set initial status
  - Add notes

- **Edit Sample**: Click "Edit" on any sample row
  - Modify all sample properties
  - Update status
  - Add/edit notes

- **Delete Sample**: Click "Delete" on any sample row
  - Confirmation required

### Features
1. **Real-time Updates**: All changes are immediately reflected in the UI
2. **Validation**: Required fields are enforced (e.g., storage location, sample name)
3. **Status Tracking**: Visual indicators for sample and submission status
4. **Export Options**: Export submissions and samples as JSON or CSV
5. **Responsive Design**: Works on desktop and mobile devices

## Usage Examples

### cURL Examples

#### Create a new sample:
```bash
curl -X POST http://localhost:8080/api/v1/submissions/{submission_id}/samples \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Sample-001",
    "volume_ul": 50.5,
    "qubit_ng_per_ul": 125.3,
    "a260_a280": 1.85,
    "status": "pending"
  }'
```

#### Update submission metadata:
```bash
curl -X PATCH http://localhost:8080/api/v1/submissions/{submission_id} \
  -H "Content-Type: application/json" \
  -d '{
    "storage_location": "Lab 101 - Freezer B, Shelf 2",
    "requester": "Dr. Smith"
  }'
```

#### Delete a sample:
```bash
curl -X DELETE http://localhost:8080/api/v1/submissions/{submission_id}/samples/{sample_id}
```

## Database Storage Notes

- The system uses a legacy SQLite database for storage
- Storage location and sample notes/status are stored as JSON in the notes fields
- All timestamps are in UTC
- Sample IDs are auto-generated UUID fragments

## Security Considerations

In production, consider adding:
- Authentication (OAuth2, API keys)
- Authorization (role-based access control)
- Rate limiting
- Input validation and sanitization
- Audit logging for all CRUD operations

## Error Handling

All endpoints return standard HTTP status codes:
- **200/201**: Success
- **204**: Success (no content, for DELETE)
- **400**: Bad request (validation errors)
- **404**: Resource not found
- **409**: Conflict (duplicate resources)
- **500**: Internal server error

Error responses include JSON with detail:
```json
{
  "detail": "Error description"
}
```
