// js/chat-widget.js — Floating mini chatbot widget
(function () {
  if (document.getElementById('cw-root')) return;

  /* ── State ── */
  let state = 'MODE_SELECT'; // MODE_SELECT → SCAN_CHECK → CONFIRM_CONTEXT → CHATTING
  let mode = null;            // 'medication' | 'health'
  let userContext = null;
  let userId = null;

  /* ── Inject HTML ── */
  const root = document.createElement('div');
  root.id = 'cw-root';
  root.innerHTML = `
    <button id="cw-fab" aria-label="챗봇 열기">
      <i class="bi bi-robot"></i> MEDIMATE 챗봇
      <span class="cw-dot"></span>
    </button>
    <div id="cw-panel" class="cw-hidden">
      <div id="cw-header">
        <span><i class="bi bi-robot me-1"></i>MEDIMATE</span>
        <div>
          <button id="cw-fullscreen" title="전체 화면"><i class="bi bi-arrows-fullscreen"></i></button>
          <button id="cw-close" title="닫기"><i class="bi bi-x-lg"></i></button>
        </div>
      </div>
      <div id="cw-log"></div>
      <div id="cw-input-area">
        <input id="cw-input" type="text" placeholder="메시지를 입력하세요..." autocomplete="off"/>
        <button id="cw-send"><i class="bi bi-send"></i></button>
      </div>
    </div>`;
  document.body.appendChild(root);

  /* ── Refs ── */
  const fab = document.getElementById('cw-fab');
  const panel = document.getElementById('cw-panel');
  const log = document.getElementById('cw-log');
  const input = document.getElementById('cw-input');
  const sendBtn = document.getElementById('cw-send');

  /* ── Toggle ── */
  fab.onclick = () => { panel.classList.remove('cw-hidden'); fab.style.display = 'none'; if (!log.hasChildNodes()) boot(); };
  document.getElementById('cw-close').onclick = () => { panel.classList.add('cw-hidden'); fab.style.display = ''; };
  document.getElementById('cw-fullscreen').onclick = () => { window.location.href = 'chatbot.html'; };

  /* ── Message helpers ── */
  function botMsg(html) {
    const d = document.createElement('div');
    d.className = 'cw-msg cw-bot';
    d.innerHTML = html;
    log.appendChild(d);
    log.scrollTop = log.scrollHeight;
  }
  function userMsg(text) {
    const d = document.createElement('div');
    d.className = 'cw-msg cw-user';
    d.textContent = text;
    log.appendChild(d);
    log.scrollTop = log.scrollHeight;
  }
  function choiceButtons(choices) {
    const wrap = document.createElement('div');
    wrap.className = 'cw-choices';
    choices.forEach(c => {
      const b = document.createElement('button');
      b.textContent = c.label;
      b.onclick = () => { wrap.remove(); userMsg(c.label); c.action(); };
      wrap.appendChild(b);
    });
    log.appendChild(wrap);
    log.scrollTop = log.scrollHeight;
  }

  /* ── Boot ── */
  async function boot() {
    try {
      const user = await window.api.getUserMe();
      userId = user.id;
    } catch { userId = null; }

    state = 'MODE_SELECT';
    mode = null;
    userContext = null;
    botMsg('안녕하세요 😊 메디메이트입니다.<br>어떤 상담을 도와드릴까요?');
    choiceButtons([
      { label: '1. 복약 상담', action: () => selectMode('medication') },
      { label: '2. 건강 상담', action: () => selectMode('health') },
    ]);
  }

  /* ── Mode select ── */
  async function selectMode(m) {
    mode = m;
    state = 'SCAN_CHECK';
    botMsg(m === 'medication' ? '💊 복약 상담을 선택하셨습니다.' : '🏃 건강 상담을 선택하셨습니다.');
    botMsg('스캔된 진료 기록을 확인하고 있습니다...');

    try {
      if (!userId) throw new Error('no user');
      userContext = await window.api.getUserContext(userId);
    } catch { userContext = null; }

    const hasDiseases = userContext?.diseases?.length > 0;
    const hasMeds = userContext?.medications?.length > 0;
    const hasContext = hasDiseases || hasMeds;

    if (!hasContext) {
      botMsg('등록된 스캔 기록이 없습니다.<br>처방전/진단서를 먼저 등록하시겠어요?');
      choiceButtons([
        { label: '📄 스캔하러 가기', action: () => { window.location.href = 'scans.html'; } },
        { label: '스캔 없이 진행', action: () => startChatting() },
      ]);
    } else {
      showContextConfirm();
    }
  }

  /* ── Context confirm ── */
  function showContextConfirm() {
    state = 'CONFIRM_CONTEXT';
    const diseases = userContext.diseases?.map(d => d.name || d.kcd_code || '-').join(', ') || '없음';
    const meds = userContext.medications?.map(m => m.drug_name || '-').join(', ') || '없음';
    botMsg(`현재 등록된 정보입니다:<br><b>진단명:</b> ${escapeHtml(diseases)}<br><b>약품명:</b> ${escapeHtml(meds)}<br><br>이 정보가 맞으신가요?`);
    choiceButtons([
      { label: '✅ 맞습니다', action: () => startChatting() },
      { label: '✏️ 수정하러 가기', action: () => { window.location.href = 'scans.html'; } },
    ]);
  }

  /* ── Start chatting ── */
  function startChatting() {
    state = 'CHATTING';
    botMsg('좋습니다! 궁금한 점을 자유롭게 질문해 주세요 😊');
    input.focus();
  }

  /* ── Send ── */
  async function handleSend() {
    const q = input.value.trim();
    if (!q) return;
    input.value = '';

    if (state === 'MODE_SELECT') {
      if (q === '1' || q.includes('복약')) { userMsg(q); selectMode('medication'); return; }
      if (q === '2' || q.includes('건강')) { userMsg(q); selectMode('health'); return; }
      userMsg(q);
      botMsg('1 또는 2를 입력해 주세요.<br>1. 복약 상담 &nbsp; 2. 건강 상담');
      return;
    }

    if (state !== 'CHATTING') { userMsg(q); botMsg('위 버튼을 선택해 주세요.'); return; }

    userMsg(q);
    sendBtn.disabled = true;

    const diseaseCode = userContext?.diseases?.map(d => d.kcd_code || d.name).filter(Boolean).join(', ') || null;
    const medications = userContext?.medications?.map(m => m.drug_name).filter(Boolean) || [];

    try {
      const res = await window.api.sendChatMessage({
        patient_id: String(userId),
        mode: mode,
        user_question: q,
        disease_code: diseaseCode,
        medications: medications,
        use_context: true,
      });
      botMsg(renderMd(res.chat_answer || '답변을 받지 못했습니다.'));
    } catch (e) {
      botMsg('⚠️ 오류가 발생했습니다: ' + escapeHtml(e.message));
    } finally {
      sendBtn.disabled = false;
      input.focus();
    }
  }

  sendBtn.onclick = handleSend;
  input.onkeydown = e => { if (e.key === 'Enter') { e.preventDefault(); handleSend(); } };

  /* ── Markdown lite ── */
  function renderMd(t) {
    return escapeHtml(t)
      .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.+?)\*/g, '<em>$1</em>')
      .replace(/^- (.+)$/gm, '• $1')
      .replace(/\n/g, '<br>');
  }

  /* ── Hide on chatbot.html ── */
  if (window.location.pathname.endsWith('chatbot.html')) {
    root.style.display = 'none';
  }
})();
