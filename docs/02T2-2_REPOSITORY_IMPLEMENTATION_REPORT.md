# T2-2. Repository 구현 보고서

**작성일**: 2026-03-03  
**작업 내용**: 도메인별 Repository 구현 및 데이터 접근 제어 패턴 적용

---

## 1. 개요

ERD 기반 Tortoise 모델에 대응하는 Repository 레이어를 구현하였다.  
**T2-3 데이터 접근 제어 패턴**을 반영하여, 사용자 데이터 조회 시 `user_id` 스코프를 필수로 적용하였다.

---

## 2. 구현된 Repository 목록

| Repository | 파일 경로 | user_id 스코프 | 비고 |
|------------|-----------|----------------|------|
| DiseaseRepository | `app/repositories/disease_repository.py` | ❌ | 마스터 데이터 (질병/가이드라인) |
| PrescriptionRepository | `app/repositories/prescription_repository.py` | ✅ | 처방전, 메모 |
| MedicationIntakeRepository | `app/repositories/medication_intake_repository.py` | ✅ | 복용 기록 |
| ChatbotRepository | `app/repositories/chatbot_repository.py` | ✅ | 챗봇 세션, 메시지, 요약 |
| RecommendationRepository | `app/repositories/recommendation_repository.py` | ✅ | 추천 배치, 개별 추천, 피드백 |
| VectorDocumentRepository | `app/repositories/vector_document_repository.py` | ⚠️ | reference 기반 (서비스에서 user 검증) |

---

## 3. Repository별 상세

### 3.1 DiseaseRepository

- **역할**: 질병 마스터, 질병별 가이드라인 조회
- **user_id 스코프**: 불필요 (공통 마스터 데이터)
- **주요 메서드**:
  - `get_by_id(disease_id)` - 질병 단건 조회
  - `list_all()` - 전체 질병 목록
  - `get_with_guidelines(disease_id)` - 질병 + 가이드라인 prefetch
  - `get_guidelines_by_disease(disease_id)` - 가이드라인 목록

### 3.2 PrescriptionRepository

- **역할**: 처방전 CRUD, 처방전 메모
- **user_id 스코프**: 모든 조회/생성에 `user_id` 필수
- **주요 메서드**:
  - `get_by_id_for_user(user_id, prescription_id)` - user 소유 처방전만 조회
  - `list_by_user(user_id, limit, offset)` - 사용자별 처방전 목록
  - `list_by_date_range(user_id, from_date, to_date)` - 기간별 조회
  - `create(...)` - 처방전 생성
  - `add_memo(user_id, prescription_id, ...)` - 메모 추가

### 3.3 MedicationIntakeRepository

- **역할**: 복용 기록(MedicationIntakeLog) CRUD
- **user_id 스코프**: `prescription__user_id`로 검증
- **주요 메서드**:
  - `get_by_id_for_user(user_id, log_id)` - user 소유 복용 기록만 조회
  - `list_by_user(user_id, limit, offset)` - 사용자별 복용 기록
  - `list_by_date_range(user_id, from_dt, to_dt)` - 기간별 조회
  - `list_by_prescription_for_user(user_id, prescription_id)` - 처방전별 복용 기록
  - `create(user_id, prescription_id, ...)` - 복용 기록 생성 (prescription 소유 검증)

### 3.4 ChatbotRepository

- **역할**: 챗봇 세션, 메시지, 세션 요약
- **user_id 스코프**: 모든 메서드에 `user_id` 필수
- **주요 메서드**:
  - `get_session_for_user(user_id, session_id)` - user 소유 세션만 조회
  - `list_sessions_by_user(user_id, limit, offset)` - 세션 목록
  - `list_sessions_by_date_range(user_id, from_dt, to_dt)` - 기간별 세션
  - `create_session(user_id)` - 세션 생성
  - `end_session(user_id, session_id)` - 세션 종료
  - `add_message(user_id, session_id, sender, message)` - 메시지 추가
  - `add_summary(user_id, session_id, summary)` - 세션 요약 추가

