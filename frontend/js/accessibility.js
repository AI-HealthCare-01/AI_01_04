// accessibility.js - 글자 크기 확대/축소 위젯
(function () {
    const STORAGE_KEY = 'a11y_font_scale';
    const SCALES = [100, 115, 130];
    const LABELS = ['기본', '크게', '매우 크게'];

    let currentIdx = SCALES.indexOf(parseInt(localStorage.getItem(STORAGE_KEY))) || 0;
    if (currentIdx < 0) currentIdx = 0;

    function applyScale() {
        document.documentElement.style.fontSize = SCALES[currentIdx] + '%';
        localStorage.setItem(STORAGE_KEY, SCALES[currentIdx]);
        if (btn) btn.textContent = '가 ' + LABELS[currentIdx];
    }

    var btn = document.createElement('button');
    btn.id = 'a11y-font-btn';
    btn.setAttribute('aria-label', '글자 크기 변경');
    btn.style.cssText =
        'position:fixed;left:16px;bottom:16px;z-index:1100;' +
        'background:#fff;border:1px solid #c5cec8;border-radius:999px;' +
        'padding:8px 16px;font-size:13px;font-weight:600;color:#2d3a33;' +
        'cursor:pointer;box-shadow:0 2px 8px rgba(0,0,0,.08);transition:all .15s;';
    btn.addEventListener('click', function () {
        currentIdx = (currentIdx + 1) % SCALES.length;
        applyScale();
    });

    document.addEventListener('DOMContentLoaded', function () {
        document.body.appendChild(btn);
        applyScale();
    });
})();
