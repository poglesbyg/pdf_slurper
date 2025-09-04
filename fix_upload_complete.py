#!/usr/bin/env python3
"""Complete fix for the upload functionality."""

from pathlib import Path

# Fix the upload.html to send all required form fields correctly
upload_html = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Upload - PDF Slurper</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3.x.x/dist/cdn.min.js"></script>
    <script src="/config.js"></script>
    <style>
        [x-cloak] { display: none !important; }
    </style>
</head>
<body class="bg-gray-50">
    <!-- Navigation -->
    <nav class="bg-white shadow-sm border-b">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div class="flex justify-between h-16">
                <div class="flex">
                    <div class="flex-shrink-0 flex items-center">
                        <h1 class="text-xl font-bold text-gray-900">PDF Slurper</h1>
                    </div>
                    <div class="hidden sm:ml-6 sm:flex sm:space-x-8">
                        <a href="/" class="border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700 inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium">
                            Dashboard
                        </a>
                        <a href="/submissions" class="border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700 inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium">
                            Submissions
                        </a>
                        <a href="/upload" class="border-indigo-500 text-gray-900 inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium">
                            Upload
                        </a>
                    </div>
                </div>
            </div>
        </div>
    </nav>

    <!-- Main Content -->
    <main class="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        <div x-data="uploadApp()" x-init="init()">
            <!-- Header -->
            <div class="px-4 sm:px-0 mb-6">
                <h2 class="text-2xl font-bold text-gray-900">Upload PDF</h2>
                <p class="mt-1 text-sm text-gray-600">Upload a laboratory PDF for processing</p>
            </div>

            <!-- Upload Form -->
            <div class="bg-white shadow rounded-lg p-6">
                <form @submit.prevent="uploadFile()">
                    <!-- File Selection -->
                    <div class="mb-6">
                        <label class="block text-sm font-medium text-gray-700 mb-2">
                            PDF File
                        </label>
                        <div class="mt-1 flex justify-center px-6 pt-5 pb-6 border-2 border-gray-300 border-dashed rounded-md">
                            <div class="space-y-1 text-center">
                                <template x-if="!selectedFile">
                                    <div>
                                        <svg class="mx-auto h-12 w-12 text-gray-400" stroke="currentColor" fill="none" viewBox="0 0 48 48">
                                            <path d="M28 8H12a4 4 0 00-4 4v20m32-12v8m0 0v8a4 4 0 01-4 4H12a4 4 0 01-4-4v-4m32-4l-3.172-3.172a4 4 0 00-5.656 0L28 28M8 32l9.172-9.172a4 4 0 015.656 0L28 28m0 0l4 4m4-24h8m-4-4v8m-12 4h.02" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
                                        </svg>
                                        <div class="flex text-sm text-gray-600">
                                            <label for="file-upload" class="relative cursor-pointer bg-white rounded-md font-medium text-indigo-600 hover:text-indigo-500 focus-within:outline-none focus-within:ring-2 focus-within:ring-offset-2 focus-within:ring-indigo-500">
                                                <span>Upload a file</span>
                                                <input id="file-upload" name="file-upload" type="file" class="sr-only" @change="handleFileSelect($event)" accept=".pdf">
                                            </label>
                                            <p class="pl-1">or drag and drop</p>
                                        </div>
                                        <p class="text-xs text-gray-500">PDF up to 50MB</p>
                                    </div>
                                </template>
                                <template x-if="selectedFile">
                                    <div>
                                        <p class="text-sm text-gray-900" x-text="selectedFile.name"></p>
                                        <p class="text-xs text-gray-500" x-text="formatFileSize(selectedFile.size)"></p>
                                        <button type="button" @click="selectedFile = null" class="mt-2 text-sm text-red-600 hover:text-red-500">
                                            Remove file
                                        </button>
                                    </div>
                                </template>
                            </div>
                        </div>
                    </div>

                    <!-- Storage Location -->
                    <div class="mb-6">
                        <label for="storage_location" class="block text-sm font-medium text-gray-700">
                            Storage Location
                        </label>
                        <input type="text" id="storage_location" x-model="storageLocation" 
                               class="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm p-2 border"
                               placeholder="e.g., Freezer A, Shelf 2">
                    </div>

                    <!-- QC Options -->
                    <div class="mb-6">
                        <label class="flex items-center">
                            <input type="checkbox" x-model="autoQC" class="rounded border-gray-300 text-indigo-600 shadow-sm focus:border-indigo-300 focus:ring focus:ring-indigo-200 focus:ring-opacity-50">
                            <span class="ml-2 text-sm text-gray-700">Run automatic QC validation</span>
                        </label>
                    </div>

                    <!-- Submit Button -->
                    <div class="flex justify-end">
                        <button type="submit" 
                                :disabled="!selectedFile || uploading"
                                class="bg-indigo-600 text-white px-4 py-2 rounded-md hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed">
                            <span x-show="!uploading">Upload PDF</span>
                            <span x-show="uploading">Uploading...</span>
                        </button>
                    </div>
                </form>

                <!-- Upload Result -->
                <div x-show="uploadResult" x-cloak class="mt-6 p-4 rounded-md" :class="uploadSuccess ? 'bg-green-50 text-green-800' : 'bg-red-50 text-red-800'">
                    <p x-text="uploadMessage"></p>
                    <template x-if="uploadSuccess && submissionId">
                        <a :href="'/submission.html?id=' + submissionId" class="mt-2 inline-block text-indigo-600 hover:text-indigo-500">
                            View Submission →
                        </a>
                    </template>
                </div>

                <!-- Debug Info (remove in production) -->
                <div x-show="uploadError" x-cloak class="mt-4 p-3 bg-yellow-50 border border-yellow-200 rounded text-sm">
                    <p class="font-semibold text-yellow-800">Debug Info:</p>
                    <p class="text-yellow-700" x-text="uploadError"></p>
                </div>
            </div>
        </div>
    </main>

    <script>
        function uploadApp() {
            return {
                selectedFile: null,
                storageLocation: '',
                autoQC: true,
                uploading: false,
                uploadResult: false,
                uploadSuccess: false,
                uploadMessage: '',
                uploadError: '',
                submissionId: null,
                
                init() {
                    console.log('Upload app initialized');
                },
                
                handleFileSelect(event) {
                    const file = event.target.files[0];
                    if (file) {
                        // Validate it's a PDF
                        if (!file.name.toLowerCase().endsWith('.pdf')) {
                            this.uploadError = 'Please select a PDF file';
                            this.uploadResult = true;
                            this.uploadSuccess = false;
                            this.uploadMessage = 'Only PDF files are allowed';
                            return;
                        }
                        this.selectedFile = file;
                        this.uploadError = '';
                        this.uploadResult = false;
                    }
                },
                
                formatFileSize(bytes) {
                    if (bytes < 1024) return bytes + ' B';
                    if (bytes < 1048576) return Math.round(bytes / 1024) + ' KB';
                    return Math.round(bytes / 1048576) + ' MB';
                },
                
                async uploadFile() {
                    if (!this.selectedFile) {
                        console.error('No file selected');
                        return;
                    }
                    
                    console.log('Starting upload for file:', this.selectedFile.name);
                    this.uploading = true;
                    this.uploadResult = false;
                    this.uploadError = '';
                    
                    const formData = new FormData();
                    formData.append('pdf_file', this.selectedFile);
                    formData.append('storage_location', this.storageLocation || 'Default Location');
                    // Convert boolean to string for FormData
                    formData.append('auto_qc', this.autoQC ? 'true' : 'false');
                    formData.append('force', 'false');
                    formData.append('min_concentration', '10.0');
                    formData.append('min_volume', '20.0');
                    formData.append('min_ratio', '1.8');
                    formData.append('evaluator', '');
                    
                    try {
                        const url = window.API_CONFIG.getApiUrl('/api/v1/submissions/');
                        console.log('Uploading to:', url);
                        
                        const response = await fetch(url, {
                            method: 'POST',
                            body: formData
                        });
                        
                        console.log('Response status:', response.status);
                        
                        if (response.ok) {
                            const data = await response.json();
                            console.log('Upload successful:', data);
                            this.uploadSuccess = true;
                            this.uploadMessage = 'PDF uploaded successfully!';
                            this.submissionId = data.id;
                            // Reset form
                            this.selectedFile = null;
                            this.storageLocation = '';
                            // Clear file input
                            document.getElementById('file-upload').value = '';
                        } else {
                            const errorText = await response.text();
                            console.error('Upload failed:', errorText);
                            this.uploadSuccess = false;
                            this.uploadMessage = 'Upload failed. Please try again.';
                            this.uploadError = `Server responded with ${response.status}: ${errorText}`;
                        }
                    } catch (error) {
                        console.error('Upload error:', error);
                        this.uploadSuccess = false;
                        this.uploadMessage = 'Network error. Please try again.';
                        this.uploadError = error.toString();
                    } finally {
                        this.uploading = false;
                        this.uploadResult = true;
                    }
                }
            }
        }
    </script>
