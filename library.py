import streamlit as st
import google.generativeai as genai
import json
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
    display: inline-block;
    background: #c8a96e;
    color: #0f0f0f;
    font-weight: 700;
    font-size: 13px;
    padding: 3px 10px;
    border-radius: 20px;
    margin-right: 8px;
}
.book-title {
    font-family: 'Noto Serif KR', serif;
    font-size: 18px;
    font-weight: 700;
    color: #e8e0d0;
    margin: 8px 0 4px 0;
}
.book-author { font-size: 13px; color: #888; margin-bottom: 10px; }
.ai-comment {
    font-size: 14px; color: #b8b0a0; line-height: 1.6;
    border-left: 2px solid #c8a96e;
    padding-left: 12px; margin-top: 10px;
}
.header-title {
    font-family: 'Noto Serif KR', serif;
    font-size: 32px; font-weight: 700; color: #c8a96e; margin-bottom: 4px;
}
.header-sub { font-size: 14px; color: #666; margin-bottom: 32px; }
.stat-box {
    background: #1a1a1a; border: 1px solid #2a2a2a;
    border-radius: 8px; padding: 16px; text-align: center;
}
.stat-num { font-size: 28px; font-weight: 700; color: #c8a96e; }
.stat-label { font-size: 12px; color: #666; margin-top: 4px; }
a.lib-btn {
    display: inline-block;
    margin-top: 12px;
    background: #1e3a2e;
    color: #7dcc74 !important;
    border: 1px solid #2d5a40;
    border-radius: 6px;
    padding: 6px 14px;
    font-size: 13px;
    text-decoration: none !important;
}
a.lib-btn:hover { background: #2d5a40; }
</style>
""", unsafe_allow_html=True)

READING_DNA = """
[고평점 픽션 DNA — 4.5~5.0점]
- 연작/앤솔로지 구조, 챕터마다 시점 전환, 반전 축적
- 동아시아 작가 압도적 선호 (한국·일본·홍콩·중국)
- 앙상블 캐릭터, 사회 비평, 심리적 깊이
- 충격적 반전과 감정적 폭발이 있는 미스터리/스릴러
- 대표 고평점: 《13.67》찬호께이(5.0), 《성모》아키요시 리카코(4.5), 《살육에 이르는 병》아비코(4.5), 《여섯명의 거짓말쟁이 대학생》아사쿠라(4.5), 《풍선인간》찬호께이(4.5), 《홍학의 자리》정해연(4.5)

[고평점 논픽션 DNA — 4.5~5.0점]
- 세계관 렌즈를 통째로 바꾸는 책
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

def generate_recommendations(gemini_key, genre, count):
    genai.configure(api_key=gemini_key)
    model = genai.GenerativeModel("gemini-2.0-flash")

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
    try:
        response = model.generate_content(prompt)
        text = response.text.strip()
        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        return json.loads(text)
    except Exception as e:
        st.error(f"AI 분석 실패: {e}")
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
            "심리학 / 뇌과학",
            "만화 / 그래픽노블",
        ])
    with col2:
        count = st.slider("추천 권수", 5, 20, 10, 5)
    with col3:
        st.markdown("<br>", unsafe_allow_html=True)

    if st.button("🔍 추천 받기", type="primary", use_container_width=True):
        with st.spinner(f"📖 독서 DNA 분석 중... {genre} {count}권 추천 생성"):
            books = generate_recommendations(gemini_key, genre, count)

        if not books:
            st.error("추천 생성에 실패했습니다.")
            return

        books.sort(key=lambda x: x.get("score", 0), reverse=True)

        st.divider()
        s1, s2, s3 = st.columns(3)
        strong = sum(1 for b in books if b.get("score", 0) >= 80)
        avg = int(sum(b.get("score", 0) for b in books) / len(books)) if books else 0

        with s1:
            st.markdown(f'<div class="stat-box"><div class="stat-num">{len(books)}</div><div class="stat-label">추천 도서</div></div>', unsafe_allow_html=True)
        with s2:
            st.markdown(f'<div class="stat-box"><div class="stat-num">{strong}</div><div class="stat-label">강력매수</div></div>', unsafe_allow_html=True)
        with s3:
            st.markdown(f'<div class="stat-box"><div class="stat-num">{avg}</div><div class="stat-label">평균 적중률</div></div>', unsafe_allow_html=True)

        st.divider()
        st.markdown(f"### 🎯 추천 결과 ({len(books)}권) — 양평도서관 재고 직접 확인")

        for b in books:
            score = b.get("score", 0)
            verdict = b.get("verdict", "")
            title = b.get("title", "")
            author = b.get("author", "")
            reason = b.get("reason", "")
            lib_url = yangpyeong_search_url(title, author)

            verdict_color = {
                "강력매수": "#c8a96e",
                "매수": "#7dcc74",
                "관심종목": "#ccaa44"
            }.get(verdict, "#888")

            st.markdown(f"""
<div class="book-card">
    <span class="score-badge">{score}점</span>
    <span style="color:{verdict_color}; font-weight:600; font-size:13px;">{verdict}</span>
    <div class="book-title">{title}</div>
    <div class="book-author">{author}</div>
    <div class="ai-comment">{reason}</div>
    <a class="lib-btn" href="{lib_url}" target="_blank">📖 양평도서관에서 검색 →</a>
</div>
""", unsafe_allow_html=True)

    else:
        st.info("👆 장르 선택 후 추천 받기 버튼을 눌러주세요.")

if __name__ == "__main__":
    main()
