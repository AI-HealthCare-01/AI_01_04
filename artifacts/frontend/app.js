(function () {
  "use strict";

  const qs = (id) => document.getElementById(id);
  const logPanel = qs("logPanel");

  const state = {
    baseUrl: localStorage.getItem("frontend_base_url") || "http://localhost:8000/api/v1",
    accessToken: localStorage.getItem("frontend_access_token") || "",
  };

  function now() {
    return new Date().toLocaleTimeString("ko-KR", { hour12: false });
  }

  function log(title, payload) {
    const line = `[${now()}] ${title}\n${payload ? JSON.stringify(payload, null, 2) : ""}\n`;
    logPanel.textContent = `${line}\n${logPanel.textContent}`.trim();
  }

  function authHeaders() {
    const headers = {};
    if (state.accessToken) headers.Authorization = `Bearer ${state.accessToken}`;
    return headers;
  }

  function endpoint(path) {
    return `${state.baseUrl}${path}`;
  }

  async function request(path, options) {
    const url = endpoint(path);
    const init = options || {};
    const headers = Object.assign({}, authHeaders(), init.headers || {});
    log(`요청 ${init.method || "GET"} ${url}`, { headers, body: init.body || null });
    const resp = await fetch(url, {
      credentials: "include",
      ...init,
      headers,
    });
    const text = await resp.text();
    let body = text;
    try {
      body = text ? JSON.parse(text) : null;
    } catch (err) {
      body = { raw: text };
    }
    log(`응답 ${resp.status} ${url}`, body);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    return body;
  }

  function jsonRequest(path, method, payload) {
    return request(path, {
      method,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  }

  function read(id) {
    return qs(id).value.trim();
  }

  function parseCsv(v) {
    if (!v) return [];
    return v.split(",").map((x) => x.trim()).filter(Boolean);
  }

  function safeInt(id) {
    const v = Number(read(id));
    return Number.isFinite(v) && v > 0 ? v : null;
  }

  function applyConfig() {
    qs("baseUrl").value = state.baseUrl;
    qs("accessToken").value = state.accessToken;
  }

  function bindBasics() {
    qs("saveConfigBtn").addEventListener("click", () => {
      state.baseUrl = read("baseUrl") || state.baseUrl;
      state.accessToken = read("accessToken");
      localStorage.setItem("frontend_base_url", state.baseUrl);
      localStorage.setItem("frontend_access_token", state.accessToken);
      log("설정 저장", { baseUrl: state.baseUrl, hasToken: Boolean(state.accessToken) });
    });

    qs("clearTokenBtn").addEventListener("click", () => {
      state.accessToken = "";
      qs("accessToken").value = "";
      localStorage.removeItem("frontend_access_token");
      log("토큰 삭제", null);
    });

    qs("clearLogBtn").addEventListener("click", () => {
      logPanel.textContent = "";
    });
  }

  function bindAuth() {
    qs("signupBtn").addEventListener("click", async () => {
      try {
        const payload = {
          email: read("signupEmail"),
          password: read("signupPassword"),
          name: read("signupName"),
          gender: read("signupGender"),
          birthday: read("signupBirthday"),
          phone_number: read("signupPhone"),
        };
        await jsonRequest("/auth/signup", "POST", payload);
      } catch (err) {
        log("회원가입 실패", { message: err.message });
      }
    });

    qs("loginBtn").addEventListener("click", async () => {
      try {
        const payload = {
          email: read("loginEmail"),
          password: read("loginPassword"),
        };
        const data = await jsonRequest("/auth/login", "POST", payload);
        if (data && data.access_token) {
          state.accessToken = data.access_token;
          qs("accessToken").value = data.access_token;
          localStorage.setItem("frontend_access_token", data.access_token);
          log("로그인 성공", { access_token_saved: true });
        }
      } catch (err) {
        log("로그인 실패", { message: err.message });
      }
    });

    qs("refreshBtn").addEventListener("click", async () => {
      try {
        const data = await request("/auth/token/refresh", { method: "GET" });
        if (data && data.access_token) {
          state.accessToken = data.access_token;
          qs("accessToken").value = data.access_token;
          localStorage.setItem("frontend_access_token", data.access_token);
        }
      } catch (err) {
        log("토큰 갱신 실패", { message: err.message });
      }
    });
  }

  function bindUser() {
    qs("meBtn").addEventListener("click", async () => {
      try {
        const me = await request("/users/me", { method: "GET" });
        qs("meName").value = me.name || "";
        qs("meEmail").value = me.email || "";
        qs("mePhone").value = me.phone_number || "";
        qs("meBirthday").value = me.birthday || "";
        qs("meGender").value = me.gender || "";
        qs("meProfileUrl").value = me.profile_image_url || "";
      } catch (err) {
        log("내 정보 조회 실패", { message: err.message });
      }
    });

    qs("mePatchBtn").addEventListener("click", async () => {
      try {
        const payload = {};
        const name = read("meName");
        const email = read("meEmail");
        const phone = read("mePhone");
        const birthday = read("meBirthday");
        const gender = read("meGender");
        const profile = read("meProfileUrl");
        if (name) payload.name = name;
        if (email) payload.email = email;
        if (phone) payload.phone_number = phone;
        if (birthday) payload.birthday = birthday;
        if (gender) payload.gender = gender;
        if (profile) payload.profile_image_url = profile;
        await jsonRequest("/users/me", "PATCH", payload);
      } catch (err) {
        log("내 정보 수정 실패", { message: err.message });
      }
    });
  }

  function bindDashboard() {
    qs("dashboardBtn").addEventListener("click", async () => {
      try {
        await request("/dashboard/summary", { method: "GET" });
      } catch (err) {
        log("대시보드 조회 실패", { message: err.message });
      }
    });
  }

  function bindScan() {
    qs("scanUploadBtn").addEventListener("click", async () => {
      try {
        const fileInput = qs("scanFile");
        const file = fileInput.files && fileInput.files[0];
        if (!file) {
          log("업로드 실패", { reason: "파일을 선택하세요." });
          return;
        }
        const fd = new FormData();
        fd.append("file", file);
        const data = await request("/scans/upload", { method: "POST", body: fd });
        if (data && data.scan_id) qs("scanId").value = String(data.scan_id);
      } catch (err) {
        log("스캔 업로드 실패", { message: err.message });
      }
    });

    qs("scanAnalyzeBtn").addEventListener("click", async () => {
      const scanId = safeInt("scanId");
      if (!scanId) return log("입력 오류", { field: "scan_id" });
      try {
        await request(`/scans/${scanId}/analyze`, { method: "POST" });
      } catch (err) {
        log("스캔 분석 실패", { message: err.message });
      }
    });

    qs("scanGetBtn").addEventListener("click", async () => {
      const scanId = safeInt("scanId");
      if (!scanId) return log("입력 오류", { field: "scan_id" });
      try {
        const data = await request(`/scans/${scanId}`, { method: "GET" });
        qs("scanDocDate").value = data.document_date || "";
        qs("scanDiagnosis").value = data.diagnosis || "";
        qs("scanDrugs").value = Array.isArray(data.drugs) ? data.drugs.join(",") : "";
      } catch (err) {
        log("스캔 결과 조회 실패", { message: err.message });
      }
    });

    qs("scanPatchBtn").addEventListener("click", async () => {
      const scanId = safeInt("scanId");
      if (!scanId) return log("입력 오류", { field: "scan_id" });
      try {
        const payload = {
          document_date: read("scanDocDate") || null,
          diagnosis: read("scanDiagnosis") || null,
          drugs: parseCsv(read("scanDrugs")),
        };
        await jsonRequest(`/scans/${scanId}/result`, "PATCH", payload);
      } catch (err) {
        log("스캔 결과 수정 실패", { message: err.message });
      }
    });

    qs("scanSaveBtn").addEventListener("click", async () => {
      const scanId = safeInt("scanId");
      if (!scanId) return log("입력 오류", { field: "scan_id" });
      try {
        const data = await request(`/scans/${scanId}/save`, { method: "POST" });
        qs("scanCreatedCount").value = String(data.created_count ?? "");
        qs("scanSkippedCount").value = String(data.skipped_count ?? "");
        qs("scanSkippedDupes").value = Array.isArray(data.skipped_duplicates)
          ? data.skipped_duplicates.join(", ")
          : "";
      } catch (err) {
        log("스캔 결과 저장 실패", { message: err.message });
      }
    });
  }

  function bindMedication() {
    qs("medHistoryBtn").addEventListener("click", async () => {
      try {
        const from = read("medFrom");
        const to = read("medTo");
        const q = new URLSearchParams();
        if (from) q.set("from", from);
        if (to) q.set("to", to);
        const suffix = q.toString() ? `?${q.toString()}` : "";
        await request(`/medications/history${suffix}`, { method: "GET" });
      } catch (err) {
        log("복약 히스토리 실패", { message: err.message });
      }
    });

    qs("medDayBtn").addEventListener("click", async () => {
      try {
        const date = read("medDate");
        if (!date) return log("입력 오류", { field: "date" });
        await request(`/medications/history/${date}`, { method: "GET" });
      } catch (err) {
        log("복약 일자 상세 실패", { message: err.message });
      }
    });

    qs("medPatchBtn").addEventListener("click", async () => {
      try {
        const logId = safeInt("medLogId");
        if (!logId) return log("입력 오류", { field: "log_id" });
        const payload = { status: read("medStatus") };
        await jsonRequest(`/medications/logs/${logId}`, "PATCH", payload);
      } catch (err) {
        log("복약 로그 수정 실패", { message: err.message });
      }
    });
  }

  function bindHealth() {
    qs("healthHistoryBtn").addEventListener("click", async () => {
      try {
        const from = read("healthFrom");
        const to = read("healthTo");
        const q = new URLSearchParams();
        if (from) q.set("from", from);
        if (to) q.set("to", to);
        const suffix = q.toString() ? `?${q.toString()}` : "";
        await request(`/health/history${suffix}`, { method: "GET" });
      } catch (err) {
        log("건강 히스토리 실패", { message: err.message });
      }
    });

    qs("healthDayBtn").addEventListener("click", async () => {
      try {
        const date = read("healthDate");
        if (!date) return log("입력 오류", { field: "date" });
        await request(`/health/history/${date}`, { method: "GET" });
      } catch (err) {
        log("건강 일자 상세 실패", { message: err.message });
      }
    });

    qs("healthPatchBtn").addEventListener("click", async () => {
      try {
        const logId = safeInt("healthLogId");
        if (!logId) return log("입력 오류", { field: "log_id" });
        const payload = { status: read("healthStatus") };
        await jsonRequest(`/health/logs/${logId}`, "PATCH", payload);
      } catch (err) {
        log("건강 로그 수정 실패", { message: err.message });
      }
    });
  }

  function bindRecommendations() {
    qs("recListBtn").addEventListener("click", async () => {
      try {
        const scanId = safeInt("recScanId");
        if (!scanId) return log("입력 오류", { field: "scan_id" });
        await request(`/recommendations/scans/${scanId}`, { method: "GET" });
      } catch (err) {
        log("추천 조회 실패", { message: err.message });
      }
    });

    qs("recSaveBtn").addEventListener("click", async () => {
      try {
        const scanId = safeInt("recScanId");
        if (!scanId) return log("입력 오류", { field: "scan_id" });
        await request(`/recommendations/scans/${scanId}/save`, { method: "POST" });
      } catch (err) {
        log("추천 저장 실패", { message: err.message });
      }
    });

    qs("recPatchBtn").addEventListener("click", async () => {
      try {
        const recId = safeInt("recId");
        if (!recId) return log("입력 오류", { field: "recommendation_id" });
        const payload = {};
        const content = read("recContent");
        const selected = read("recSelected");
        if (content) payload.content = content;
        if (selected) payload.is_selected = selected === "true";
        await jsonRequest(`/recommendations/${recId}`, "PATCH", payload);
      } catch (err) {
        log("추천 수정 실패", { message: err.message });
      }
    });

    qs("recDeleteBtn").addEventListener("click", async () => {
      try {
        const recId = safeInt("recId");
        if (!recId) return log("입력 오류", { field: "recommendation_id" });
        await request(`/recommendations/${recId}`, { method: "DELETE" });
      } catch (err) {
        log("추천 삭제 실패", { message: err.message });
      }
    });
  }

  applyConfig();
  bindBasics();
  bindAuth();
  bindUser();
  bindDashboard();
  bindScan();
  bindMedication();
  bindHealth();
  bindRecommendations();
  log("프론트 초기화 완료", { baseUrl: state.baseUrl });
})();
