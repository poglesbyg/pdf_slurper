// API Configuration for OpenShift deployment
window.API_CONFIG = {
    // Direct API URL - ensure HTTPS
    API_BASE_URL: 'https://pdf-slurper-v2-dept-barc.apps.cloudapps.unc.edu',
    
    // Helper function to build API URLs
    getApiUrl: function(endpoint) {
        // Remove leading slash if present
        if (endpoint.startsWith('/')) {
            endpoint = endpoint.substring(1);
        }
        // Ensure the URL uses HTTPS
        const url = `${this.API_BASE_URL}/${endpoint}`;
        // Force HTTPS if somehow it got changed to HTTP
        return url.replace(/^http:/, 'https:');
    }
};

console.log('API Configuration loaded:', window.API_CONFIG.API_BASE_URL);
