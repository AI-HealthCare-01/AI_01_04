"""
03-seed-recommendations.json 정제 스크립트 v4

정제 항목:
1. 접속부사 제거 (따라서, 또한, 그러나 등)
2. 잘린 "~가 하기" → 서술형 복원 ("~가 필요합니다")
3. 복수 행동 분리 ("A하고, B하기" → 2개)
4. 분리된 파트에도 복원 재적용
5. 공백 보정 ("을하기" → "을 하기")
6. 번호/불릿 접두사 제거
7. 설명문/라벨 제거, 중복 제거
"""

import json
import re
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "init-db" / "03-seed-recommendations.json"
DST = Path(__file__).resolve().parent / "03-seed-recommendations-refined.json"


# ── 접속부사 제거 ──────────────────────────────────────────────
CONJ_RE = re.compile(
    r"^(?:따라서|단,|그러나|또한|특히|아울러|그러므로|그래서|하지만|"
    r"반면|반대로|다만|물론|우선|이때|이런|이러한|이처럼|이를|이는|"
    r"그리고|그런데|즉,)\s+"
)


def strip_conjunction(text: str) -> str:
    return CONJ_RE.sub("", text.strip()).strip()


# ── 잘린 문장 서술형 복원 ──────────────────────────────────────
RESTORE_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"치료가 하기$"), "치료가 필요합니다"),
    (re.compile(r"관리가 하기$"), "관리가 필요합니다"),
    (re.compile(r"검사가 하기$"), "검사가 필요합니다"),
    (re.compile(r"수술이 하기$"), "수술이 필요합니다"),
    (re.compile(r"확인이 하기$"), "확인이 필요합니다"),
    (re.compile(r"평가가 하기$"), "평가가 필요합니다"),
    (re.compile(r"조절이 하기$"), "조절이 필요합니다"),
    (re.compile(r"상담이 하기$"), "상담이 필요합니다"),
    (re.compile(r"투여가 하기$"), "투여가 필요합니다"),
    (re.compile(r"주의가 하기$"), "주의가 필요합니다"),
    (re.compile(r"교육이 하기$"), "교육이 필요합니다"),
    (re.compile(r"접종이 하기$"), "접종이 필요합니다"),
    (re.compile(r"보충이 하기$"), "보충이 필요합니다"),
    (re.compile(r"관찰이 하기$"), "관찰이 필요합니다"),
    (re.compile(r"시행이 하기$"), "시행이 필요합니다"),
    (re.compile(r"복용이 하기$"), "복용이 필요합니다"),
    (re.compile(r"방문이 하기$"), "방문이 필요합니다"),
    (re.compile(r"휴식이 하기$"), "휴식이 필요합니다"),
    (re.compile(r"시술이 하기$"), "시술이 필요합니다"),
    (re.compile(r"치료를 하기$"), "치료를 해야 합니다"),
    # ~에/에도 하기
    (re.compile(r"에 하기$"), "에 도움이 됩니다"),
    (re.compile(r"에도 하기$"), "에도 도움이 됩니다"),
    (re.compile(r"데 하기$"), "데 도움이 됩니다"),
    # ~것이 하기
    (re.compile(r"것이 건강에 하기$"), "것이 건강에 좋습니다"),
    (re.compile(r"것이 가장 하기$"), "것이 가장 좋습니다"),
    (re.compile(r"것이 장기적으로 하기$"), "것이 장기적으로 좋습니다"),
    (re.compile(r"것이 하기$"), "것이 좋습니다"),
    (re.compile(r"것을 하기$"), "것을 권장합니다"),
    # ~도 하기
    (re.compile(r"도 하기$"), "도 도움이 됩니다"),
    # 중요함
    (re.compile(r"중요함$"), "중요합니다"),
]

BROKEN_RE = re.compile(
    r"(?:"
    r"(?:이|가)\s+하기"
    r"|(?:에|에도|데)\s+하기"
    r"|것이\s+(?:가장\s+|건강에\s+|장기적으로\s+)?하기"
    r"|것을\s+하기"
    r"|도\s+하기"
    r"|중요함"
    r")$"
)


def restore_broken(text: str) -> str:
    t = text.strip()
    if not BROKEN_RE.search(t):
        return t
    for pat, repl in RESTORE_PATTERNS:
        if pat.search(t):
            return pat.sub(repl, t)
    if re.search(r"(?:이|가)\s+하기$", t):
        return re.sub(r"하기$", "필요합니다", t)
    return t


# ── 복수 행동 분리 ─────────────────────────────────────────────
SPLIT_RE = re.compile(r"하고,\s*|하고\s+|하며,\s*|하며\s+")
NO_SPLIT_KW = ["제외하고", "비교하고", "고려하고", "생각하고"]


def split_actions(text: str) -> list[str]:
    t = text.strip()
    if not t.endswith("하기") and not t.endswith("합니다") and not t.endswith("됩니다"):
        return [t]
    if not re.search(r"하고[,\s]|하며[,\s]", t):
        return [t]
    for kw in NO_SPLIT_KW:
        if kw in t:
            return [t]

    parts = SPLIT_RE.split(t)
    if len(parts) < 2:
        return [t]

    results = []
    for i, chunk in enumerate(parts):
        chunk = chunk.strip()
        if not chunk:
            continue
        if i < len(parts) - 1 and not chunk.endswith("하기"):
            chunk = chunk + "하기"
        chunk = re.sub(r"\s+", " ", chunk).strip()
        # 공백 보정: "을하기" → "을 하기"
        chunk = re.sub(r"([을를])하기$", r"\1 하기", chunk)
        if len(chunk) >= 8:
            results.append(chunk)

    return results if len(results) >= 2 else [t]


