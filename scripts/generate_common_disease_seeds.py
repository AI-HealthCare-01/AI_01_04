"""일상 진료 고빈도 질환 추천 시드 생성 스크립트.

현재 03-seed-recommendations.json에 없는 고빈도 질환에 대해
기본 건강관리/복약주의/추적관찰 가이드를 생성하여 병합한다.

사용법:
    python scripts/generate_common_disease_seeds.py

결과:
    scripts/init-db/03-seed-recommendations.json에 병합됨
    scripts/init-db/04-* 매핑 파일도 재생성 필요
"""

from __future__ import annotations

import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
RECOMMENDATION_JSON = BASE_DIR / "scripts" / "init-db" / "03-seed-recommendations.json"

# 추가할 질환별 추천 가이드
# 형식: (disease_code, disease_name, original_disease_name, [(category, content), ...])
COMMON_DISEASE_GUIDES: list[tuple[str, str, str, list[tuple[str, str]]]] = [
    # === 호흡기 ===
    (
        "J06",
        "급성 상기도감염",
        "감기",
        [
            ("general_care", "충분한 수분 섭취와 휴식을 취하세요"),
            ("general_care", "실내 습도를 50~60%로 유지하세요"),
            ("medication_caution", "해열제는 38.5도 이상일 때 복용하고, 용법·용량을 지키세요"),
            ("follow_up", "고열이 3일 이상 지속되거나 호흡곤란이 있으면 재진료를 받으세요"),
        ],
    ),
    (
        "J02",
        "급성 인두염",
        "인두염",
        [
            ("general_care", "따뜻한 물이나 차를 자주 마시고 목을 쉬게 하세요"),
            ("general_care", "자극적인 음식과 찬 음료를 피하세요"),
            ("medication_caution", "항생제가 처방된 경우 증상이 호전되어도 처방 기간을 끝까지 복용하세요"),
            ("follow_up", "고열이 지속되거나 음식을 삼키기 어려우면 재진료를 받으세요"),
        ],
    ),
    (
        "J03",
        "급성 편도염",
        "편도염",
        [
            ("general_care", "충분한 수분 섭취와 안정을 취하세요"),
            ("general_care", "부드러운 음식을 섭취하고 자극적인 음식을 피하세요"),
            ("medication_caution", "항생제가 처방된 경우 정해진 기간 동안 빠짐없이 복용하세요"),
            ("follow_up", "편도염이 반복되면 이비인후과 전문의와 상담하세요"),
        ],
    ),
    (
        "J20",
        "급성 기관지염",
        "기관지염",
        [
            ("general_care", "충분한 수분 섭취로 가래 배출을 도우세요"),
            ("general_care", "흡연을 삼가고 먼지가 많은 환경을 피하세요"),
            ("medication_caution", "기침 억제제와 거담제를 혼용하지 마세요"),
            ("follow_up", "기침이 3주 이상 지속되면 추가 검사를 받으세요"),
        ],
    ),
    (
        "J30",
        "알레르기성 비염",
        "알레르기비염",
        [
            ("general_care", "꽃가루·먼지 등 알레르겐 노출을 최소화하세요"),
            ("general_care", "외출 후 세안과 코 세척을 하세요"),
            ("medication_caution", "항히스타민제 복용 시 졸음이 올 수 있으니 운전에 주의하세요"),
            ("follow_up", "증상이 일상생활에 지장을 줄 정도면 알레르기 검사를 받아보세요"),
        ],
    ),
    (
        "J45",
        "천식",
        "천식",
        [
            ("general_care", "먼지, 담배연기, 찬 공기 등 유발인자를 피하세요"),
            ("general_care", "규칙적인 유산소 운동을 하되 과격한 운동은 피하세요"),
            ("medication_caution", "흡입기 사용법을 정확히 익히고 정해진 시간에 사용하세요"),
            ("medication_caution", "증상이 없어도 예방 흡입제를 임의로 중단하지 마세요"),
            ("follow_up", "야간 증상이 잦거나 응급 흡입기 사용이 늘면 진료를 받으세요"),
        ],
    ),
    # === 소화기 ===
    (
        "K21",
        "위식도역류병",
        "역류성식도염",
        [
            ("general_care", "식후 바로 눕지 말고 최소 2~3시간 후에 눕세요"),
            ("general_care", "과식을 피하고 기름진 음식, 카페인, 탄산음료를 줄이세요"),
            ("medication_caution", "제산제는 식후 1시간 또는 취침 전에 복용하세요"),
            ("follow_up", "속쓰림이 4주 이상 지속되면 내시경 검사를 고려하세요"),
        ],
    ),
    (
        "K58",
        "과민성장증후군",
        "과민성장증후군",
        [
            ("general_care", "규칙적인 식사와 충분한 식이섬유 섭취를 하세요"),
            ("general_care", "스트레스 관리와 규칙적인 운동이 증상 완화에 도움됩니다"),
            ("medication_caution", "증상 유형(설사형/변비형)에 맞는 약물을 복용하세요"),
            ("follow_up", "체중 감소, 혈변 등 경고 증상이 있으면 즉시 진료를 받으세요"),
        ],
    ),
    # === 근골격계 ===
    (
        "M17",
        "무릎관절증",
        "무릎관절염",
        [
            ("general_care", "적정 체중을 유지하여 무릎 부담을 줄이세요"),
            ("general_care", "수영, 자전거 등 관절에 부담이 적은 운동을 하세요"),
            ("medication_caution", "소염진통제는 위장장애가 올 수 있으니 식후에 복용하세요"),
            ("follow_up", "관절 부종이나 잠김 현상이 있으면 정형외과 진료를 받으세요"),
        ],
    ),
    (
        "M51",
        "추간판장애",
        "디스크",
        [
            ("general_care", "올바른 자세를 유지하고 장시간 같은 자세를 피하세요"),
            ("general_care", "무거운 물건을 들 때 허리가 아닌 무릎을 굽혀 들어올리세요"),
            ("medication_caution", "근이완제 복용 시 졸음이 올 수 있으니 주의하세요"),
            ("follow_up", "하지 저림이나 근력 약화가 있으면 즉시 진료를 받으세요"),
        ],
    ),
    (
        "M54",
        "등통증",
        "요통",
        [
            ("general_care", "적절한 스트레칭과 코어 근력 운동을 꾸준히 하세요"),
            ("general_care", "장시간 앉아있을 때는 1시간마다 일어나 움직이세요"),
            ("medication_caution", "진통제를 장기 복용하지 말고 증상이 지속되면 진료를 받으세요"),
            ("follow_up", "통증이 6주 이상 지속되거나 다리로 방사되면 정밀검사를 받으세요"),
        ],
    ),
    (
        "M79",
        "연조직장애",
        "근육통",
        [
            ("general_care", "무리한 활동을 피하고 충분한 휴식을 취하세요"),
            ("general_care", "온찜질이나 가벼운 스트레칭으로 근육 긴장을 풀어주세요"),
            ("medication_caution", "소염진통제는 단기간 사용하고 위장장애에 주의하세요"),
            ("follow_up", "통증이 2주 이상 지속되거나 부종이 동반되면 진료를 받으세요"),
        ],
    ),
    (
        "M75",
        "어깨병변",
        "어깨질환",
        [
            ("general_care", "어깨 스트레칭을 꾸준히 하되 통증 범위 내에서 하세요"),
            ("general_care", "팔을 머리 위로 반복적으로 올리는 동작을 피하세요"),
            ("medication_caution", "소염진통제와 함께 물리치료를 병행하면 효과적입니다"),
            ("follow_up", "야간 통증이 심하거나 팔을 올리기 어려우면 정형외과 진료를 받으세요"),
        ],
    ),
    # === 피부 ===
    (
        "L20",
        "아토피피부염",
        "아토피",
        [
            ("general_care", "보습제를 하루 2회 이상 충분히 바르세요"),
            ("general_care", "뜨거운 물 목욕을 피하고 미지근한 물로 짧게 씻으세요"),
            ("medication_caution", "스테로이드 연고는 처방된 부위와 기간만 사용하세요"),
            ("follow_up", "피부 감염 징후(진물, 고름)가 보이면 진료를 받으세요"),
        ],
    ),
    (
        "L50",
        "두드러기",
        "두드러기",
        [
            ("general_care", "원인 물질(음식, 약물 등)을 파악하고 피하세요"),
            ("general_care", "피부를 긁지 말고 냉찜질로 가려움을 완화하세요"),
            ("medication_caution", "항히스타민제 복용 시 졸음에 주의하세요"),
            ("follow_up", "호흡곤란이나 입술/혀 부종이 동반되면 즉시 응급실을 방문하세요"),
        ],
    ),
    # === 정신건강 ===
    (
        "F32",
        "우울에피소드",
        "우울증",
        [
            ("general_care", "규칙적인 수면과 기상 시간을 유지하세요"),
            ("general_care", "가벼운 산책이나 운동을 매일 30분 이상 하세요"),
            ("medication_caution", "항우울제는 효과가 나타나기까지 2~4주가 걸릴 수 있으니 꾸준히 복용하세요"),
            ("medication_caution", "임의로 약을 중단하면 금단 증상이 올 수 있으니 반드시 의료진과 상의하세요"),
            ("follow_up", "자해 충동이나 극심한 무기력감이 있으면 즉시 전문의와 상담하세요"),
        ],
    ),
    (
        "F41",
        "불안장애",
        "불안장애",
        [
            ("general_care", "복식호흡이나 명상 등 이완 기법을 연습하세요"),
            ("general_care", "카페인과 알코올 섭취를 줄이세요"),
            ("medication_caution", "항불안제는 의존성이 있을 수 있으니 처방대로만 복용하세요"),
            ("follow_up", "공황발작이 반복되거나 일상생활이 어려우면 정신건강의학과 진료를 받으세요"),
        ],
    ),
    (
        "F51",
        "비기질성 수면장애",
        "수면장애",
        [
            ("general_care", "매일 같은 시간에 자고 일어나는 수면 습관을 만드세요"),
            ("general_care", "취침 전 스마트폰, TV 등 전자기기 사용을 줄이세요"),
            ("medication_caution", "수면제는 단기간만 사용하고 장기 복용 시 의료진과 상의하세요"),
            ("follow_up", "불면이 4주 이상 지속되면 수면 클리닉 상담을 받아보세요"),
        ],
    ),
    # === 신경계 ===
    (
        "G43",
        "편두통",
        "편두통",
        [
            ("general_care", "유발인자(스트레스, 수면부족, 특정 음식)를 파악하고 피하세요"),
            ("general_care", "규칙적인 식사와 충분한 수면을 유지하세요"),
            ("medication_caution", "두통약을 월 10일 이상 복용하면 약물과용두통이 올 수 있으니 주의하세요"),
            ("follow_up", "두통 양상이 변하거나 구토·시력장애가 동반되면 진료를 받으세요"),
        ],
    ),
    (
        "G47",
        "수면장애",
        "수면장애(신경계)",
        [
            ("general_care", "규칙적인 수면 스케줄과 쾌적한 수면 환경을 유지하세요"),
            ("general_care", "낮잠은 30분 이내로 제한하세요"),
            ("medication_caution", "수면 보조제는 의료진 처방에 따라 단기간만 사용하세요"),
            ("follow_up", "코골이나 수면 중 호흡 멈춤이 있으면 수면다원검사를 받아보세요"),
        ],
    ),
    # === 눈/귀 ===
    (
        "H10",
        "결막염",
        "결막염",
        [
            ("general_care", "손으로 눈을 만지지 말고 손 씻기를 자주 하세요"),
            ("general_care", "수건, 베개 등 개인 물품을 공유하지 마세요"),
            ("medication_caution", "안약은 정해진 횟수와 간격을 지켜 점안하세요"),
            ("follow_up", "시력 저하나 심한 통증이 있으면 안과 진료를 받으세요"),
        ],
    ),
    (
        "H65",
        "비화농성 중이염",
        "중이염",
        [
            ("general_care", "코를 세게 풀지 말고 한쪽씩 부드럽게 풀으세요"),
            ("general_care", "수영이나 물놀이 시 귀에 물이 들어가지 않도록 주의하세요"),
            ("medication_caution", "항생제가 처방된 경우 증상이 호전되어도 끝까지 복용하세요"),
            ("follow_up", "청력 저하가 느껴지거나 귀에서 분비물이 나오면 이비인후과 진료를 받으세요"),
        ],
    ),
    # === 비뇨기 ===
    (
        "N76",
        "질 및 외음부의 기타 염증",
        "질염",
        [
            ("general_care", "통풍이 잘 되는 면 속옷을 착용하세요"),
            ("general_care", "질 내부 세정제 사용을 피하고 외음부만 깨끗이 씻으세요"),
            ("medication_caution", "처방된 질정이나 연고는 증상이 호전되어도 치료 기간을 지키세요"),
            ("follow_up", "증상이 반복되면 원인균 검사를 받아보세요"),
        ],
    ),
    # === 증상/징후 ===
    (
        "R10",
        "복부 및 골반 통증",
        "복통",
        [
            ("general_care", "자극적인 음식을 피하고 소화가 잘 되는 음식을 드세요"),
            ("general_care", "스트레스 관리와 규칙적인 식사 습관을 유지하세요"),
            ("follow_up", "복통이 지속되거나 발열·구토가 동반되면 진료를 받으세요"),
        ],
    ),
    (
        "R50",
        "달리 분류되지 않은 발열",
        "발열",
        [
            ("general_care", "충분한 수분 섭취와 휴식을 취하세요"),
            ("medication_caution", "해열제는 38.5도 이상일 때 복용하고 용법을 지키세요"),
            ("follow_up", "고열이 3일 이상 지속되거나 원인을 모르면 진료를 받으세요"),
        ],
    ),
]


