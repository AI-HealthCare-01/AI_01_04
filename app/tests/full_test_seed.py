import asyncio
from datetime import date, datetime, timedelta
from typing import Any

from tortoise import Tortoise
from tortoise.connection import connections

# 서비스 및 모델 임포트
from app.db.databases import TORTOISE_ORM
from app.models.users import User, Gender
from app.models.prescriptions import Prescription
from app.repositories.scan_repository import ScanRepository
from app.services.scan_analysis import ScanAnalysisService

from app.models.diseases import Disease
from app.models.drugs import Drug
from app.models.scans import Scan
from app.models.recommendations import Recommendation

async def create_test_data():
    # 1. DB 연결 초기화
    await Tortoise.init(config=TORTOISE_ORM)
    
    scan_repo = ScanRepository()
    scan_service = ScanAnalysisService()

    print("🚀 현실적인 정밀 의료 데이터 생성을 시작합니다...")

    # 2. 가상 환자 4명 생성 (Gender Enum 적용)
    patients = [
        {"name": "김철수", "email": "chul@example.com", "birthday": date(1980, 5, 20), "gender": Gender.MALE},
        {"name": "이영희", "email": "young@example.com", "birthday": date(1992, 11, 15), "gender": Gender.FEMALE},
        {"name": "박민수", "email": "min@example.com", "birthday": date(1975, 2, 10), "gender": Gender.MALE},
        {"name": "최지우", "email": "jiu@example.com", "birthday": date(2000, 8, 5), "gender": Gender.FEMALE}
    ]
    
    user_objects = []
    for p in patients:
        user, _ = await User.get_or_create(
            email=p["email"],
            defaults={
                "name": p["name"],
                "phone_number": "01012345678",
                "birthday": p["birthday"],
                "gender": p["gender"],
                "is_active": True
            }
        )
        user_objects.append(user)
    print(f"✅ {len(user_objects)}명의 환자 기반 생성 완료")

    # 3. 처방전 이미지 기반 정밀 시나리오 (5개 세트)
    # 이미지의 '1회 투여량', '1일 투여횟수', '투약일수' 데이터를 반영
    mock_scans = [
        {
            "diag": "상세불명의 감염성 설사 및 장염", 
            "drugs": ["티알피정", "비오락토캅셀", "스멕타현탁액", "세토펜이알서방정"],
            "dose_amount": "1", "dose_count": 3, "duration": 3, # 이미지 기반 3일치
            "note": "자극적인 음식을 피하고 수분을 충분히 섭취하세요."
        },
        {
            "diag": "본태성 고혈압", 
            "drugs": ["노바스크정 5mg", "딜라트렌정 12.5mg"],
            "dose_amount": "1", "dose_count": 1, "duration": 30, # 장기 처방
            "note": "매일 아침 일정한 시간에 복용하세요."
        },
        {
            "diag": "급성 위염", 
            "drugs": ["알마겔정", "스티렌정"],
            "dose_amount": "1", "dose_count": 3, "duration": 7, 
            "note": "식후 30분에 복용하시고 술, 커피는 피하세요."
        },
        {
            "diag": "제2형 당뇨병", 
            "drugs": ["자누메트정 50/500mg"],
            "dose_amount": "1", "dose_count": 2, "duration": 60, # 장기 처방
            "note": "식사 직후 복용하시고 저혈당 증상에 주의하세요."
        },
        {
            "diag": "급성 인후염", 
            "drugs": ["코대원포르테시럽", "모니플루정"],
            "dose_amount": "1", "dose_count": 3, "duration": 5,
            "note": "따뜻한 물을 자주 마시고 목을 보호하세요."
        }
    ]

    for user in user_objects:
        print(f"📦 {user.name} 환자의 정밀 처방 이력 생성 중...")
        for i, m in enumerate(mock_scans):
            # 날짜 계산: 오늘을 기준으로 과거로 분산 배치
            start_date = date.today() - timedelta(days=i*15) 
            end_date = start_date + timedelta(days=m["duration"])
            
            try:
                # [단계 1] Scan 레코드 생성
                scan_data = await scan_repo.create(
                    user_id=user.id,
                    file_path=f"/artifacts/scan_{user.id}_{i}.jpg",
                    document_type="prescription"
                )
                scan_id = scan_data["scan_id"]

                # [단계 2] 분석 데이터 업데이트
                await scan_repo.update(
                    user_id=user.id, 
                    scan_id=scan_id,
                    status="done",
                    document_date=start_date.isoformat(),
                    diagnosis=m["diag"],
                    clinical_note=m["note"],
                    drugs=m["drugs"],
                    analyzed_at=datetime.now().isoformat()
                )

                # [단계 3] 통합 저장 서비스 호출 (내부 로직 수행)
                await scan_service.save_result(user=user, scan_id=scan_id)

                # [단계 4] Prescription 상세 컬럼 보정 (정밀 데이터 주입)
                # save_result가 생성한 가장 최근 처방전을 찾아 기간과 횟수 수정
                latest_p = await Prescription.filter(user_id=user.id).order_by("-id").first()
                if latest_p:
                    latest_p.start_date = start_date
                    latest_p.end_date = end_date
                    latest_p.dose_count = m["dose_count"]
                    latest_p.dose_amount = m["dose_amount"]
                    latest_p.dose_unit = "정" if "시럽" not in str(m["drugs"]) else "포"
                    await latest_p.save()

                print(f"   - [{start_date} ~ {end_date}] {m['diag']} ({m['duration']}일분) 저장 성공")
                
            except Exception as e:
                print(f"   - [{start_date}] 처리 중 오류 발생: {e}")

    print("\n✨ 모든 정밀 테스트 데이터 생성 완료!")
    await Tortoise.close_connections()

async def reset_database():
    """기존 데이터 삭제 (테이블 구조는 유지)"""
    print("🧹 데이터베이스 초기화를 시작합니다...")
    conn = connections.get("default")
    
    # 외래키 제약 조건을 잠시 끄고 모든 테이블 데이터 삭제 (Truncate)
    # 테이블 순서는 상관없도록 CASCADE 혹은 제약조건 해제 방식을 사용합니다.
    tables = [
        "recommendations", "prescriptions", "scans", 
        "diseases", "drugs", "users", "chatbot_messages", "chatbot_sessions"
    ]
    
    for table in tables:
        try:
            await conn.execute_query(f'TRUNCATE TABLE "{table}" CASCADE;')
            print(f"   - {table} 테이블 비우기 완료")
        except Exception as e:
            print(f"   - {table} 삭제 중 건너뜀 (존재하지 않거나 에러): {e}")


async def main():
    await Tortoise.init(config=TORTOISE_ORM)
    try:
        await reset_database()
        await create_test_data()
    finally:
        await Tortoise.close_connections()

if __name__ == "__main__":
    asyncio.run(main())
