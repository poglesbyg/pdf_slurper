#!/usr/bin/env python3
"""Fix to serve config.js properly in the FastAPI app."""

# Read the start_combined.py file
with open('start_combined.py', 'r') as f:
    content = f.read()

# Find where to insert the config.js route
# We'll add it right after the health check endpoints
insert_position = content.find('    # API Routes')

if insert_position == -1:
    print("Could not find insertion point")
    exit(1)

# Add the config.js route
config_route = '''    # Serve config.js
    @app.get("/config.js", response_class=HTMLResponse)
    async def serve_config():
        """Serve the config.js file."""
        config_content = """// Local Development Configuration
window.API_CONFIG = {
    getApiUrl: function(path) {
        const baseUrl = 'http://localhost:8080';
        if (!path) return baseUrl;
        const cleanPath = path.startsWith('/') ? path : '/' + path;
        return baseUrl + cleanPath;
    },
    apiBase: '/api/v1'
};

window.config = window.API_CONFIG;
console.log('API Configuration (LOCAL):', window.API_CONFIG.getApiUrl());"""
        return HTMLResponse(content=config_content, media_type="application/javascript")
    
    '''

# Insert the route
new_content = content[:insert_position] + config_route + content[insert_position:]

# Write back
with open('start_combined.py', 'w') as f:
    f.write(new_content)

print("✅ Added config.js route to start_combined.py")
print("The server should auto-reload with the changes.")
