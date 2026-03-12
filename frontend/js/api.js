// api.js - Core API Client

const API_BASE_URL = 'http://localhost:8000/api/v1';

const getAccessToken = () => localStorage.getItem('access_token');
const setAccessToken = (token) => localStorage.setItem('access_token', token);
const clearAuth = () => {
    localStorage.removeItem('access_token');
    window.location.href = 'index.html';
};

// Simple fetch wrapper
async function fetchAPI(endpoint, options = {}) {
    const url = `${API_BASE_URL}${endpoint}`;

    // Set headers
    const headers = options.headers ? new Headers(options.headers) : new Headers();

    // Add auth token if exists and it's not an auth request
    const token = getAccessToken();
    if (token && !endpoint.startsWith('/auth')) {
        headers.set('Authorization', `Bearer ${token}`);
    }

    // Default to JSON if not uploading files
    if (!(options.body instanceof FormData)) {
        headers.set('Accept', 'application/json');
        if (options.body && typeof options.body === 'object') {
            options.body = JSON.stringify(options.body);
            headers.set('Content-Type', 'application/json');
        }
    }

    try {
        let response = await fetch(url, { ...options, headers });

        if (response.status === 401 && !endpoint.startsWith('/auth/login')) {
            // Try refreshing token
            console.log("Token expired, attempting refresh...");
            const refreshRes = await fetch(`${API_BASE_URL}/auth/token/refresh`);
            if (refreshRes.ok) {
                const data = await refreshRes.json();
                setAccessToken(data.access_token);
                // Retry original request with new token
                headers.set('Authorization', `Bearer ${data.access_token}`);
                response = await fetch(url, { ...options, headers });
            } else {
                // Refresh failed, clear and logout
                clearAuth();
                throw new Error("Authentication failed");
            }
        }

        if (!response.ok) {
            let errData;
            try { errData = await response.json(); } catch (e) { }
            throw new Error((errData && errData.detail) || `API error: ${response.status}`);
        }

        const contentType = response.headers.get("content-type");
        if (contentType && contentType.includes("application/json")) {
            return await response.json();
        }
        return await response.text();

    } catch (error) {
        console.error(`API Request failed for ${endpoint}:`, error);
        throw error;
    }
}

// Named exports/global functions
window.api = {
    login: (email, password) => fetchAPI('/auth/login', { method: 'POST', body: { email, password } }),
    signup: (name, email, gender, birthday, phone_number, password) => fetchAPI('/auth/signup', { method: 'POST', body: { name, email, gender, birthday, phone_number, password } }),
    logout: clearAuth,
    getUserMe: () => fetchAPI('/users/me'),
    getDashboardSummary: () => fetchAPI('/dashboard/summary'),
    getMedicationHistory: (params = '') => fetchAPI(`/medications/history${params}`),
    updateMedicationLog: (logId, status) => fetchAPI(`/medications/logs/${logId}`, { method: 'PATCH', body: { status } }),
    getHealthHistory: (params = '') => fetchAPI(`/health/history${params}`),
    uploadScan: (formData) => fetchAPI('/scans/upload', { method: 'POST', body: formData }),
    analyzeScan: (scanId) => fetchAPI(`/scans/${scanId}/analyze`, { method: 'POST' }),
    saveScanResult: (scanId) => fetchAPI(`/scans/${scanId}/save`, { method: 'POST' }),
    getActiveRecommendations: () => fetchAPI('/recommendations/active'),
    sendFeedback: (recId, type) => fetchAPI(`/recommendations/${recId}/feedback?feedback_type=${type}`, { method: 'POST' })
};