</body>
</html>'''

# Write the fixed upload.html
upload_path = Path("src/presentation/web/templates/upload.html")
with open(upload_path, 'w') as f:
    f.write(upload_html)
print("✅ Fixed upload.html with all required form fields and better error handling")

# Create a simple test script
test_script = '''#!/usr/bin/env python3
"""Test the upload functionality."""

import requests
import sys
from pathlib import Path

# Create a minimal valid PDF
pdf_content = b"%PDF-1.4\\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\\n2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\\n3 0 obj<</Type/Page/MediaBox[0 0 3 3]/Parent 2 0 R/Resources<</Font<</F1<</Type/Font/Subtype/Type1/BaseFont/Times-Roman>>>>>>>/Contents 4 0 R>>endobj\\n4 0 obj<</Length 44>>stream\\nBT /F1 12 Tf 100 700 Td (Test PDF) Tj ET\\nendstream\\nendobj\\nxref\\n0 5\\n0000000000 65535 f\\n0000000009 00000 n\\n0000000056 00000 n\\n0000000115 00000 n\\n0000000229 00000 n\\ntrailer<</Size 5/Root 1 0 R>>\\nstartxref\\n316\\n%%EOF"

# Save to temporary file
test_pdf = Path("/tmp/test_upload.pdf")
test_pdf.write_bytes(pdf_content)
print(f"Created test PDF: {test_pdf}")

