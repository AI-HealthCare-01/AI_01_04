from __future__ import annotations

from app.integrations.openai.client import chat_completion


async def recommendation_chat_completion(
    system_prompt: str,
    user_prompt: str,
) -> str:
    """
    recommendation 후처리 전용 ChatCompletion 호출.

    중복 제거/문장 정리 용도이므로 낮은 temperature를 사용한다.
    """
    return await chat_completion(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        temperature=0.2,
    )