def generate_seed_entries() -> list[dict]:
    entries = []
    for code, name, original, guides in COMMON_DISEASE_GUIDES:
        for category, content in guides:
            entries.append(
                {
                    "disease_code": code,
                    "disease_name": name,
                    "original_disease_name": original,
                    "category": category,
                    "content": content,
                    "source": "common_disease_guide",
                }
            )
    return entries


def main() -> None:
    with RECOMMENDATION_JSON.open("r", encoding="utf-8") as f:
        existing = json.load(f)

    existing_codes = set(r["disease_code"] for r in existing)
    new_entries = generate_seed_entries()

    added_codes = set()
    added_count = 0
    for entry in new_entries:
        if entry["disease_code"] not in existing_codes:
            existing.append(entry)
            added_codes.add(entry["disease_code"])
            added_count += 1

    with RECOMMENDATION_JSON.open("w", encoding="utf-8") as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)

    print(f"[DONE] 기존 시드: {len(existing) - added_count}건")
    print(f"[DONE] 추가된 질환: {len(added_codes)}개, 추가된 항목: {added_count}건")
    print(f"[DONE] 총 시드: {len(existing)}건")
    print(f"[DONE] 추가된 질환 코드: {sorted(added_codes)}")
    print()
    print("다음 단계: 매핑 재빌드 필요")
    print("  python scripts/build_disease_code_mapping_v2.py")


if __name__ == "__main__":
    main()
