# Direct Links Guide - PDF Slurper Application

## 🔗 Explicit Direct Links

### Test Pages (Start Here)
1. **Test Links Page** - Shows all available links  
   https://pdf-slurper-v2-dept-barc.apps.cloudapps.unc.edu/test_links.html

2. **Simple Samples View** - Basic table showing all 96 samples  
   https://pdf-slurper-v2-dept-barc.apps.cloudapps.unc.edu/simple_samples.html

### Main Application Pages
3. **Dashboard** - List of all submissions  
   https://pdf-slurper-v2-dept-barc.apps.cloudapps.unc.edu/dashboard.html

4. **Submission Detail Page** - Full detail view with samples  
   https://pdf-slurper-v2-dept-barc.apps.cloudapps.unc.edu/submission_detail.html?id=sub_06fa0d0e37b7

5. **Upload Page** - Upload new PDF files  
   https://pdf-slurper-v2-dept-barc.apps.cloudapps.unc.edu/upload.html

### API Endpoints (JSON Data)
6. **List All Submissions**  
   https://pdf-slurper-v2-dept-barc.apps.cloudapps.unc.edu/api/v1/submissions/

7. **Get Specific Submission Details**  
   https://pdf-slurper-v2-dept-barc.apps.cloudapps.unc.edu/api/v1/submissions/sub_06fa0d0e37b7

8. **Get All 96 Samples**  
   https://pdf-slurper-v2-dept-barc.apps.cloudapps.unc.edu/api/v1/submissions/sub_06fa0d0e37b7/samples

## 📊 Current Data Summary

### Submission Information
- **ID**: sub_06fa0d0e37b7
- **Identifier**: HTSF--JL-147
- **Requester**: Joshua Leon
- **Email**: joshleon@unc.edu
- **Lab**: Mitchell, Charles (UNC-CH) Lab
- **Service**: Oxford Nanopore DNA Samples Request

### Sample Data (96 total samples)
Each sample contains:
- Sample name (e.g., "1", "3", "5", etc.)
- Volume: 2.0 μL
- Concentration (Nanodrop): Various values (e.g., 298.9, 314.05, 348.2 ng/μL)
- A260/A280 ratio: 1.84
- Status: pending

## 🔍 Troubleshooting

If pages don't load properly:

1. **Clear Browser Cache**
   - Press `Ctrl+Shift+R` (Windows/Linux) or `Cmd+Shift+R` (Mac)

2. **Check Browser Console**
   - Press `F12` to open developer tools
   - Look for any red error messages in Console tab

3. **Try Simple Pages First**
   - Start with the Simple Samples View (link #2 above)
   - This uses basic JavaScript without any frameworks

4. **Test API Directly**
   - Click the JSON API links (6-8) to verify data is available
   - You should see raw JSON data in the browser

5. **Alternative Access**
   - Try opening in an incognito/private browser window
   - Try a different browser (Chrome, Firefox, Edge)

## ✅ What Should Work

When you click the links above, you should see:

- **Test Links Page**: A page with clickable links to all features
- **Simple Samples View**: A basic table with 96 samples
- **Dashboard**: A list showing one submission (HTSF--JL-147)
- **Submission Detail**: Full details with metadata and sample table
- **API Endpoints**: Raw JSON data showing submission and sample information

## 📝 Copy-Paste URLs

For easy copying, here are all the URLs:

```
https://pdf-slurper-v2-dept-barc.apps.cloudapps.unc.edu/test_links.html
https://pdf-slurper-v2-dept-barc.apps.cloudapps.unc.edu/simple_samples.html
https://pdf-slurper-v2-dept-barc.apps.cloudapps.unc.edu/dashboard.html
https://pdf-slurper-v2-dept-barc.apps.cloudapps.unc.edu/submission_detail.html?id=sub_06fa0d0e37b7
https://pdf-slurper-v2-dept-barc.apps.cloudapps.unc.edu/api/v1/submissions/
https://pdf-slurper-v2-dept-barc.apps.cloudapps.unc.edu/api/v1/submissions/sub_06fa0d0e37b7
https://pdf-slurper-v2-dept-barc.apps.cloudapps.unc.edu/api/v1/submissions/sub_06fa0d0e37b7/samples
```
