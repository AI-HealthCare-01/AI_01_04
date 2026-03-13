from app.models.chat_health import HealthChat
from app.models.chat_medication import MediChat
from app.models.users import User

_health_cache = {}
_medi_cache = {}


class ChatBaseService:
    async def check_user_exists(self, patient_id: str) -> bool:
        User.filter(id=patient_id).exists
        # exists = await MediChat.filter(patient_id=patient_id).exists
        return True

    # 복약 이력과 건강 상담 이력을 모두 가져와 통합 관리
    async def get_health_history(self, patient_id: str, force_refresh: bool = False):
        """
        건강 상담 이력 조회.
        캐시가 있으면 메모리에서 반환하고, 캐시가 없거나 force_refresh=True일 경우 DB 조회.
        """
        # 1. 캐시 확인
        # if patient_id in _health_cache and not force_refresh:
        #     print(f"⚡ [Cache Hit] {patient_id}의 건강 상담 데이터를 메모리에서 불러옵니다.")
        #     return _health_cache[patient_id]

        # 2. DB 조회
        print(f"🔍 [DB Lookup] {patient_id}의 건강 상담 데이터를 DB에서 새로 조회합니다.")
        health_history = await HealthChat.filter(patient_id=patient_id).all()

        # 3. 조회한 데이터를 캐시에 저장 (세션 유지 효과)
        serialized_history = []
        for h in health_history:
            serialized_history.append(
                {
                    "created_at": h.created_at,  # 이미 읽어온 값은 괜찮음
                    "user_question": h.user_question,
                    "advice": h.advice,
                }
            )
        _health_cache[patient_id] = serialized_history
        return serialized_history

    def clear_health_cache(self, patient_id: str):
        """특정 환자의 캐시를 삭제 (로그아웃이나 데이터 변경 시 사용)"""
        if patient_id in _health_cache:
            del _health_cache[patient_id]

    async def get_medi_history(self, patient_id: str, force_refresh: bool = False):
        """
        복약 이력 조회.
        캐시가 있으면 메모리에서 반환하고, 캐시가 없거나 force_refresh=True일 경우 DB 쿼리.
        """
        # 1. 캐시 확인
        # if patient_id in _medi_cache and not force_refresh:
        #     print(f"⚡ [Cache Hit] {patient_id}의 복약 이력 데이터를 메모리에서 불러옵니다.")
        #     return _medi_cache[patient_id]

        # 2. DB 조회
        print(f"🔍 [DB Lookup] {patient_id}의 복약 이력 데이터를 DB에서 새로 조회합니다.")
        medi_history = await MediChat.filter(patient_id=patient_id).all()
        print(f">>> medi_history: \n{medi_history} \n<<<")

        # 3. 조회한 데이터를 캐시에 저장 (세션 유지 효과)
        serialized_history = []
        for h in medi_history:
            serialized_history.append(
                {
                    "created_at": h.created_at,  # 이미 읽어온 값은 괜찮음
                    "medications": h.medications,
                    "disease_code": h.disease_code,
                }
            )

        _medi_cache[patient_id] = serialized_history
        return serialized_history

    def clear_medication_cache(self, patient_id: str):
        """특정 환자의 캐시를 삭제 (로그아웃이나 데이터 변경 시 사용)"""
        if patient_id in _medi_cache:
            del _medi_cache[patient_id]
