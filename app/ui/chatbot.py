from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()


@router.get("/chatbot", response_class=HTMLResponse)
def index():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>AI 메디컬 파트너</title>
        <meta charset="utf-8">
        <style>
            :root { --primary: #2e7d32; --secondary: #0288d1; --bg: #f4f7f6; --danger: #d32f2f; }
            body { font-family: 'Pretendard', sans-serif; margin: 0; background: var(--bg); display: flex; flex-direction: column; height: 100vh; overflow: hidden; }
            .header { padding: 15px; text-align: center; background: white; border-bottom: 1px solid #eee; flex-shrink: 0; }
            .header h2 { margin: 0; color: var(--primary); }
            .chat-container { flex: 1; max-width: 700px; margin: 10px auto; width: 95%; display: flex; flex-direction: column; background: white; border-radius: 15px; box-shadow: 0 5px 15px rgba(0,0,0,0.05); overflow: hidden; }
            .chat-window { flex: 1; padding: 20px; overflow-y: auto; display: flex; flex-direction: column; gap: 12px; scroll-behavior: smooth; }
            .msg { padding: 12px 16px; border-radius: 15px; max-width: 85%; font-size: 14px; line-height: 1.5; }
            .ai { background: #f1f3f4; align-self: flex-start; border-bottom-left-radius: 2px; white-space: pre-wrap; }
            .user { background: var(--primary); color: white; align-self: flex-end; border-bottom-right-radius: 2px; }
            .input-area { padding: 15px; border-top: 1px solid #eee; display: flex; gap: 10px; background: white; }
            input { flex: 1; padding: 12px; border: 1px solid #ddd; border-radius: 8px; outline: none; }
            .send-btn { padding: 10px 20px; background: var(--primary); color: white; border: none; border-radius: 8px; cursor: pointer; font-weight: bold; }
            .action-btn { border: 1px solid #ddd; background: white; padding: 8px 14px; border-radius: 20px; cursor: pointer; font-size: 12px; transition: 0.2s; margin: 3px; }
            .action-btn:hover { background: #f0f0f0; border-color: #bbb; }
            .action-btn.danger { border-color: var(--danger); color: var(--danger); }
            .action-btn.danger:hover { background: #fce4ec; }
            .action-btn.primary { border-color: var(--primary); color: var(--primary); }
            .action-btn.primary:hover { background: #e8f5e9; }
            .retry-btn { border: 1px solid #ddd; background: white; padding: 8px 12px; border-radius: 20px; cursor: pointer; font-size: 12px; display: inline-flex; align-items: center; gap: 5px; transition: 0.2s; margin-top: 5px; }
            .retry-btn:hover { background: #f0f0f0; border-color: #bbb; }
            .tag { font-size: 10px; padding: 2px 6px; border-radius: 10px; color: white; margin-right: 5px; }
            .modal { display: none; position: fixed; z-index: 2000; left: 0; top: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); align-items: center; justify-content: center; }
            .modal-content { background: white; padding: 25px; border-radius: 15px; width: 90%; max-width: 500px; position: relative; }
            .close { position: absolute; top: 15px; right: 20px; font-size: 24px; cursor: pointer; }
            .log-panel { height: 60px; background: #222; color: #0f0; font-family: monospace; font-size: 11px; padding: 10px; overflow-y: auto; flex-shrink: 0; }
            .med-item { display: flex; justify-content: space-between; align-items: center; padding: 6px 0; border-bottom: 1px solid #eee; }
        </style>
    </head>
    <body>
        <div class="header">
            <h2>💊 AI 메디컬 파트너</h2>
            <p style="font-size:12px; color:#888;">사용자 맞춤형 복약지도 & 건강상담</p>
        </div>

        <div class="chat-container">
            <div id="chat-window" class="chat-window"></div>
            <div class="input-area">
                <input type="text" id="user-input" placeholder="메시지 또는 번호를 입력하세요..." onkeypress="if(event.keyCode==13) handleInput()">
                <button class="send-btn" onclick="handleInput()">전송</button>
            </div>
        </div>

        <div id="log-panel" class="log-panel"></div>

        <div id="modal-report" class="modal"><div class="modal-content"><span class="close" onclick="closeModal()">×</span>
            <h3 id="pop-title">📋 리포트</h3><div id="report-text" style="white-space:pre-wrap; font-size:14px; max-height:450px; overflow-y:auto; line-height:1.6;"></div></div></div>

        <script>
            // ── 상태 관리 ──
            let step = 'MENU';
            let userData = { patient_id: '1', disease_code: '', medications: [], user_question: '' };
            let userContext = null;
            let reportCache = {};
            const win = document.getElementById('chat-window');
            const input = document.getElementById('user-input');

            window.onload = () => {
                addMsg("안녕하세요! 원하시는 서비스 번호를 입력해주세요.\\n\\n1. 💊 <b>복약 지도</b>\\n2. 🌿 <b>건강 상담</b>", "ai");
                addLog("시스템 가동: 메뉴 대기 중");
            };

            function addLog(msg) {
                const div = document.createElement('div');
                div.innerText = `[${new Date().toLocaleTimeString()}] ${msg}`;
                document.getElementById('log-panel').appendChild(div);
                document.getElementById('log-panel').scrollTop = 9999;
            }

            function addMsg(text, type) {
                const d = document.createElement('div');
                d.className = `msg ${type}`;
                d.innerHTML = text;
                win.appendChild(d);
                win.scrollTop = win.scrollHeight;
            }

            function addButtons(buttons) {
                const div = document.createElement('div');
                div.style.cssText = 'display:flex; flex-wrap:wrap; gap:4px; margin:4px 0;';
                buttons.forEach(b => {
                    const btn = document.createElement('button');
                    btn.className = `action-btn ${b.cls || ''}`;
                    btn.innerHTML = b.label;
                    btn.onclick = b.action;
                    div.appendChild(btn);
                });
                win.appendChild(div);
                win.scrollTop = win.scrollHeight;
            }

            function closeModal() { document.getElementById('modal-report').style.display = 'none'; }

            // ── API 호출 ──
            async function fetchContext(userId) {
                const res = await fetch(`/api/v1/chatbot/context/${userId}`);
                return await res.json();
            }

            async function deactivateMed(prescriptionId) {
                const res = await fetch('/api/v1/chatbot/deactivate', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ prescription_id: prescriptionId })
                });
                return await res.json();
            }

            // ── 복약지도 플로우 ──
            async function startMediFlow() {
                addMsg("📋 사용자 정보를 확인합니다...", "ai");
                addLog("복약지도: 사용자 컨텍스트 조회 중");

                try {
                    userContext = await fetchContext(userData.patient_id);
                } catch(e) {
                    addMsg("⚠️ 사용자 정보 조회에 실패했습니다. 수동 입력 모드로 전환합니다.", "ai");
                    step = 'MEDI_MANUAL_DISEASE';
                    addMsg("<b>질병명</b>을 입력해주세요.", "ai");
                    return;
                }

                // 질병 정보 확인
                if (!userContext.has_diseases) {
                    addMsg("등록된 질병 정보가 없습니다.", "ai");
                    if (userContext.has_scans && userContext.scan_summary.pending_count > 0) {
                        addMsg("⏳ 처리 중인 스캔이 있습니다. 스캔 완료 후 자동으로 질병이 등록됩니다.", "ai");
                    }
                    addMsg("질병명을 직접 입력하시거나, 스캔 기능을 이용해주세요.", "ai");
                    addButtons([
                        { label: '✏️ 질병명 직접 입력', cls: 'primary', action: () => { step = 'MEDI_MANUAL_DISEASE'; addMsg("질병명을 입력해주세요.", "ai"); }},
                        { label: '📷 스캔하러 가기', action: () => { window.location.href = '/scans.html'; }},
                        { label: '🏠 메뉴로', action: goMenu }
                    ]);
                    return;
                }

                // 질병 정보 표시
                let diseaseList = userContext.diseases.map((d, i) => `  ${i+1}. ${d.name}${d.kcd_code ? ' ('+d.kcd_code+')' : ''}`).join('\\n');
                addMsg(`✅ 등록된 질병:\\n${diseaseList}`, "ai");

                // 약품 조회
                showMedications();
            }

            function showMedications() {
                if (!userContext.has_medications) {
                    addMsg("현재 등록된 복용 약품이 없습니다.", "ai");
                    addButtons([
                        { label: '✏️ 약품 직접 입력', cls: 'primary', action: () => { step = 'MEDI_MANUAL_MEDS'; addMsg("복용 중인 약품을 쉼표로 구분하여 입력해주세요.", "ai"); }},
                        { label: '🏠 메뉴로', action: goMenu }
                    ]);
                    return;
                }

                addMsg("💊 약품 내역을 조회 중입니다...", "ai");
                let medList = userContext.medications.map((m, i) =>
                    `  ${i+1}. ${m.drug_name}${m.dose_count ? ' (1일 '+m.dose_count+'회)' : ''}`
                ).join('\\n');
                addMsg(`현재 복용 중인 약품:\\n${medList}`, "ai");

                step = 'MEDI_CONFIRM';
                addMsg("복용 종료된 약이 있으면 비활성화할 수 있습니다.", "ai");
                addButtons([
                    { label: '✅ 이상 없음 - 복약 안내 시작', cls: 'primary', action: confirmAndGenerate },
                    { label: '🗑️ 약품 비활성화', cls: 'danger', action: showDeactivateOptions },
                    { label: '🏠 메뉴로', action: goMenu }
                ]);
            }

            function showDeactivateOptions() {
                if (!userContext || !userContext.medications.length) return;
                addMsg("비활성화할 약품 번호를 선택하세요:", "ai");
                let btns = userContext.medications.map((m, i) => ({
                    label: `${i+1}. ${m.drug_name}`,
                    cls: 'danger',
                    action: () => confirmDeactivate(m.prescription_id, m.drug_name)
                }));
                btns.push({ label: '↩️ 취소', action: showMedications });
                addButtons(btns);
            }

            async function confirmDeactivate(prescriptionId, drugName) {
                addMsg(`"${drugName}"을(를) 정말 비활성화하시겠습니까?`, "ai");
                addButtons([
                    { label: '✅ 확인', cls: 'danger', action: async () => {
                        const result = await deactivateMed(prescriptionId);
                        addMsg(result.message, "ai");
                        if (result.success) {
                            userContext = await fetchContext(userData.patient_id);
                            showMedications();
                        }
                    }},
                    { label: '↩️ 취소', action: showMedications }
                ]);
            }

            async function confirmAndGenerate() {
                addMsg("이상 없으시면 복약 안내를 드리겠습니다. 잠시만 기다려주세요...", "ai");
                addLog("복약지도: AI 분석 시작");

                // 컨텍스트에서 자동 추출
                if (userContext.diseases.length > 0) {
                    userData.disease_code = userContext.diseases[0].kcd_code || userContext.diseases[0].name;
                }
                if (userContext.medications.length > 0) {
                    userData.medications = userContext.medications.map(m => m.drug_name);
                }

                await runAnalysis('medication');
            }

            // ── 건강상담 플로우 ──
            async function startHealthFlow() {
                addMsg("🌿 건강 상담을 시작합니다.", "ai");
                addLog("건강상담: 사용자 컨텍스트 조회 중");

                try {
                    userContext = await fetchContext(userData.patient_id);
                    if (userContext.has_diseases || userContext.has_medications) {
                        let info = "📋 참고할 사용자 정보:";
                        if (userContext.has_diseases) {
                            info += "\\n  질병: " + userContext.diseases.map(d => d.name).join(', ');
                        }
                        if (userContext.has_medications) {
                            info += "\\n  복용약: " + userContext.medications.map(m => m.drug_name).join(', ');
                        }
                        addMsg(info, "ai");
                    }
                } catch(e) {
                    addLog("건강상담: 컨텍스트 조회 실패 (일반 모드)");
                }

                step = 'HEALTH_CHAT';
                addMsg("궁금하신 건강 관련 질문을 입력해주세요.", "ai");
            }

            // ── 공통 ──
            function goMenu() {
                step = 'MENU';
                userContext = null;
                addMsg("\\n원하시는 서비스 번호를 입력해주세요.\\n\\n1. 💊 <b>복약 지도</b>\\n2. 🌿 <b>건강 상담</b>", "ai");
            }

            async function handleInput() {
                const val = input.value.trim();
                if(!val) return;
                addMsg(val, 'user');
                input.value = '';

                if (val === '1' || val === '2') step = 'MENU';

                if (step === 'MENU') {
                    if (val === '1') { startMediFlow(); }
                    else if (val === '2') { startHealthFlow(); }
                    else { addMsg("1번 또는 2번을 입력해주세요.", "ai"); }
                } else if (step === 'MEDI_MANUAL_DISEASE') {
                    userData.disease_code = val;
                    step = 'MEDI_MANUAL_MEDS';
                    addMsg("처방받으신 <b>약 목록</b>을 쉼표로 구분하여 입력해주세요.", "ai");
                } else if (step === 'MEDI_MANUAL_MEDS') {
                    userData.medications = val.split(',').map(m => m.trim());
                    addMsg("분석 리포트를 생성 중입니다...", "ai");
                    await runAnalysis('medication');
                } else if (step === 'HEALTH_CHAT') {
                    userData.user_question = val;
                    addMsg("답변을 생성 중입니다...", "ai");
                    await runAnalysis('health');
                }
            }

            async function runAnalysis(currentMode) {
                const reportId = 'report_' + Date.now();
                const res = await fetch('/api/v1/chatbot/chat', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({...userData, mode: currentMode, use_context: true})
                });
                const data = await res.json();

                const title = currentMode === 'medication' ? '복약지도' : '건강상담';
                const tagColor = currentMode === 'medication' ? '#2e7d32' : '#0288d1';
                reportCache[reportId] = { title, content: data.chat_answer, tag: userData.disease_code || '상담' };

                showPopup(reportId);

                const btnDiv = document.createElement('div');
                btnDiv.innerHTML = `<button class="retry-btn" onclick="showPopup('${reportId}')">
                    <span class="tag" style="background:${tagColor}">${title}</span>
                    <span>#${userData.disease_code || '상담'} 결과 다시보기</span>
                </button>`;
                win.appendChild(btnDiv);
                win.scrollTop = win.scrollHeight;

                addMsg(`🏥 ${title} 분석이 완료되었습니다.`, "ai");

                if (currentMode === 'medication') {
                    goMenu();
                } else {
                    addMsg("추가 질문이 있으시면 입력해주세요. 메뉴로 돌아가려면 1 또는 2를 입력하세요.", "ai");
                }
            }

            function showPopup(id) {
                const data = reportCache[id];
                document.getElementById('pop-title').innerText = `📋 ${data.title} 리포트 (#${data.tag})`;
                document.getElementById('report-text').innerText = data.content;
                document.getElementById('modal-report').style.display = 'flex';
            }
        </script>
    </body>
    </html>
    """