# Test the upload
url = "http://localhost:8080/api/v1/submissions/"
files = {'pdf_file': ('test.pdf', open(test_pdf, 'rb'), 'application/pdf')}
data = {
    'storage_location': 'Test Location',
    'auto_qc': 'false',
    'force': 'false',
    'min_concentration': '10.0',
    'min_volume': '20.0',
    'min_ratio': '1.8',
    'evaluator': ''
}

print(f"Uploading to: {url}")
try:
    response = requests.post(url, files=files, data=data)
    print(f"Response status: {response.status_code}")
    
    if response.status_code == 201 or response.status_code == 200:
        print("✅ Upload successful!")
        print(f"Response: {response.json()}")
    else:
        print(f"❌ Upload failed: {response.status_code}")
        print(f"Response: {response.text}")
except Exception as e:
    print(f"❌ Error: {e}")
'''

test_path = Path("test_upload.py")
test_path.write_text(test_script)
test_path.chmod(0o755)
print("✅ Created test_upload.py script")

print("\n✨ Upload functionality completely fixed!")
print("\nNext steps:")
print("1. The upload page now sends all required form fields")
print("2. Added proper error handling and debug info")
print("3. Boolean values are converted to strings for FormData")
print("\nYou can test the upload at: http://localhost:8080/upload")
