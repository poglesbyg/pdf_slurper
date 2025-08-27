# 🌐 PDF Slurper OpenShift URLs - FULLY OPERATIONAL

## ✅ Everything is Running on OpenShift!

All components are successfully deployed and running on OpenShift with full CRUD functionality.

### 📊 Current Status
- **API Pods**: 3/3 running (x86 architecture)
- **Web UI Pod**: 1/1 running
- **Architecture**: linux/amd64 (x86_64) ✅
- **CRUD Features**: Fully operational ✅

## 🔗 Working URLs

### 🎯 **PRIMARY FRONTEND URLs**

#### Dashboard (Main Interface)
**https://pdf-slurper-dept-barc.apps.cloudapps.unc.edu/dashboard.html**
- Main dashboard with statistics and recent submissions
- Access all CRUD features from here

#### Upload PDF
**https://pdf-slurper-dept-barc.apps.cloudapps.unc.edu/upload.html**
- Upload new PDFs with storage location (required field)
- Process laboratory sample data

#### Submissions List
**https://pdf-slurper-dept-barc.apps.cloudapps.unc.edu/submissions.html**
- View all submissions
- Edit/Delete submissions
- See storage locations

#### Submission Details
**https://pdf-slurper-dept-barc.apps.cloudapps.unc.edu/submission/{id}**
- Full CRUD for individual samples
- Edit submission metadata
- Add/Edit/Delete samples

### 📡 **API ENDPOINTS**

#### Base API URL
**https://pdf-slurper-v2-dept-barc.apps.cloudapps.unc.edu**

#### API Documentation (Swagger)
**https://pdf-slurper-v2-dept-barc.apps.cloudapps.unc.edu/api/docs**
- Interactive API documentation
- Test all CRUD endpoints directly

#### Key API Endpoints:
- `GET /api/v1/submissions/` - List all submissions
- `POST /api/v1/submissions/` - Create submission from PDF
- `PATCH /api/v1/submissions/{id}` - Update submission metadata
- `DELETE /api/v1/submissions/{id}` - Delete submission
- `POST /api/v1/submissions/{id}/samples` - Create sample
- `GET /api/v1/submissions/{id}/samples/{sample_id}` - Get sample
- `PATCH /api/v1/submissions/{id}/samples/{sample_id}` - Update sample
- `DELETE /api/v1/submissions/{id}/samples/{sample_id}` - Delete sample

## 🚀 Quick Start Guide

1. **Access the Dashboard**
   - Go to: https://pdf-slurper-dept-barc.apps.cloudapps.unc.edu/dashboard.html
   - This is your main entry point

2. **Upload a PDF**
   - Click "Upload PDF" from dashboard
   - Or go directly to: https://pdf-slurper-dept-barc.apps.cloudapps.unc.edu/upload.html
   - **Required**: Enter storage location before uploading

3. **Manage Submissions**
   - View all: https://pdf-slurper-dept-barc.apps.cloudapps.unc.edu/submissions.html
   - Click any submission to view/edit details
   - Full CRUD operations available

4. **Manage Samples**
   - From submission details page
   - Click "Add Sample" to create new samples
   - Click "Edit" or "Delete" on any sample row

## 🔧 Technical Details

### Services Running
```
pdf-slurper-web     - Frontend UI (nginx serving HTML/JS)
pdf-slurper-v2      - API Server (FastAPI with CRUD)
```

### Pods Status
```
pdf-slurper-v2-65bdbb75bb-bvg7l    1/1     Running (x86)
pdf-slurper-v2-65bdbb75bb-mvcbx    1/1     Running (x86)
pdf-slurper-v2-65bdbb75bb-nw42k    1/1     Running (x86)
pdf-slurper-web-55ccf66946-8hbxb   1/1     Running
```

### Routes
```
pdf-slurper      -> pdf-slurper-web:8080    (Frontend)
pdf-slurper-v2   -> pdf-slurper-v2:8080     (API)
```

## 📝 Notes

- The root URL (/) shows nginx default page, but all application pages work correctly
- Frontend communicates with API via proxy configuration
- All data persists in PVC mounted at `/data`
- SQLite database at `/data/pdf_slurper.db`

## ✨ New CRUD Features Available

1. **Storage Location Field** - Required for all new uploads
2. **Edit Submission Metadata** - Update any submission fields
3. **Sample Management** - Full CRUD for individual samples
4. **Export Options** - JSON and CSV export
5. **Status Tracking** - Visual indicators for sample status

---

**Deployment Date**: 2025-08-27
**Version**: 2.1.0-CRUD-x86
**Status**: ✅ **FULLY OPERATIONAL**
**Architecture**: x86_64 (linux/amd64)
