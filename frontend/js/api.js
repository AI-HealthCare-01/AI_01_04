// api.js - Core API Client

const BACKEND_ORIGIN = (() => {
    const override = typeof window.__BACKEND_ORIGIN__ === 'string' ? window.__BACKEND_ORIGIN__.trim() : '';
    if (override) {
        return override.replace(/\/$/, '');
    }

    if (window.location.protocol === 'file:') {
        return 'http://localhost:8000';
    }

    const isLocalHost = ['localhost', '127.0.0.1'].includes(window.location.hostname);
    if (window.location.port === '8000') {
        return window.location.origin;
    }

    if (isLocalHost) {
        return `${window.location.protocol}//${window.location.hostname}:8000`;
    }

    return window.location.origin;
})();
const API_BASE_URL = `${BACKEND_ORIGIN}/api/v1`;
const STATIC_BASE_URL = BACKEND_ORIGIN;

const getAccessToken = () => localStorage.getItem('access_token');
const setAccessToken = (token) => localStorage.setItem('access_token', token);
const clearAuth = () => {
    localStorage.removeItem('access_token');
    window.location.href = 'index.html';
};

function resolveBackendUrl(path) {
    if (!path) {
        return '';
    }
    if (/^https?:\/\//.test(path)) {
        return path;
    }
    return `${STATIC_BASE_URL}${path.startsWith('/') ? '' : '/'}${path}`;
}

function formatErrorDetail(detail) {
    if (!detail) {
        return null;
    }

    if (typeof detail === 'string') {
        return detail;
    }

    if (Array.isArray(detail)) {
        return detail
            .map((item) => {
                if (typeof item === 'string') {
                    return item;
                }
                if (item && typeof item === 'object') {
                    return item.msg || JSON.stringify(item);
                }
                return String(item);
            })
            .join('\n');
    }

    if (typeof detail === 'object') {
        return detail.msg || JSON.stringify(detail);
    }

    return String(detail);
}

function formatHttpStatusMessage(status) {
    switch (status) {
        case 400:
            return '요청 형식이 올바르지 않습니다.';
        case 401:
            return '로그인이 필요합니다.';
        case 403:
            return '이 작업을 수행할 권한이 없습니다.';
        case 404:
            return '요청한 정보를 찾을 수 없습니다.';
        case 409:
            return '이미 존재하는 정보와 충돌했습니다.';
        case 422:
            return '입력값을 다시 확인해주세요.';
        case 429:
            return 'OCR 서버 요청이 잠시 몰려 있습니다. 잠깐 기다린 뒤 다시 확인해주세요.';
        case 500:
            return '서버 내부 오류가 발생했습니다.';
        case 502:
            return '외부 연동 서버에서 오류가 발생했습니다.';
        case 504:
            return '분석 시간이 길어져 응답이 지연되었습니다. 잠시 후 결과를 다시 확인하거나 직접 수정해 주세요.';
        default:
            return `API error: ${status}`;
    }
}

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
        let response = await fetch(url, { ...options, headers, credentials: 'include' });

        if (response.status === 401 && !endpoint.startsWith('/auth/login') && !options._retried) {
            // Try refreshing token (once only)
            console.log("Token expired, attempting refresh...");
            const refreshRes = await fetch(`${API_BASE_URL}/auth/token/refresh`, {
                credentials: 'include',
            });
            if (refreshRes.ok) {
                const data = await refreshRes.json();
                setAccessToken(data.access_token);
                // Retry original request with new token (mark as retried)
                headers.set('Authorization', `Bearer ${data.access_token}`);
                response = await fetch(url, { ...options, headers, credentials: 'include', _retried: true });
            } else {
                // Refresh failed, clear and logout
                clearAuth();
                throw new Error("Authentication failed");
            }
        }

        if (!response.ok) {
            let errData;
            try { errData = await response.json(); } catch (e) { }
            throw new Error(formatErrorDetail(errData && errData.detail) || formatHttpStatusMessage(response.status));
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
    fetchAPI,
    resolveBackendUrl,
    login: (email, password) => fetchAPI('/auth/login', { method: 'POST', body: { email, password } }),
    signup: (name, email, gender, birthday, phone_number, password) => fetchAPI('/auth/signup', { method: 'POST', body: { name, email, gender, birthday, phone_number, password } }),
    logout: clearAuth,
    getUserMe: () => fetchAPI('/users/me'),
    getDashboardSummary: () => fetchAPI('/dashboard/summary'),
    getMedicationHistory: (params = '') => fetchAPI(`/medications/history${params}`),
    updateMedicationLog: (logId, status) => fetchAPI(`/medications/logs/${logId}`, { method: 'PATCH', body: { status } }),
    getHealthHistory: (params = '') => fetchAPI(`/health/history${params}`),
    updateHealthLog: (logId, status) => fetchAPI(`/health/logs/${logId}`, { method: 'PATCH', body: { status } }),
    uploadScan: (formData) => fetchAPI('/scans/upload', { method: 'POST', body: formData }),
    analyzeScan: (scanId) => fetchAPI(`/scans/${scanId}/analyze`, { method: 'POST' }),
    getScanResult: (scanId) => fetchAPI(`/scans/${scanId}`),
    updateScanResult: (scanId, body) => fetchAPI(`/scans/${scanId}/result`, { method: 'PATCH', body }),
    saveScanResult: (scanId) => fetchAPI(`/scans/${scanId}/save`, { method: 'POST' }),
    getRecommendationsForScan: (scanId) => fetchAPI(`/recommendations/scans/${scanId}`),
    saveRecommendationsForScan: (scanId) => fetchAPI(`/recommendations/scans/${scanId}/save`, { method: 'POST' }),
    searchDrugs: (q, limit = 10) => fetchAPI(`/drugs/search?q=${encodeURIComponent(q)}&limit=${limit}`),
    getActiveRecommendations: () => fetchAPI('/recommendations/active'),
    sendFeedback: (recId, type) => fetchAPI(`/recommendations/${recId}/feedback?feedback_type=${type}`, { method: 'POST' }),
    checkChatbotPatient: (patientId) => fetchAPI(`/chatbot/check-patient/${encodeURIComponent(patientId)}`),
    getChatbotHistory: (patientId) => fetchAPI(`/chatbot/history/${encodeURIComponent(patientId)}`),
    sendChatMessage: (body) => fetchAPI('/chatbot/chat', { method: 'POST', body })
};
