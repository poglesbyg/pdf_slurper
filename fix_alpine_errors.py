#!/usr/bin/env python3
"""Fix Alpine.js errors in submission detail page."""

from pathlib import Path

# Read the current submission_detail.html
detail_path = Path("src/presentation/web/templates/submission_detail.html")
with open(detail_path, 'r') as f:
    content = f.read()

# Fix 1: Use index as key instead of sample.id which might be undefined
old_xfor = '<template x-for="sample in samples" :key="sample.id">'
new_xfor = '<template x-for="(sample, index) in samples" :key="index">'

if old_xfor in content:
    content = content.replace(old_xfor, new_xfor)
    print("✅ Fixed x-for loop to use index as key")
else:
    print("⚠️ x-for loop not found or already fixed")

# Fix 2: Ensure samples is always initialized as an array
old_init = '''                samples: [],
                loading: true,
                
                async init() {'''

new_init = '''                samples: [],
                loading: true,
                initialized: false,
                
                async init() {
                    // Prevent double initialization
                    if (this.initialized) return;
                    this.initialized = true;'''

if old_init in content:
    content = content.replace(old_init, new_init)
    print("✅ Added initialization guard to prevent duplicate execution")
else:
    print("⚠️ Init function pattern not found, trying alternative fix...")
    
    # Try to fix just the init function
    if 'async init() {' in content and 'if (this.initialized) return;' not in content:
        content = content.replace(
            'async init() {',
            'async init() {\n                    // Prevent double initialization\n                    if (this.initialized) return;\n                    this.initialized = true;'
        )
        # Also add initialized property
        content = content.replace(
            'loading: true,',
            'loading: true,\n                initialized: false,'
        )
        print("✅ Added initialization guard (alternative method)")

# Fix 3: Ensure samples is properly handled even if the API returns null
old_load_samples = '''                async loadSamples(id) {
                    try {
                        const url = window.API_CONFIG.getApiUrl('/api/v1/submissions/' + id + '/samples');
                        const response = await fetch(url);
                        if (response.ok) {
                            this.samples = await response.json();
                        }'''

new_load_samples = '''                async loadSamples(id) {
                    try {
                        const url = window.API_CONFIG.getApiUrl('/api/v1/submissions/' + id + '/samples');
                        const response = await fetch(url);
                        if (response.ok) {
                            const data = await response.json();
                            this.samples = Array.isArray(data) ? data : [];
                        }'''

if old_load_samples in content:
    content = content.replace(old_load_samples, new_load_samples)
    print("✅ Added array validation for samples data")
else:
    print("⚠️ loadSamples function not found or already fixed")

# Write back
with open(detail_path, 'w') as f:
    f.write(content)

print("\n✨ Alpine.js errors fixed!")
print("The submission detail page should now work without errors.")
