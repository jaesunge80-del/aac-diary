import streamlit as st
import google.generativeai as genai
from pathlib import Path

try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
except Exception:
    st.error("🔑 API 키가 없어요! Streamlit Cloud Secrets에 GEMINI_API_KEY를 추가해주세요.")
    st.stop()

IMAGE_DIR   = Path("images")
SUBJECT_DIR = IMAGE_DIR / "주어"
OBJECT_DIR  = IMAGE_DIR / "목적어"
VERB_DIR    = IMAGE_DIR / "동사"

@st.cache_data
def load_card_names():
    def get_names(folder_path):
        if not folder_path.exists():
            return []
        return [
            f.stem
            for f in folder_path.iterdir()
            if f.suffix.lower() in [".png", ".jpg", ".jpeg"]
        ]
    return {
        "주어":  get_names(SUBJECT_DIR),
        "목적어": get_names(OBJECT_DIR),
        "동사":  get_names(VERB_DIR),
    }

card_names = load_card_names()

def find_best_card(keyword: str, category: str):
    folder_map = {
        "주어":  SUBJECT_DIR,
        "목적어": OBJECT_DIR,
        "동사":  VERB_DIR
    }
    folder = folder_map[category]
    names  = card_names[category]
    if not names:
        return None
    if keyword in names:
        return _get_file_path(folder, keyword)
    for name in names:
        if keyword in name or name in keyword:
            return _get_file_path(folder, name)
    matched = ask_gemini_for_similar_word(keyword, names)
    if matched:
        return _get_file_path(folder, matched)
    return None

def _get_file_path(folder: Path, stem: str):
    for ext in [".png", ".jpg", ".jpeg"]:
        path = folder / f"{stem}{ext}"
        if path.exists():
            return path
    return None

def ask_gemini_for_similar_word(keyword: str, candidates: list):
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        prompt = (
            f"다음 단어와 의미가 가장 비슷한 단어를 아래 목록에서 딱 하나만 골라줘.\n"
            f"반드시 목록에 있는 단어 그대로만 답해줘. 설명이나 다른 말은 절대 하지 마.\n\n"
            f"찾는 단어: {keyword}\n"
            f"목록: {', '.join(candidates)}"
        )
        response = model.generate_content(prompt)
        result = response.text.strip()
        if result in candidates:
            return result
        for c in candidates:
            if c in result:
                return c
    except Exception:
        pass
    return None

def extract_keywords_from_image(uploaded_file) -> dict:
    uploaded_file.seek(0)
    image_bytes = uploaded_file.read()
    image_part = {
        "mime_type": uploaded_file.type,
        "data": image_bytes
    }
    model = genai.GenerativeModel("gemini-1.5-flash")
    prompt = (
        "이 사진을 보고 가장 중요한 행동을 한 단어씩 추출해줘.\n"
        "반드시 아래 형식으로만 답해줘. 다른 말은 절대 하지 마:\n\n"
        "주어: [한 단어]\n"
        "목적어: [한 단어]\n"
        "동사: [한 단어]"
    )
    response = model.generate_content([prompt, image_part])
    return parse_keywords(response.text)

def extract_keywords_from_text(user_text: str) -> dict:
    model = genai.GenerativeModel("gemini-1.5-flash")
    prompt = (
        f"다음 문장에서 가장 중요한 행동을 한 단어씩 추출해줘.\n"
        f"반드시 아래 형식으로만 답해줘. 다른 말은 절대 하지 마:\n\n"
        f"주어: [한 단어]\n"
        f"목적어: [한 단어]\n"
        f"동사: [한 단어]\n\n"
        f"문장: {user_text}"
    )
    response = model.generate_content(prompt)
    return parse_keywords(response.text)

def parse_keywords(text: str) -> dict:
    result = {"주어": "", "목적어": "", "동사": ""}
    for line in text.strip().split("\n"):
        for key in result:
            if f"{key}:" in line:
                result[key] = line.split(f"{key}:")[-1].strip()
    return result

def generate_diary_sentence(subject: str, obj: str, verb: str) -> str:
    model = genai.GenerativeModel("gemini-1.5-flash")
    prompt = (
        f"AAC 사용자를 위한 따뜻하고 짧은 일기 문장 2개를 만들어줘.\n"
        f"초등학교 1학년도 이해할 수 있을 만큼 쉽고 단순하게 써줘.\n"
        f"긍정적이고 응원하는 느낌으로 써줘.\n\n"
        f"주어: {subject}\n"
        f"목적어: {obj}\n"
        f"동사: {verb}"
    )
    response = model.generate_content(prompt)
    return response.text.strip()

