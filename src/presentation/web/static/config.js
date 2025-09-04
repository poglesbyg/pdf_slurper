// Local Development Configuration
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
console.log('API Configuration (LOCAL):', window.API_CONFIG.getApiUrl());
