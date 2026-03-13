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
            :root { --primary: #2e7d32; --secondary: #0288d1; --bg: #f4f7f6; }
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
            
            /* 다시보기 버튼 스타일 */
            .retry-btn { border: 1px solid #ddd; background: white; padding: 8px 12px; border-radius: 20px; cursor: pointer; font-size: 12px; display: inline-flex; align-items: center; gap: 5px; transition: 0.2s; margin-top: 5px; }
            .retry-btn:hover { background: #f0f0f0; border-color: #bbb; }
            .tag { font-size: 10px; padding: 2px 6px; border-radius: 10px; color: white; margin-right: 5px; }

            .modal { display: none; position: fixed; z-index: 2000; left: 0; top: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); align-items: center; justify-content: center; }
            .modal-content { background: white; padding: 25px; border-radius: 15px; width: 90%; max-width: 500px; position: relative; }
            .close { position: absolute; top: 15px; right: 20px; font-size: 24px; cursor: pointer; }
            .log-panel { height: 80px; background: #222; color: #0f0; font-family: monospace; font-size: 11px; padding: 10px; overflow-y: auto; flex-shrink: 0; }
        </style>
    </head>
    <body>
        <div class="header">
            <h2>💊 AI 메디컬 파트너</h2>
            <p style="font-size:12px; color:#888;">환자 ID와 질병코드 기반 정밀 분석 리포트</p>
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
            let step = 'MENU';
            let userData = { patient_id: '1', disease_code: '', medications: [] };
            let reportCache = {}; // 상담별 데이터를 저장할 객체
            const win = document.getElementById('chat-window');
            const input = document.getElementById('user-input');

            window.onload = () => {
                addMsg("안녕하세요! 원하시는 서비스 번호를 입력해주세요.<br><br>1. 💊 <b>복약 지도</b><br>2. 🌿 <b>건강 상담</b>", "ai");
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

            function closeModal() { document.getElementById('modal-report').style.display = 'none'; }

            async function handleInput() {
                const val = input.value.trim();
                if(!val) return;
                addMsg(val, 'user');
                input.value = '';

                if (val === '1' || val === '2') { 
                    step = 'MENU'; 
                }

                if (step === 'MENU') {
                    if (val === '1') { 
                        step = 'CODE'; 
                        mode = 'medication'; 
                        addMsg("<b>복약 지도</b> 매뉴를 시작합니다. <b>질병명</b>를 입력해주세요.", "ai"); 
                    } else if (val === '2') { 
                        step = 'CHAT'; 
                        mode = 'health'; 
                        addMsg("<b>건강 상담</b> 매뉴를 시작합니다. <b>질문</b>을 입력해주세요.", "ai"); 
                    } else {
                        addMsg("1번 또는 2번을 입력해주세요.", "ai");
                    }
                } else if (step === 'CODE') {
                    userData.disease_code = val; 
                    step = 'MEDS';
                    addMsg("처방받으신 <b>약 목록</b>을 입력해주세요.", "ai");
                } else if (step === 'MEDS') {
                    userData.medications = val.split(',').map(m => m.trim());
                    addMsg("분석 리포트를 생성 중입니다...", "ai");
                    runAnalysis(mode);
                } else if (step === 'CHAT') {
                    userData.disease_code = ""; 
                    userData.medications = [];
                    userData.user_question = val; 
                    addMsg("분석 리포트를 생성 중입니다...", "ai");
                    runAnalysis(mode);
                }
            }

            async function runAnalysis(currentMode) {
                const reportId = 'report_' + Date.now(); // 고유 ID 생성
                const res = await fetch('/api/v1/chatbot/chat', { 
                    method: 'POST', 
                    headers: {'Content-Type': 'application/json'}, 
                    body: JSON.stringify({...userData, mode: currentMode}) 
                });
                const data = await res.json();
                
                // 데이터 캐싱
                const title = currentMode === 'medication' ? '복약지도' : '건강상담';
                const tagColor = currentMode === 'medication' ? '#2e7d32' : '#0288d1';
                reportCache[reportId] = { title: title, content: data.chat_answer, tag: userData.disease_code };

                // 팝업 표시
                showPopup(reportId);

                // 다시보기 버튼 추가
                const btnDiv = document.createElement('div');
                btnDiv.innerHTML = `<button class="retry-btn" onclick="showPopup('${reportId}')">
                    <span class="tag" style="background:${tagColor}">${title}</span>
                    <span>#${userData.disease_code} 결과 다시보기</span>
                </button>`;
                win.appendChild(btnDiv);
                win.scrollTop = win.scrollHeight;

                addMsg(`🏥 ${title} 분석이 완료되었습니다. 팝업을 닫으셔도 위 버튼으로 언제든 다시 보실 수 있습니다.`, "ai");

                step = currentMode === 'medication' ? 'MENU' : 'CHAT';
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
