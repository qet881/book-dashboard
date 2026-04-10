import streamlit as st
import google.generativeai as genai
from google import genai
from google.genai import types
import json
import os
import re
from urllib.parse import quote

st.set_page_config(
    page_title="📚 독서 주치의 — 양평도서관",
    page_icon="📚",
    layout="wide"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Serif+KR:wght@400;700&family=Noto+Sans+KR:wght@300;400;500&display=swap');

html, body, [class*="css"] { font-family: 'Noto Sans KR', sans-serif; }
h1, h2, h3 { font-family: 'Noto Serif KR', serif; }
.stApp { background-color: #0f0f0f; color: #e8e0d0; }

.book-card {
    background: #1a1a1a;
    border: 1px solid #2a2a2a;
    border-radius: 12px;
    padding: 20px 24px;
    margin-bottom: 14px;
}
.book-card:hover { border-color: #c8a96e; }
.score-badge {
@@ -87,89 +90,137 @@ READING_DNA = """
- 반직관적 프레임워크, 확률적 사고, 역발상
- 빠른 챕터 페이스, 즉각 적용 가능한 통찰
- 대표 고평점: 《안티프래질》탈레브(5.0), 《투자에 대한 생각》하워드 막스(5.0), 《감정은 어떻게 만들어지는가》배럿(5.0)

[확인된 트랩 패턴 — 절대 추천 금지]
- 서양 문학 고전 + 실존주의 내면 독백 (카뮈, 쿤데라, 오스틴)
- 순수 격언/아포리즘 컬렉션
- 강의 편집·컴파일 형식
- 여러 인물 사례 나열식 구성
- 추천 절대 금지 도서: 《미움받을 용기》, 《죽음의 수용소에서》

[이미 읽은 책 — 추천 제외]
히가시노 게이고(마구/악의/숙명/편지/용의자X/나미야/녹나무), 찬호께이(13.67/풍선인간/염소가웃는순간/망내인/기억나지않음형사),
아키요시 리카코(성모/유리의살의), 미나토 가나에(고백/속죄), 아비코 다케마루(살육에이르는병),
나카야마 시치리(연쇄살인마개구리남자), 아사쿠라 아키나리(여섯명의거짓말쟁이대학생),
정해연(유괴의날/홍학의자리), 양귀자(희망/원미동사람들/모순), 천명관(고래),
탈레브(안티프래질/행운에속지마라), 하워드막스(투자에대한생각), 리사펠드먼배럿(감정은어떻게만들어지는가)
"""

def get_gemini_key():
    try:
        return st.secrets["GEMINI_API_KEY"]
    except:
        return None

def _extract_json_payload(raw_text):
    text = (raw_text or "").strip()
    if not text:
        raise ValueError("모델 응답이 비어 있습니다.")

    fence_pattern = r"```(?:json)?\s*(.*?)\s*```"
    fenced = re.search(fence_pattern, text, re.DOTALL | re.IGNORECASE)
    if fenced:
        return fenced.group(1).strip()

    start = text.find("[")
    end = text.rfind("]")
    if start != -1 and end != -1 and end >= start:
        return text[start : end + 1].strip()

    return text

def generate_recommendations(gemini_key, genre, count):
    genai.configure(api_key=gemini_key)
    model = genai.GenerativeModel("gemini-1.5-flash")
    model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    client = genai.Client(api_key=gemini_key)

    prompt = f"""
당신은 독서 취향 분석 전문가입니다. 아래 독서 DNA를 가진 독자에게 맞는 책을 추천하세요.

[독자의 독서 DNA]
{READING_DNA}

요청: {genre} 장르에서 {count}권 추천
- 이미 읽은 책 목록에 있는 책은 절대 추천하지 마세요
- 추천 금지 도서는 절대 포함하지 마세요
- 한국 출판 시장에서 구할 수 있는 책으로 추천하세요

아래 JSON 배열로만 응답하세요. 다른 텍스트 없이 JSON만:
[
  {{
    "title": "책 제목 (원제 아닌 한국어 출판 제목)",
    "author": "저자명",
    "score": 88,
    "verdict": "강력매수",
    "reason": "이 독자에게 맞는 이유 1~2문장. 포트폴리오 선례 인용 필수."
  }}
]

score: 0~100 (취향 적중률 예측)
verdict: 강력매수(80+) / 매수(60~79) / 관심종목(40~59)
"""
    response_schema = types.Schema(
        type=types.Type.ARRAY,
        items=types.Schema(
            type=types.Type.OBJECT,
            required=["title", "author", "score", "verdict", "reason"],
            properties={
                "title": types.Schema(type=types.Type.STRING),
                "author": types.Schema(type=types.Type.STRING),
                "score": types.Schema(type=types.Type.INTEGER),
                "verdict": types.Schema(type=types.Type.STRING),
                "reason": types.Schema(type=types.Type.STRING),
            },
        ),
    )

    try:
        response = model.generate_content(prompt)
        text = response.text.strip()
        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        return json.loads(text)
        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=response_schema,
                temperature=0.4,
            ),
        )
        text = _extract_json_payload(getattr(response, "text", ""))
        recommendations = json.loads(text)
        if not isinstance(recommendations, list) or not recommendations:
            raise ValueError("추천 결과 JSON이 비어 있거나 배열 형식이 아닙니다.")
        return recommendations
    except Exception as e:
        raw_response = ""
        try:
            raw_response = getattr(response, "text", "") if "response" in locals() else ""
        except Exception:
            raw_response = ""
        st.error(f"AI 분석 실패: {e}")
        if raw_response:
            with st.expander("디버그: Gemini 원문 응답 보기"):
                st.code(raw_response)
        st.info("추천 생성에 실패했습니다. 잠시 후 다시 시도하거나 GEMINI_MODEL 설정을 확인해주세요.")
        return []

def yangpyeong_search_url(title, author):
    query = f"{title} {author}".strip()
    encoded = quote(query)
    return f"https://www.yplib.go.kr/search/tot/searchTotList.do?kwd={encoded}"

def main():
    st.markdown('<div class="header-title">📚 독서 주치의</div>', unsafe_allow_html=True)
    st.markdown('<div class="header-sub">나의 독서 DNA 기반 추천 → 양평도서관 바로 검색</div>', unsafe_allow_html=True)

    gemini_key = get_gemini_key()
    if not gemini_key:
        st.warning("⚙️ Secrets에 GEMINI_API_KEY를 설정해주세요.")
        return

    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        genre = st.selectbox("장르", [
            "전체 (픽션 + 논픽션)",
            "미스터리 / 스릴러",
            "한국 소설",
            "일본 소설",
            "논픽션 / 자기계발",
            "투자 / 경제",