def show_aac_cards(keywords: dict):
    st.subheader("🃏 AAC 그림카드")
    col1, col2, col3 = st.columns(3)
    categories = [
        (col1, "주어",  "👤"),
        (col2, "목적어", "🎯"),
        (col3, "동사",  "⚡"),
    ]
    for col, label, emoji in categories:
        keyword = keywords.get(label, "")
        with col:
            st.markdown(f"### {emoji} {label}")
            st.markdown(
                f"<div style='text-align:center; font-size:18px; "
                f"font-weight:bold; color:#555; margin-bottom:8px;'>"
                f"「{keyword}」</div>",
                unsafe_allow_html=True
            )
            if keyword:
                card_path = find_best_card(keyword, label)
                if card_path:
                    st.image(str(card_path), use_container_width=True)
                    matched_name = card_path.stem
                    if matched_name != keyword:
                        st.caption(f"🔗 '{keyword}' → '{matched_name}' 카드 사용")
                else:
                    st.markdown(
                        f"""<div style="border:3px dashed #ddd; border-radius:12px;
                            padding:40px 10px; text-align:center; color:#bbb;
                            background-color:#fafafa;">
                            <div style="font-size:36px;">🖼️</div>
                            <div style="font-size:14px; margin-top:8px;">
                                카드 없음<br>
                                <b style="color:#888;">{keyword}</b>
                            </div></div>""",
                        unsafe_allow_html=True
                    )
                    st.caption("💡 이 단어의 카드를 추가하면 표시돼요")
            else:
                st.markdown("_(키워드 없음)_")

st.set_page_config(
    page_title="나만의 AAC 그림 일기",
    page_icon="🎨",
    layout="centered"
)

st.title("🎨 나만의 AAC 그림 일기")
st.caption("사진이나 문장을 입력하면 그림카드로 표현해드려요! 📷✏️")

total_cards = sum(len(v) for v in card_names.values())
if total_cards > 0:
    st.info(
        f"📚 현재 등록된 그림카드: **{total_cards}장**  \n"
        f"👤 주어 {len(card_names['주어'])}장 · "
        f"🎯 목적어 {len(card_names['목적어'])}장 · "
        f"⚡ 동사 {len(card_names['동사'])}장"
    )
else:
    st.warning(
        "⚠️ 그림카드가 없어요!  \n"
        "`images/주어/`, `images/목적어/`, `images/동사/` 폴더에 이미지를 넣어주세요."
    )

st.divider()

tab1, tab2 = st.tabs(["📷 사진으로 표현하기", "✏️ 글로 표현하기"])

keywords = None

with tab1:
    st.markdown("**오늘 있었던 일을 사진으로 올려주세요!**")
    uploaded_file = st.file_uploader(
        "사진 선택 (jpg, jpeg, png)",
        type=["jpg", "jpeg", "png"],
        key="photo_upload"
    )
    if uploaded_file is not None:
        st.image(uploaded_file, caption="📸 내가 올린 사진", use_container_width=True)
        if st.button("🔍 그림카드 찾기", use_container_width=True, key="btn_photo"):
            with st.spinner("AI가 사진을 분석하고 있어요... 잠깐만요! 🔍"):
                try:
                    keywords = extract_keywords_from_image(uploaded_file)
                    st.session_state["keywords"] = keywords
                except Exception as e:
                    st.error(f"❌ 사진 분석에 실패했어요. 다시 시도해주세요.\n\n오류: {e}")

with tab2:
    st.markdown("**오늘 있었던 일을 짧게 써주세요!**")
    st.caption("예: '오늘 엄마랑 밥을 먹었어요' / '친구랑 공원에서 놀았어'")
    user_text = st.text_input(
        "문장 입력",
        placeholder="오늘 있었던 일을 써주세요",
        key="text_input",
        label_visibility="collapsed"
    )
    if st.button("🔍 그림카드 찾기", use_container_width=True, key="btn_text"):
        if user_text.strip():
            with st.spinner("AI가 문장을 분석하고 있어요... 🔍"):
                try:
                    keywords = extract_keywords_from_text(user_text)
                    st.session_state["keywords"] = keywords
                except Exception as e:
                    st.error(f"❌ 문장 분석에 실패했어요. 다시 시도해주세요.\n\n오류: {e}")
        else:
            st.warning("⚠️ 문장을 먼저 입력해주세요!")

if keywords is None and "keywords" in st.session_state:
    keywords = st.session_state["keywords"]

if keywords:
    subject = keywords.get("주어",  "")
    obj     = keywords.get("목적어", "")
    verb    = keywords.get("동사",  "")

    st.divider()

    st.subheader("📝 추출된 키워드")
    c1, c2, c3 = st.columns(3)
    c1.metric(label="👤 주어",  value=subject or "없음")
    c2.metric(label="🎯 목적어", value=obj     or "없음")
    c3.metric(label="⚡ 동사",  value=verb    or "없음")

    st.divider()

    show_aac_cards(keywords)

    st.divider()

    st.subheader("📖 오늘의 일기")
    with st.spinner("일기 문장을 만들고 있어요... 📖"):
        try:
            diary = generate_diary_sentence(subject, obj, verb)
            st.success(diary)
        except Exception as e:
            st.error(f"일기 생성에 실패했어요: {e}")

    st.divider()
    st.markdown(
        """
        <div style="text-align:center; padding:20px;
                    background-color:#FFF9E6; border-radius:12px;">
            <div style="font-size:40px;">🌟</div>
            <div style="font-size:20px; font-weight:bold; color:#F5A623;">
                오늘 하루도 정말 잘했어요!
            </div>
            <div style="font-size:14px; color:#888; margin-top:8px;">
                내일은 어떤 일이 있을까요?
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )
    st.balloons()

    if st.button("🔄 다시 하기", use_container_width=True):
        if "keywords" in st.session_state:
            del st.session_state["keywords"]
        st.rerun()