#!/usr/bin/env python3
"""Fix submission detail page routing."""

# Read the start_combined.py file
with open('start_combined.py', 'r') as f:
    content = f.read()

# Find the submission route
old_route = '''    @app.get("/submission/{submission_id}", response_class=HTMLResponse)
    async def submission_detail(request: Request, submission_id: str):
        """Submission detail page."""
        return templates.TemplateResponse("submission_detail.html", {
            "request": request,
            "submission_id": submission_id
        })'''

# Replace with routes that handle both patterns
new_routes = '''    @app.get("/submission/{submission_id}", response_class=HTMLResponse)
    async def submission_detail_path(request: Request, submission_id: str):
        """Submission detail page with path parameter."""
        return templates.TemplateResponse("submission_detail.html", {
            "request": request,
            "submission_id": submission_id
        })
    
    @app.get("/submission.html", response_class=HTMLResponse)
    async def submission_detail_query(request: Request):
        """Submission detail page with query parameter."""
        submission_id = request.query_params.get("id", "")
        return templates.TemplateResponse("submission_detail.html", {
            "request": request,
            "submission_id": submission_id
        })
    
    @app.get("/submission_detail.html", response_class=HTMLResponse)
    async def submission_detail_page(request: Request):
        """Submission detail page (alternative URL)."""
        submission_id = request.query_params.get("id", "")
        return templates.TemplateResponse("submission_detail.html", {
            "request": request,
            "submission_id": submission_id
        })'''

# Replace the old route with new routes
if old_route in content:
    content = content.replace(old_route, new_routes)
    print("✅ Updated submission routes")
else:
    print("⚠️ Could not find original route, adding new routes...")
    # Find where to insert (after submissions page route)
    insert_after = '''    @app.get("/submissions", response_class=HTMLResponse)
    async def submissions_page(request: Request):
        """Submissions page."""
        return templates.TemplateResponse("submissions.html", {"request": request})'''
    
    if insert_after in content:
        content = content.replace(insert_after, insert_after + "\n" + new_routes)
        print("✅ Added submission routes")

# Write back
with open('start_combined.py', 'w') as f:
    f.write(content)

print("The server should auto-reload with the changes.")
