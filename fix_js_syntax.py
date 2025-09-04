#!/usr/bin/env python3
"""Fix JavaScript syntax errors in all template pages."""

from pathlib import Path

# Fixed dashboard template
dashboard_html = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dashboard - PDF Slurper</title>
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
                        <a href="/" class="border-indigo-500 text-gray-900 inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium">
                            Dashboard
                        </a>
                        <a href="/submissions" class="border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700 inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium">
                            Submissions
                        </a>
                        <a href="/upload" class="border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700 inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium">
                            Upload
                        </a>
                    </div>
                </div>
            </div>
        </div>
    </nav>

    <!-- Main Content -->
    <main class="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        <div x-data="dashboardApp()" x-init="init()">
            <!-- Header -->
            <div class="px-4 sm:px-0 mb-6">
                <h2 class="text-2xl font-bold text-gray-900">Dashboard</h2>
                <p class="mt-1 text-sm text-gray-600">Overview of all submissions and samples</p>
            </div>

            <!-- Statistics Cards -->
            <div class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
                <div class="bg-white p-6 rounded-lg shadow">
                    <p class="text-sm font-medium text-gray-600">Total Submissions</p>
                    <p class="text-2xl font-bold text-gray-900" x-text="statistics.total_submissions">0</p>
                </div>
                <div class="bg-white p-6 rounded-lg shadow">
                    <p class="text-sm font-medium text-gray-600">Total Samples</p>
                    <p class="text-2xl font-bold text-gray-900" x-text="statistics.total_samples">0</p>
                </div>
                <div class="bg-white p-6 rounded-lg shadow">
                    <p class="text-sm font-medium text-gray-600">Passed QC</p>
                    <p class="text-2xl font-bold text-green-600" x-text="statistics.passed_samples">0</p>
                </div>
                <div class="bg-white p-6 rounded-lg shadow">
                    <p class="text-sm font-medium text-gray-600">Failed QC</p>
                    <p class="text-2xl font-bold text-red-600" x-text="statistics.failed_samples">0</p>
                </div>
            </div>

            <!-- Recent Submissions -->
            <div class="bg-white shadow rounded-lg">
                <div class="px-6 py-4 border-b">
                    <h3 class="text-lg font-medium text-gray-900">Recent Submissions</h3>
                </div>
                <div class="overflow-x-auto">
                    <table class="min-w-full divide-y divide-gray-200">
                        <thead class="bg-gray-50">
                            <tr>
                                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">ID</th>
                                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Requester</th>
                                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Lab</th>
                                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Storage</th>
                                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Samples</th>
                                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
                            </tr>
                        </thead>
                        <tbody class="bg-white divide-y divide-gray-200">
                            <template x-for="submission in submissions" :key="submission.id">
                                <tr class="hover:bg-gray-50">
                                    <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900" x-text="submission.id.substring(0, 8) + '...'"></td>
                                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500" x-text="submission.metadata?.requester || '-'"></td>
                                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500" x-text="submission.metadata?.lab || '-'"></td>
                                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500" x-text="submission.metadata?.storage_location || '-'"></td>
                                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500" x-text="submission.sample_count"></td>
                                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                        <a :href="'/submission.html?id=' + submission.id" class="text-indigo-600 hover:text-indigo-900">View</a>
                                    </td>
                                </tr>
                            </template>
                        </tbody>
                    </table>
                </div>
                <div class="px-6 py-4 border-t">
                    <a href="/submissions" class="text-indigo-600 hover:text-indigo-900 text-sm font-medium">View all submissions →</a>
                </div>
            </div>
        </div>
    </main>

    <script>
        function dashboardApp() {
            return {
                statistics: { total_submissions: 0, total_samples: 0, passed_samples: 0, failed_samples: 0 },
                submissions: [],
                
                async init() {
                    await this.loadStatistics();
                    await this.loadSubmissions();
                },
                
                async loadStatistics() {
                    try {
                        const response = await fetch(window.API_CONFIG.getApiUrl('/api/v1/submissions/statistics'));
                        if (response.ok) {
                            this.statistics = await response.json();
                        }
                    } catch (error) {
                        console.error('Error loading statistics:', error);
                    }
                },
                
                async loadSubmissions() {
                    try {
                        const response = await fetch(window.API_CONFIG.getApiUrl('/api/v1/submissions/?limit=10'));
                        if (response.ok) {
                            const data = await response.json();
                            this.submissions = data.items || [];
                        }
                    } catch (error) {
                        console.error('Error loading submissions:', error);
                    }
                }
            }
        }
    </script>
