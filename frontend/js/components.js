// components.js - Shared UI components (Sidebar/Navbar)

function renderSidebar() {
    const activePage = window.location.pathname.split('/').pop() || 'dashboard.html';

    // Current user context
    const userName = localStorage.getItem('user_name') || window.getText('common.userFallbackName', '사용자');

    const sidebarHtml = `
        <div class="p-4 d-flex flex-column h-100">
            <div class="mb-4 text-center">
                <i class="bi bi-heart-pulse text-primary-custom" style="font-size: 2rem;"></i>
                <h4 class="fw-bold text-primary-custom mt-2 mb-0">${window.getText('common.serviceName', 'HealthCare AI')}</h4>
                <p class="text-soft small mt-1">${window.getText('common.serviceTagline', '당신의 곁에, 언제나')}</p>
            </div>
            
            <div class="user-block p-3 mb-4 bg-light rounded text-center">
                <img src="https://ui-avatars.com/api/?name=${encodeURIComponent(userName)}&background=random&color=fff&size=48" class="profile-img-sm mb-2 shadow-sm">
                <h6 class="mb-0 fw-bold">${userName} 님</h6>
            </div>

            <div class="menu-list flex-grow-1">
                <p class="text-soft fw-bold mb-2 small px-2">${window.getText('sidebar.sectionTitle', '나의 건강 서비스')}</p>
                <a href="dashboard.html" class="d-flex align-items-center menu-item px-3 py-2 ${activePage === 'dashboard.html' ? 'active' : ''}">
                    <div class="icon-box p-2 me-3"><i class="bi bi-house-door-fill"></i></div>
                    <span>${window.getText('sidebar.menu.dashboard', '대시보드')}</span>
                </a>
                <a href="medications.html" class="d-flex align-items-center menu-item px-3 py-2 ${activePage === 'medications.html' ? 'active' : ''}">
                    <div class="icon-box p-2 me-3"><i class="bi bi-capsule-pill"></i></div>
                    <span>${window.getText('sidebar.menu.medications', '복약 관리')}</span>
                </a>
                <a href="health.html" class="d-flex align-items-center menu-item px-3 py-2 ${activePage === 'health.html' ? 'active' : ''}">
                    <div class="icon-box p-2 me-3"><i class="bi bi-activity"></i></div>
                    <span>${window.getText('sidebar.menu.health', '일상 건강')}</span>
                </a>
                <a href="scans.html" class="d-flex align-items-center menu-item px-3 py-2 ${activePage === 'scans.html' ? 'active' : ''}">
                    <div class="icon-box p-2 me-3"><i class="bi bi-file-earmark-medical-fill"></i></div>
                    <span>${window.getText('sidebar.menu.scans', '처방전 스캔')}</span>
                </a>
                <a href="recommendations.html" class="d-flex align-items-center menu-item px-3 py-2 ${activePage === 'recommendations.html' ? 'active' : ''}">
                    <div class="icon-box p-2 me-3"><i class="bi bi-star-fill text-warning"></i></div>
                    <span>${window.getText('sidebar.menu.recommendations', 'AI 맞춤 추천')}</span>
                </a>
            </div>

            <div class="mt-auto">
                <a href="profile.html" class="d-flex align-items-center menu-item px-3 py-2 mb-2 ${activePage === 'profile.html' ? 'active' : ''}">
                    <div class="icon-box p-2 me-3"><i class="bi bi-person-circle"></i></div>
                    <span>${window.getText('sidebar.menu.profile', '내 프로필 설정')}</span>
                </a>
                <a href="#" onclick="window.api.logout(); return false;" class="d-flex align-items-center menu-item px-3 py-2 text-danger">
                    <div class="icon-box bg-white text-danger p-2 me-3"><i class="bi bi-box-arrow-right"></i></div>
                    <span class="fw-bold">${window.getText('sidebar.menu.logout', '로그아웃')}</span>
                </a>
            </div>
        </div>
    `;

    // Inject sidebar into element with id 'sidebar-container'
    const container = document.getElementById('sidebar-container');
    if (container) {
        container.innerHTML = sidebarHtml;
    }
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
