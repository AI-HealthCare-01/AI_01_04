// components.js - Shared UI components (Sidebar/Navbar)

function renderSidebar() {
    const activePage = window.location.pathname.split('/').pop() || 'dashboard.html';

    // Current user context
    const userName = localStorage.getItem('user_name') || window.getText('common.userFallbackName', '사용자');

    const sidebarHtml = `
        <nav class="d-flex justify-content-between align-items-center p-3 shadow-sm sticky-top bg-white border-bottom">
            <div class="h5 mb-0 fw-bold text-primary-custom" style="cursor:pointer;" onclick="window.location.href='dashboard.html'">
                <i class="bi bi-heart-pulse me-2"></i>${window.getText('common.serviceName', 'HealthCare AI')}
            </div>
            <button class="btn btn-outline-primary border-0 fs-4 py-0" type="button" data-bs-toggle="offcanvas"
                data-bs-target="#globalOffcanvasMenu" aria-controls="globalOffcanvasMenu">
                <i class="bi bi-list"></i>
            </button>
        </nav>

        <div class="offcanvas offcanvas-end" tabindex="-1" id="globalOffcanvasMenu" aria-labelledby="globalOffcanvasLabel">
            <div class="offcanvas-header bg-soft-primary pb-4 pt-4 border-bottom-0">
                <div class="d-flex align-items-center w-100">
                    <img id="menu-profile-img" src="https://ui-avatars.com/api/?name=${encodeURIComponent(userName)}&background=6da285&color=fff&size=48"
                        alt="프로필" class="profile-img-sm me-3 shadow-sm border border-light">
                    <div class="flex-grow-1 text-white">
                        <h5 class="mb-0 fw-bold" id="menu-user-name">${escapeHtml(userName)} 님</h5>
                        <span class="small opacity-75">회원</span>
                    </div>
                    <button type="button" class="btn-close btn-close-white" data-bs-dismiss="offcanvas" aria-label="Close"></button>
                </div>
            </div>

            <div class="offcanvas-body p-4 d-flex flex-column" style="background-color: var(--bg-color);">
                <h6 class="text-soft fw-bold mb-3 small text-uppercase">${window.getText('sidebar.sectionTitle', '나의 건강 서비스')}</h6>

                <a href="dashboard.html" class="d-flex align-items-center menu-item px-3 py-3 mb-2 text-decoration-none ${activePage === 'dashboard.html' ? 'bg-white shadow-sm' : ''}">
                    <div class="bg-soft-primary text-primary-custom rounded p-2 me-3"><i class="bi bi-house-door-fill fs-5"></i></div>
                    <span class="fw-medium">${window.getText('sidebar.menu.dashboard', '홈 (대시보드)')}</span>
                </a>
                <a href="profile.html" class="d-flex align-items-center menu-item px-3 py-3 mb-2 text-decoration-none ${activePage === 'profile.html' ? 'bg-white shadow-sm' : ''}">
                    <div class="bg-soft-primary text-primary-custom rounded p-2 me-3"><i class="bi bi-person-lines-fill fs-5"></i></div>
                    <span class="fw-medium">${window.getText('sidebar.menu.profile', '내 건강 프로필')}</span>
                </a>
                <a href="medications.html" class="d-flex align-items-center menu-item px-3 py-3 mb-2 text-decoration-none ${activePage === 'medications.html' ? 'bg-white shadow-sm' : ''}">
                    <div class="bg-soft-primary text-primary-custom rounded p-2 me-3"><i class="bi bi-capsule-pill fs-5"></i></div>
                    <span class="fw-medium">${window.getText('sidebar.menu.medications', '전체 복약 기록')}</span>
                </a>
                <a href="scans.html" class="d-flex align-items-center menu-item px-3 py-3 mb-2 text-decoration-none ${activePage === 'scans.html' ? 'bg-white shadow-sm' : ''}">
                    <div class="bg-soft-primary text-primary-custom rounded p-2 me-3"><i class="bi bi-file-earmark-medical-fill fs-5"></i></div>
                    <span class="fw-medium">${window.getText('sidebar.menu.scans', '처방전 관리 보관함')}</span>
                </a>
                <a href="recommendations.html" class="d-flex align-items-center menu-item px-3 py-3 mb-2 text-decoration-none ${activePage === 'recommendations.html' ? 'bg-white shadow-sm' : ''}">
                    <div class="bg-soft-primary text-primary-custom rounded p-2 me-3"><i class="bi bi-star-fill text-warning fs-5"></i></div>
                    <span class="fw-medium">${window.getText('sidebar.menu.recommendations', 'AI 맞춤 추천')}</span>
                </a>
                <a href="chatbot.html" class="d-flex align-items-center menu-item px-3 py-3 mb-2 text-decoration-none ${activePage === 'chatbot.html' ? 'bg-white shadow-sm' : ''}">
                    <div class="bg-soft-primary text-primary-custom rounded p-2 me-3"><i class="bi bi-chat-dots-fill fs-5"></i></div>
                    <span class="fw-medium">${window.getText('sidebar.menu.chatbot', 'AI 건강 상담')}</span>
                </a>

                <div class="mt-auto pt-4 border-top">
                    <button onclick="window.api.logout(); return false;" class="d-flex align-items-center text-danger text-decoration-none px-3 py-2 menu-item btn btn-link w-100 text-start">
                        <i class="bi bi-box-arrow-right me-3 fs-5"></i><span class="fw-bold">\${window.getText('sidebar.menu.logout', '로그아웃')}</span>
                    </button>
                </div>
            </div>
        </div>
    `;

    // Inject sidebar into element with id 'sidebar-container'
    let container = document.getElementById('sidebar-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'sidebar-container';
        document.body.insertBefore(container, document.body.firstChild);
    }
    container.innerHTML = sidebarHtml;
}

// Initialize components when DOM is ready
document.addEventListener("DOMContentLoaded", () => {
    // Basic Auth Check for non-index pages
    if (window.location.pathname.indexOf('index.html') === -1) {
        if (!localStorage.getItem('access_token')) {
            window.location.href = 'index.html';
        } else {
            renderSidebar();
        }
    }
});