### 3.5 RecommendationRepository

- **역할**: 추천 배치, 개별 추천, 활성 추천, 피드백
- **user_id 스코프**: 모든 메서드에 `user_id` 필수
- **주요 메서드**:
  - `get_recommendation_for_user(user_id, recommendation_id)` - user 소유 추천만 조회
  - `list_by_user(user_id, limit, offset)` - 추천 목록
  - `list_by_date_range(user_id, from_dt, to_dt)` - 기간별 조회
  - `list_active_for_user(user_id)` - 활성 추천 목록
  - `create_batch(user_id, ...)` - 추천 배치 생성
  - `create_recommendation(user_id, batch_id, ...)` - 개별 추천 생성 (batch 소유 검증)
  - `assign_active(user_id, recommendation_id)` - 활성 추천 할당
  - `add_feedback(user_id, recommendation_id, feedback_type)` - 피드백 추가

### 3.6 VectorDocumentRepository

- **역할**: 벡터 임베딩 문서 CRUD (RAG/검색용)
- **user_id 스코프**: `vector_documents` 테이블에 user_id 없음. `reference_type` + `reference_id`로 다형 참조. **서비스 레이어에서 user 소유 reference만 전달**하여 검증.
- **주요 메서드**:
  - `get_by_reference(reference_type, reference_id)` - reference로 단건 조회
  - `list_by_reference_type_and_ids(reference_type, reference_ids)` - ID 목록으로 조회 (reference_ids는 서비스에서 user 검증된 값)
  - `create(reference_type, reference_id, content, embedding)` - 문서 생성
  - `delete_by_reference(reference_type, reference_id)` - reference로 삭제

---

## 4. 데이터 접근 제어 패턴 (T2-3)

### 4.1 원칙

- **항상 user_id 스코프**: 사용자 데이터 조회 시 `user_id`를 필수 인자로 받음
- **다른 사용자 데이터 조회 불가**: `user_id=user_id`, `prescription__user_id=user_id` 등으로 필터링하여 구조적으로 차단
- **생성 시 소유 검증**: `create` 전에 prescription/session/batch 등이 해당 user 소유인지 확인

### 4.2 적용 예시

```python
# ✅ 올바른 사용: user_id 필수
prescriptions = await prescription_repo.list_by_user(user_id=current_user.id)
rx = await prescription_repo.get_by_id_for_user(user_id=current_user.id, prescription_id=5)

# ❌ 잘못된 사용: user_id 없이 prescription_id만으로 조회 불가
# get_by_id_for_user 없이 get_or_none(id=5)만 호출하면 다른 사용자 데이터 노출 위험
```

---

## 5. DoD 달성 여부

| DoD 항목 | 상태 |
|----------|------|
| 도메인별 repo: disease, prescription, medication, chatbot, recommendation, vector | ✅ 완료 |
| 서비스에서 사용할 핵심 메서드 제공 (`get_by_user`, `list_by_date_range` 등) | ✅ 완료 |
| 항상 user_id 스코프 메서드 제공 | ✅ 완료 |
| 다른 사용자 데이터 조회가 구조적으로 불가능 | ✅ 완료 |

---

## 6. 파일 구조

```
app/repositories/
├── __init__.py                    # Repository export
├── user_repository.py             # (기존)
├── user_credential_repository.py   # (기존)
├── disease_repository.py          # 신규
├── prescription_repository.py     # 신규
├── medication_intake_repository.py # 신규
├── chatbot_repository.py          # 신규
├── recommendation_repository.py   # 신규
└── vector_document_repository.py # 신규
```

---

## 7. 향후 작업

- 서비스 레이어에서 각 Repository 연동
- VectorDocument: pgvector 유사도 검색 구현 시 `list_by_reference_type_and_ids` 외 검색 메서드 추가 검토
