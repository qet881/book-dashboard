import streamlit as st
import requests
import pandas as pd
import google.generativeai as genai
import xml.etree.ElementTree as ET
import json

st.set_page_config(
    page_title="📚 독서 주치의 — 양평도서관",
    page_icon="📚",
    layout="wide"
)

# ── 스타일 ──────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Serif+KR:wght@400;700&family=Noto+Sans+KR:wght@300;400;500&display=swap');

html, body, [class*="css"] {
    font-family: 'Noto Sans KR', sans-serif;
}
h1, h2, h3 {
    font-family: 'Noto Serif KR', serif;
}
.main { background-color: #0f0f0f; }
.stApp { background-color: #0f0f0f; color: #e8e0d0; }

.book-card {
    background: #1a1a1a;
    border: 1px solid #2a2a2a;
    border-radius: 12px;
    padding: 20px;
    margin-bottom: 16px;
    transition: border-color 0.2s;
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
.available-badge {
    display: inline-block;
    background: #2d5a27;
    color: #7dcc74;
    font-size: 12px;
    padding: 3px 10px;
    border-radius: 20px;
}
.unavailable-badge {
    display: inline-block;
    background: #3a1a1a;
    color: #cc7474;
    font-size: 12px;
    padding: 3px 10px;
    border-radius: 20px;
}
.book-title {
    font-family: 'Noto Serif KR', serif;
    font-size: 18px;
    font-weight: 700;
    color: #e8e0d0;
    margin: 8px 0 4px 0;
}
.book-author {
    font-size: 13px;
    color: #888;
    margin-bottom: 10px;
}
.ai-comment {
    font-size: 14px;
    color: #b8b0a0;
    line-height: 1.6;
    border-left: 2px solid #c8a96e;
    padding-left: 12px;
    margin-top: 10px;
}
.header-title {
    font-family: 'Noto Serif KR', serif;
    font-size: 32px;
    font-weight: 700;
    color: #c8a96e;
    margin-bottom: 4px;
}
.header-sub {
    font-size: 14px;
    color: #666;
    margin-bottom: 32px;
}
.stat-box {
    background: #1a1a1a;
    border: 1px solid #2a2a2a;
    border-radius: 8px;
    padding: 16px;
    text-align: center;
}
.stat-num {
    font-size: 28px;
    font-weight: 700;
    color: #c8a96e;
}
.stat-label {
    font-size: 12px;
    color: #666;
    margin-top: 4px;
}
</style>
""", unsafe_allow_html=True)

# ── 독서 DNA 정의 ──────────────────────────────────────
READING_DNA = """
[고평점 픽션 DNA — 4.5~5.0점]
- 연작/앤솔로지 구조, 챕터마다 시점 전환, 반전 축적
- 동아시아 작가 압도적 선호 (한국·일본·홍콩·중국)
- 앙상블 캐릭터, 사회 비평, 심리적 깊이
- 충격적 반전과 감정적 폭발이 있는 미스터리/스릴러
- 대표작: 《13.67》찬호께이(5.0), 《성모》아키요시 리카코(4.5), 《살육에 이르는 병》아비코(4.5), 《여섯명의 거짓말쟁이 대학생》(4.5)

[고평점 논픽션 DNA — 4.5~5.0점]
- 세계관 렌즈를 통째로 바꾸는 책
- 반직관적 프레임워크, 확률적 사고
- 빠른 챕터 페이스, 즉각 적용 가능한 통찰
- 대표작: 《안티프래질》탈레브(5.0), 《투자에 대한 생각》하워드 막스(5.0), 《감정은 어떻게 만들어지는가》배럿(5.0)

[확인된 트랩 패턴 — 저평점 반복]
- 서양 문학 고전 + 실존주의 내면 독백 (카뮈, 쿤데라, 오스틴 → 1.5~2.0)
- 순수 격언/아포리즘 컬렉션 (에픽테토스 → 1.0)
- 강의 편집·컴파일 형식 (가난한 찰리의 연감 → 2.0)
- 여러 인물 사례 나열식 구성
- 장황한 묘사 위주의 서양 문학
- 추천 금지: 《미움받을 용기》, 《죽음의 수용소에서》
"""

# ── API 설정 ────────────────────────────────────────────
def get_api_keys():
    try:
        gemini_key = st.secrets["GEMINI_API_KEY"]
        library_key = st.secrets["LIBRARY_API_KEY"]
        return gemini_key, library_key
    except:
        return None, None

# ── 정보나루 API ─────────────────────────────────────────
LIB_CODE = "264032"  # 양평군립도서관

def get_new_arrivals(auth_key, page_size=30):
    """양평도서관 신착도서 조회"""
    url = "http://data4library.kr/api/newArrivalList"
    params = {
        "authKey": auth_key,
        "libCode": LIB_CODE,
        "pageNo": 1,
        "pageSize": page_size,
        "format": "json"
    }
    try:
        resp = requests.get(url, params=params, timeout=10)
        data = resp.json()
        docs = data.get("response", {}).get("docs", [])
        books = []
        for doc in docs:
            d = doc.get("doc", {})
            books.append({
                "title": d.get("bookname", ""),
                "author": d.get("authors", ""),
                "publisher": d.get("publisher", ""),
                "isbn": d.get("isbn13", ""),
                "pub_date": d.get("publication_year", ""),
                "class_nm": d.get("class_nm", ""),
                "bookImageURL": d.get("bookImageURL", ""),
                "loan_count": d.get("loan_count", 0),
            })
        return books
    except Exception as e:
        st.error(f"신착도서 조회 실패: {e}")
        return []

def check_availability(auth_key, isbn):
    """대출 가능 여부 확인"""
    if not isbn:
        return None
    url = "http://data4library.kr/api/bookExist"
    params = {
        "authKey": auth_key,
        "libCode": LIB_CODE,
        "isbn13": isbn,
        "format": "json"
    }
    try:
        resp = requests.get(url, params=params, timeout=5)
        data = resp.json()
        result = data.get("response", {}).get("result", {})
        has_book = result.get("hasBook", "N")
        loan_available = result.get("loanAvailable", "N")
        return {"has_book": has_book == "Y", "loan_available": loan_available == "Y"}
    except:
        return None

# ── Gemini 분석 ─────────────────────────────────────────
def analyze_books_with_gemini(gemini_key, books):
    """Gemini로 취향 적중률 분석"""
    genai.configure(api_key=gemini_key)
    model = genai.GenerativeModel("gemini-2.0-flash")

    book_list = "\n".join([
        f"{i+1}. 제목: {b['title']} | 저자: {b['author']} | 분류: {b['class_nm']}"
        for i, b in enumerate(books)
    ])

    prompt = f"""
당신은 독서 취향 분석 전문가입니다. 아래 독서 DNA를 가진 독자를 위해 신착 도서 목록을 분석하세요.

[독자의 독서 DNA]
{READING_DNA}

[양평도서관 신착 도서 목록]
{book_list}

각 책에 대해 아래 JSON 배열로만 응답하세요. 다른 텍스트 없이 JSON만 출력하세요:
[
  {{
    "index": 1,
    "score": 85,
    "reason": "취향 적중 이유를 1~2문장으로 (투자 언어 사용: 강력매수/매수/보류/매도)",
    "verdict": "강력매수"
  }},
  ...
]

score: 0~100 (취향 적중률). 트랩 패턴은 20 이하. 동아시아 미스터리/반전 구조는 80 이상.
verdict: 강력매수(80+) / 매수(60~79) / 보류(40~59) / 매도(40 미만)
모든 책에 대해 반드시 응답하세요.
"""

    try:
        response = model.generate_content(prompt)
        text = response.text.strip()
        # JSON 파싱
        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        return json.loads(text)
    except Exception as e:
        st.error(f"Gemini 분석 실패: {e}")
        return []

# ── 메인 UI ─────────────────────────────────────────────
def main():
    st.markdown('<div class="header-title">📚 독서 주치의</div>', unsafe_allow_html=True)
    st.markdown('<div class="header-sub">양평도서관 신착도서 × 나의 독서 DNA 분석</div>', unsafe_allow_html=True)

    gemini_key, library_key = get_api_keys()

    if not gemini_key or not library_key:
        st.warning("⚙️ secrets.toml에 API 키를 설정해주세요.")
        with st.expander("설정 방법 보기"):
            st.code("""
# .streamlit/secrets.toml
GEMINI_API_KEY = "여기에_Gemini_키_입력"
LIBRARY_API_KEY = "여기에_정보나루_키_입력"
""", language="toml")
        return

    # ── 컨트롤 바 ──
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        page_size = st.slider("신착도서 조회 수", 10, 50, 20, 5)
    with col2:
        min_score = st.slider("최소 적중률", 0, 100, 50, 10)
    with col3:
        only_available = st.checkbox("대출 가능만", value=True)

    if st.button("🔍 분석 시작", type="primary", use_container_width=True):
        
        # 1. 신착도서 조회
        with st.spinner("양평도서관 신착도서 불러오는 중..."):
            books = get_new_arrivals(library_key, page_size)
        
        if not books:
            st.error("신착도서를 불러올 수 없습니다. 도서관 코드 또는 API 키를 확인하세요.")
            return

        # 2. Gemini 분석
        with st.spinner(f"📖 {len(books)}권을 독서 DNA로 분석 중..."):
            analysis = analyze_books_with_gemini(gemini_key, books)

        if not analysis:
            st.error("AI 분석에 실패했습니다.")
            return

        # 3. 대출 가능 여부 확인
        with st.spinner("대출 현황 확인 중..."):
            availability = {}
            for book in books:
                if book["isbn"]:
                    availability[book["isbn"]] = check_availability(library_key, book["isbn"])

        # 4. 결과 병합 및 정렬
        results = []
        analysis_map = {a["index"]: a for a in analysis}
        
        for i, book in enumerate(books):
            a = analysis_map.get(i + 1, {})
            score = a.get("score", 0)
            avail = availability.get(book["isbn"])
            loan_ok = avail["loan_available"] if avail else False
            
            if score < min_score:
                continue
            if only_available and not loan_ok:
                continue

            results.append({
                **book,
                "score": score,
                "reason": a.get("reason", ""),
                "verdict": a.get("verdict", ""),
                "loan_available": loan_ok,
            })

        results.sort(key=lambda x: x["score"], reverse=True)

        # 5. 통계
        st.divider()
        s1, s2, s3, s4 = st.columns(4)
        with s1:
            st.markdown(f'<div class="stat-box"><div class="stat-num">{len(books)}</div><div class="stat-label">신착도서</div></div>', unsafe_allow_html=True)
        with s2:
            strong_buy = sum(1 for r in results if r["score"] >= 80)
            st.markdown(f'<div class="stat-box"><div class="stat-num">{strong_buy}</div><div class="stat-label">강력매수</div></div>', unsafe_allow_html=True)
        with s3:
            avail_count = sum(1 for r in results if r["loan_available"])
            st.markdown(f'<div class="stat-box"><div class="stat-num">{avail_count}</div><div class="stat-label">지금 대출 가능</div></div>', unsafe_allow_html=True)
        with s4:
            avg = int(sum(r["score"] for r in results) / len(results)) if results else 0
            st.markdown(f'<div class="stat-box"><div class="stat-num">{avg}</div><div class="stat-label">평균 적중률</div></div>', unsafe_allow_html=True)

        st.divider()

        if not results:
            st.info("조건에 맞는 책이 없습니다. 필터를 조정해보세요.")
            return

        # 6. 도서 카드
        st.markdown(f"### 🎯 추천 결과 ({len(results)}권)")

        for r in results:
            verdict_color = {
                "강력매수": "#c8a96e",
                "매수": "#7dcc74", 
                "보류": "#ccaa44",
                "매도": "#cc7474"
            }.get(r["verdict"], "#888")

            avail_html = (
                '<span class="available-badge">✅ 대출 가능</span>' 
                if r["loan_available"] 
                else '<span class="unavailable-badge">⏳ 대출 중</span>'
            )

            st.markdown(f"""
<div class="book-card">
    <span class="score-badge">{r['score']}점</span>
    <span style="color:{verdict_color}; font-weight:600; font-size:13px;">{r['verdict']}</span>
    {avail_html}
    <div class="book-title">{r['title']}</div>
    <div class="book-author">{r['author']} · {r['publisher']} · {r['pub_date']}</div>
    <div class="ai-comment">{r['reason']}</div>
</div>
""", unsafe_allow_html=True)

    else:
        st.info("👆 분석 시작 버튼을 눌러주세요.")
        st.markdown("""
        **이 앱은:**
        - 양평도서관 신착 도서를 실시간으로 가져옵니다
        - AI가 당신의 독서 DNA(226권 분석)와 비교합니다
        - 지금 당장 빌릴 수 있는 책만 필터링합니다
        """)

if __name__ == "__main__":
    main()
