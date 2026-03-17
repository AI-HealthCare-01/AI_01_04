import os

import pandas as pd  # type: ignore[import-untyped]

# 파일 경로 설정
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(os.path.dirname(BASE_DIR), "kcd_codes.csv")


# 1. 샘플 CSV 파일이 없으면 자동으로 생성하는 함수
def initialize_csv():
    if not os.path.exists(CSV_PATH):
        print("📝 샘플 질병코드 파일을 생성합니다...")
        data = {
            "code": ["J00", "J20.9", "M17", "E11", "I10", "K21.9"],
            "name": [
                "급성 비인두염(감기)",
                "상세불명의 급성 기관지염",
                "무릎관절증(퇴행성 관절염)",
                "2형 당뇨병",
                "본태성(원발성) 고혈압",
                "상세불명의 위-식도역류병",
            ],
        }
        df_sample = pd.DataFrame(data)
        df_sample.to_csv(CSV_PATH, index=False, encoding="utf-8-sig")
        print(f"✅ {CSV_PATH} 생성 완료!")


# 2. 데이터 로드 로직
initialize_csv()  # 실행 시 파일 생성 체크

try:
    df = pd.read_csv(CSV_PATH)
    # 코드를 키로, 병명을 값으로 변환
    disease_dict = pd.Series(df.name.values, index=df.code.astype(str)).to_dict()
    print(f">>> \n질병코드 {len(disease_dict)}건 로드 완료")
except Exception as e:
    print(f"❌ 데이터 로드 실패: {e}")
    disease_dict = {}


def get_disease_name(code):
    clean_code = str(code).strip().upper()
    return disease_dict.get(clean_code, f"미등록 질병코드({code})")
