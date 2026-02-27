# 네이버 응답에서 “우리가 쓸 부분”만 타입으로 정의(선택)
# 전부 다 정의할 필요 없음. fields -> inferText 같은 최소만

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

# 네이버 OCR 응답은 상품/버전에 따라 세부 구조가 조금 달라질 수 있어서
# "우리가 쓰는 최소 필드만" 정의 + extra="allow"로 유연하게 받도록 설계.


class OCRField(BaseModel):
    """
    OCR 결과의 가장 작은 단위(단어/토큰/블록).
    네이버 OCR 응답에서 보통 fields[*].inferText 를 많이 사용함.
    """

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    infer_text: str | None = Field(default=None, alias="inferText")
    infer_confidence: float | None = Field(default=None, alias="inferConfidence")


class OCRImageResult(BaseModel):
    """
    이미지(페이지) 단위 결과.
    """

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    uid: str | None = None
    name: str | None = None
    infer_result: str | None = Field(default=None, alias="inferResult")
    message: str | None = None

    fields: list[OCRField] = Field(default_factory=list)


class OCRErrorInfo(BaseModel):
    """
    일부 응답에는 error/code/message 형태가 포함되기도 함.
    """

    model_config = ConfigDict(extra="allow")

    code: str | None = None
    message: str | None = None


class NaverOCRResponse(BaseModel):
    """
    네이버 OCR 최상위 응답.
    """

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    version: str | None = None
    request_id: str | None = Field(default=None, alias="requestId")
    timestamp: int | None = None

    images: list[OCRImageResult] = Field(default_factory=list)
    error: OCRErrorInfo | None = None

    def full_text(self, sep: str = " ") -> str:
        """
        inferText를 모두 합쳐서 전체 텍스트를 만들기 위한 헬퍼.
        parser.py에서 쓰기 좋게 schemas에 넣어둠.
        """
        tokens: list[str] = []
        for img in self.images:
            for f in img.fields or []:
                if f.infer_text:
                    tokens.append(str(f.infer_text))
        return sep.join(tokens).strip()


# ---- (선택) 내부 표준 결과 스키마: parser의 출력 형태를 고정하고 싶을 때 ----


class ParsedPrescription(BaseModel):
    """
    OCR raw를 파싱해서 우리 서비스에서 쓰는 표준 결과 형태(선택).
    """

    model_config = ConfigDict(extra="allow")

    document_date: str | None = None  # YYYY-MM-DD (처방/진단 날짜)
    diagnosis: str | None = None
    drugs: list[str] = Field(default_factory=list)

    raw_text: str | None = None  # 전체 텍스트
    ocr_raw: dict[str, Any] | None = None  # 원본 raw(json) (저장/디버깅용)