</body>
</html>'''

# Fixed submissions template
submissions_html = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Submissions - PDF Slurper</title>
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
                        <a href="/submissions" class="border-indigo-500 text-gray-900 inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium">
                            Submissions
                        </a>
                        <a href="/upload" class="border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700 inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium">
                            Upload
                        </a>
                    </div>
                </div>
            </div>
        </div>
    </nav>

    <!-- Main Content -->
    <main class="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        <div x-data="submissionsApp()" x-init="init()">
            <!-- Header -->
            <div class="px-4 sm:px-0 mb-6 flex justify-between items-center">
                <div>
                    <h2 class="text-2xl font-bold text-gray-900">All Submissions</h2>
                    <p class="mt-1 text-sm text-gray-600">Browse and manage all PDF submissions</p>
                </div>
                <a href="/upload" class="bg-indigo-600 text-white px-4 py-2 rounded-md hover:bg-indigo-700">
                    Upload New PDF
                </a>
            </div>

            <!-- Submissions Table -->
            <div class="bg-white shadow rounded-lg">
                <div class="overflow-x-auto">
                    <table class="min-w-full divide-y divide-gray-200">
                        <thead class="bg-gray-50">
                            <tr>
                                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Submission ID</th>
                                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Created</th>
                                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Requester</th>
                                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Lab</th>
                                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Storage Location</th>
                                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Samples</th>
                                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
                            </tr>
                        </thead>
                        <tbody class="bg-white divide-y divide-gray-200">
                            <template x-for="submission in submissions" :key="submission.id">
                                <tr class="hover:bg-gray-50">
                                    <td class="px-6 py-4 whitespace-nowrap">
                                        <div class="text-sm font-medium text-gray-900" x-text="submission.id"></div>
                                    </td>
                                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500" x-text="formatDate(submission.created_at)"></td>
                                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500" x-text="submission.metadata?.requester || '-'"></td>
                                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500" x-text="submission.metadata?.lab || '-'"></td>
                                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500" x-text="submission.metadata?.storage_location || '-'"></td>
                                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500" x-text="submission.sample_count"></td>
                                    <td class="px-6 py-4 whitespace-nowrap text-sm font-medium">
                                        <a :href="'/submission.html?id=' + submission.id" class="text-indigo-600 hover:text-indigo-900">View Details</a>
                                    </td>
                                </tr>
                            </template>
                        </tbody>
                    </table>
                </div>

                <!-- Pagination -->
                <div class="px-6 py-4 border-t flex justify-between items-center">
                    <div class="text-sm text-gray-700">
                        Showing <span x-text="((currentPage - 1) * pageSize) + 1"></span> to 
                        <span x-text="Math.min(currentPage * pageSize, totalCount)"></span> of 
                        <span x-text="totalCount"></span> results
                    </div>
                    <div class="flex space-x-2">
                        <button @click="previousPage()" :disabled="currentPage === 1" 
                                class="px-3 py-1 border rounded text-sm disabled:opacity-50 disabled:cursor-not-allowed">
                            Previous
                        </button>
                        <button @click="nextPage()" :disabled="currentPage >= totalPages" 
                                class="px-3 py-1 border rounded text-sm disabled:opacity-50 disabled:cursor-not-allowed">
                            Next
                        </button>
                    </div>
                </div>
            </div>
        </div>
    </main>

    <script>
        function submissionsApp() {
            return {
                submissions: [],
                currentPage: 1,
                pageSize: 20,
                totalCount: 0,
                totalPages: 1,
                
                async init() {
                    await this.loadSubmissions();
                },
                
                async loadSubmissions() {
                    try {
                        const offset = (this.currentPage - 1) * this.pageSize;
                        const url = window.API_CONFIG.getApiUrl('/api/v1/submissions/?limit=' + this.pageSize + '&offset=' + offset);
                        const response = await fetch(url);
                        if (response.ok) {
                            const data = await response.json();
                            this.submissions = data.items || [];
                            this.totalCount = data.total || 0;
                            this.totalPages = Math.ceil(this.totalCount / this.pageSize);
                        }
                    } catch (error) {
                        console.error('Error loading submissions:', error);
                    }
                },
                
                formatDate(dateString) {
                    return new Date(dateString).toLocaleDateString();
                },
                
                async previousPage() {
                    if (this.currentPage > 1) {
                        this.currentPage--;
                        await this.loadSubmissions();
                    }
                },
                
                async nextPage() {
                    if (this.currentPage < this.totalPages) {
                        this.currentPage++;
                        await this.loadSubmissions();
                    }
                }
            }
        }
    </script>
</body>
</html>'''