# ── 접두사 제거 ────────────────────────────────────────────────
NUM_PREFIX_RE = re.compile(r"^[\d]+[\)\.]\s*")
BULLET_RE = re.compile(r"^[˚•●◦▪✔﻿⦁\-]\s*")
SPECIAL_RE = re.compile(r"^[①②③④⑤⑥⑦⑧⑨⑩]\s*")


def clean_prefix(text: str) -> str:
    t = text.strip()
    t = NUM_PREFIX_RE.sub("", t)
    t = BULLET_RE.sub("", t)
    t = SPECIAL_RE.sub("", t)
    return t.strip()


# ── 설명문 필터 ────────────────────────────────────────────────
DESC_ENDINGS = [
    "차지합니다", "의미합니다", "해당합니다", "나뉘어집니다",
    "분류합니다", "이루어집니다", "구성됩니다", "포함됩니다", "비례합니다",
]
MIN_LEN = 8
LABEL_RE = re.compile(r"^[\w\s]{2,12}$")


def is_actionable(text: str, category: str) -> bool:
    t = text.strip()
    if len(t) < MIN_LEN:
        return False
    if LABEL_RE.match(t):
        return False
    for kw in DESC_ENDINGS:
        if t.endswith(kw):
            return False
    if category != "warning_sign":
        if t.endswith("발생합니다") or t.endswith("나타납니다"):
            if not any(k in t for k in ("예방", "주의", "피하")):
                return False
    return True


# ── 후처리 ─────────────────────────────────────────────────────
def postprocess(text: str) -> str:
    t = text.strip().strip("˚•●◦▪✔﻿⦁\"'").strip()
    if t.startswith("<") and t.endswith(">"):
        return ""
    # 공백 보정
    t = re.sub(r"([을를])하기$", r"\1 하기", t)
    return t


# ── 메인 ───────────────────────────────────────────────────────
def main():
    with open(SRC, encoding="utf-8") as f:
        data = json.load(f)

    print(f"원본 항목 수: {len(data)}")

    refined = []
    seen = set()
    stats = {"conj": 0, "restored": 0, "split": 0, "removed_desc": 0, "removed_dup": 0, "removed_short": 0}
    restore_samples = []
    split_samples = []

    for item in data:
        content = item["content"]
        category = item["category"]
        disease_code = item["disease_code"]

        # 접두사 제거
        content = clean_prefix(content)

        # 접속부사 제거
        before_conj = content
        content = strip_conjunction(content)
        if content != before_conj:
            stats["conj"] += 1

        # 잘린 문장 복원
        before_restore = content
        content = restore_broken(content)
        if content != before_restore:
            stats["restored"] += 1
            if len(restore_samples) < 25:
                restore_samples.append((before_conj, content))

        content = postprocess(content)

        # 복수 행동 분리
        parts = split_actions(content)
        if len(parts) > 1:
            stats["split"] += 1
            if len(split_samples) < 15:
                split_samples.append((content, parts))

        for part in parts:
            part = part.strip()

            # 분리된 파트에도 복원 재적용
            part = restore_broken(part)
            part = postprocess(part)

            if not part or len(part) < MIN_LEN:
                stats["removed_short"] += 1
                continue
            if not is_actionable(part, category):
                stats["removed_desc"] += 1
                continue

            dedup_key = (disease_code, category, part.lower().replace(" ", ""))
            if dedup_key in seen:
                stats["removed_dup"] += 1
                continue
            seen.add(dedup_key)

            refined.append({**item, "content": part})

    print(f"정제 후 항목 수: {len(refined)}")
    print(f"통계: {stats}")

    print("\n=== 잘린 문장 복원 샘플 ===")
    for before, after in restore_samples[:12]:
        print(f"  ❌ {before[:85]}")
        print(f"  ✅ {after[:85]}")
        print()

    print("=== 문장 분리 샘플 ===")
    for orig, parts in split_samples[:8]:
        print(f"  원본: {orig[:90]}")
        for i, p in enumerate(parts):
            print(f"    → [{i+1}] {p[:80]}")
        print()

    # 최종 검증
    still_broken = [r for r in refined if BROKEN_RE.search(r["content"])]
    bad_space = [r for r in refined if "을하기" in r["content"] or "를하기" in r["content"]]
    has_conj = [r for r in refined if CONJ_RE.match(r["content"])]

    print(f"검증 — 잔여 잘린 문장: {len(still_broken)}")
    for r in still_broken[:3]:
        print(f"  {r['content'][:80]}")
    print(f"검증 — 공백 누락: {len(bad_space)}")
    for r in bad_space[:3]:
        print(f"  {r['content'][:80]}")
    print(f"검증 — 접속부사 잔여: {len(has_conj)}")
    for r in has_conj[:3]:
        print(f"  {r['content'][:80]}")

    with open(DST, "w", encoding="utf-8") as f:
        json.dump(refined, f, ensure_ascii=False, indent=2)

    print(f"\n저장 완료: {DST}")


if __name__ == "__main__":
    main()