# Fixed upload template  
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
                                                <input id="file-upload" name="file-upload" type="file" class="sr-only" @change="selectedFile = $event.target.files[0]" accept=".pdf">
                                            </label>
                                            <p class="pl-1">or drag and drop</p>
                                        </div>
                                        <p class="text-xs text-gray-500">PDF up to 10MB</p>
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
                submissionId: null,
                
                init() {
                    // Initialize
                },
                
                formatFileSize(bytes) {
                    if (bytes < 1024) return bytes + ' B';
                    if (bytes < 1048576) return Math.round(bytes / 1024) + ' KB';
                    return Math.round(bytes / 1048576) + ' MB';
                },
                
                async uploadFile() {
                    if (!this.selectedFile) return;
                    
                    this.uploading = true;
                    this.uploadResult = false;
                    
                    const formData = new FormData();
                    formData.append('pdf_file', this.selectedFile);
                    formData.append('storage_location', this.storageLocation || 'Default Location');
                    formData.append('auto_qc', this.autoQC);
                    
                    try {
                        const response = await fetch(window.API_CONFIG.getApiUrl('/api/v1/submissions/upload'), {
                            method: 'POST',
                            body: formData
                        });
                        
                        if (response.ok) {
                            const data = await response.json();
                            this.uploadSuccess = true;
                            this.uploadMessage = 'PDF uploaded successfully!';
                            this.submissionId = data.id;
                            this.selectedFile = null;
                            this.storageLocation = '';
                        } else {
                            this.uploadSuccess = false;
                            this.uploadMessage = 'Upload failed. Please try again.';
                        }
                    } catch (error) {
                        this.uploadSuccess = false;
                        this.uploadMessage = 'Network error. Please try again.';
                        console.error('Upload error:', error);
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

# Fixed submission detail template
submission_detail_html = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Submission Detail - PDF Slurper</title>
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
                        <a href="/upload" class="border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700 inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium">
                            Upload
                        </a>
                    </div>
                </div>
            </div>
        </div>
    </nav>

    <!-- Main Content -->
    <main class="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        <div x-data="submissionDetailApp()" x-init="init()">
            <!-- Loading State -->
            <div x-show="loading" class="text-center py-8">
                <div class="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
                <p class="mt-2 text-gray-600">Loading submission...</p>
            </div>

            <!-- Content -->
            <div x-show="!loading && submission" x-cloak>
                <!-- Header -->
                <div class="mb-6">
                    <a href="/submissions" class="text-indigo-600 hover:text-indigo-900 text-sm">← Back to Submissions</a>
                    <h2 class="mt-4 text-2xl font-bold text-gray-900">Submission Details</h2>
                </div>

                <!-- Submission Info -->
                <div class="bg-white shadow rounded-lg p-6 mb-6">
                    <h3 class="text-lg font-medium text-gray-900 mb-4">Submission Information</h3>
                    <dl class="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div>
                            <dt class="text-sm font-medium text-gray-500">Submission ID</dt>
                            <dd class="mt-1 text-sm text-gray-900" x-text="submission?.id || '-'"></dd>
                        </div>
                        <div>
                            <dt class="text-sm font-medium text-gray-500">Storage Location</dt>
                            <dd class="mt-1 text-sm text-gray-900 font-semibold text-indigo-600" x-text="submission?.metadata?.storage_location || '-'"></dd>
                        </div>
                        <div>
                            <dt class="text-sm font-medium text-gray-500">Requester</dt>
                            <dd class="mt-1 text-sm text-gray-900" x-text="submission?.metadata?.requester || '-'"></dd>
                        </div>
                        <div>
                            <dt class="text-sm font-medium text-gray-500">Lab</dt>
                            <dd class="mt-1 text-sm text-gray-900" x-text="submission?.metadata?.lab || '-'"></dd>
                        </div>
                        <div>
                            <dt class="text-sm font-medium text-gray-500">Service Requested</dt>
                            <dd class="mt-1 text-sm text-gray-900" x-text="submission?.metadata?.service_requested || '-'"></dd>
                        </div>
                        <div>
                            <dt class="text-sm font-medium text-gray-500">Created</dt>
                            <dd class="mt-1 text-sm text-gray-900" x-text="formatDate(submission?.created_at)"></dd>
                        </div>
                    </dl>
                </div>

                <!-- Samples Table -->
                <div class="bg-white shadow rounded-lg">
                    <div class="px-6 py-4 border-b">
                        <h3 class="text-lg font-medium text-gray-900">Samples (<span x-text="samples.length"></span>)</h3>
                    </div>
                    <div class="overflow-x-auto">
                        <table class="min-w-full divide-y divide-gray-200">
                            <thead class="bg-gray-50">
                                <tr>
                                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Name</th>
                                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Volume (μL)</th>
                                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Concentration (ng/μL)</th>
                                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">A260/A280</th>
                                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                                </tr>
                            </thead>
                            <tbody class="bg-white divide-y divide-gray-200">
                                <template x-for="sample in samples" :key="sample.id">
                                    <tr class="hover:bg-gray-50">
                                        <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900" x-text="sample.sample_name"></td>
                                        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500" x-text="sample.volume || '-'"></td>
                                        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500" x-text="sample.concentration || '-'"></td>
                                        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500" x-text="sample.a260_a280 || '-'"></td>
                                        <td class="px-6 py-4 whitespace-nowrap">
                                            <span x-show="sample.qc_status === 'passed'" class="px-2 py-1 inline-flex text-xs leading-5 font-semibold rounded-full bg-green-100 text-green-800">
                                                Passed
                                            </span>
                                            <span x-show="sample.qc_status === 'failed'" class="px-2 py-1 inline-flex text-xs leading-5 font-semibold rounded-full bg-red-100 text-red-800">
                                                Failed
                                            </span>
                                            <span x-show="sample.qc_status === 'pending'" class="px-2 py-1 inline-flex text-xs leading-5 font-semibold rounded-full bg-yellow-100 text-yellow-800">
                                                Pending
                                            </span>
                                        </td>
                                    </tr>
                                </template>
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>
    </main>

    <script>
        function submissionDetailApp() {
            return {
                submission: null,
                samples: [],
                loading: true,
                
                async init() {
                    const urlParams = new URLSearchParams(window.location.search);
                    const submissionId = urlParams.get('id') || window.location.pathname.split('/submission/')[1];
                    
                    if (submissionId) {
                        await this.loadSubmission(submissionId);
                        await this.loadSamples(submissionId);
                    }
                    this.loading = false;
                },
                
                async loadSubmission(id) {
                    try {
                        const url = window.API_CONFIG.getApiUrl('/api/v1/submissions/' + id);
                        const response = await fetch(url);
                        if (response.ok) {
                            this.submission = await response.json();
                        }
                    } catch (error) {
                        console.error('Error loading submission:', error);
                    }
                },
                
                async loadSamples(id) {
                    try {
                        const url = window.API_CONFIG.getApiUrl('/api/v1/submissions/' + id + '/samples');
                        const response = await fetch(url);
                        if (response.ok) {
                            this.samples = await response.json();
                        }
                    } catch (error) {
                        console.error('Error loading samples:', error);
                    }
                },
                
                formatDate(dateString) {
                    if (!dateString) return '-';
                    return new Date(dateString).toLocaleString();
                }
            }
        }
    </script>
</body>
</html>'''

# Write all fixed templates
templates_dir = Path("src/presentation/web/templates")

print("🔧 Fixing JavaScript syntax errors in all pages...")

pages = {
    "dashboard.html": dashboard_html,
    "submissions.html": submissions_html,
    "upload.html": upload_html,
    "submission_detail.html": submission_detail_html
}

for filename, content in pages.items():
    filepath = templates_dir / filename
    with open(filepath, 'w') as f:
        f.write(content)
    print(f"  ✅ Fixed {filename}")

print("\n✨ All JavaScript syntax errors fixed!")
print("\nAll pages now have:")
print("  ✅ Correct JavaScript syntax (no escaped backticks)")
print("  ✅ String concatenation instead of template literals in URLs")
print("  ✅ Proper Alpine.js structure")
print("  ✅ Uniform navigation and styling")
