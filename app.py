import streamlit as st
import pdfplumber
import re
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib import font_manager
from collections import Counter
from janome.tokenizer import Tokenizer
import os, requests

# ===== 日本語フォントを動的ダウンロード（Cloud対応） =====
FONT_URL = "https://github.com/googlefonts/noto-cjk/raw/main/Sans/OTF/Japanese/NotoSansCJKjp-Regular.otf"
FONT_PATH = "NotoSansCJKjp-Regular.otf"

if not os.path.exists(FONT_PATH):
    r = requests.get(FONT_URL)
    with open(FONT_PATH, "wb") as f:
        f.write(r.content)

plt.rcParams['font.family'] = font_manager.FontProperties(fname=FONT_PATH).get_name()
plt.rcParams['axes.unicode_minus'] = False

# ===== ページ設定 =====
st.set_page_config(page_title="統合報告書PDF語尾・時制分析アプリ", layout="wide")
st.title("📄 統合報告書PDF語尾・時制分析アプリ")
st.write("企業の統合報告書PDFから文末語尾と時制（過去形・現在形）を分析し、文体傾向を可視化します。")

# ===== PDFアップロード =====
uploaded_file = st.file_uploader("分析したい統合報告書PDFをアップロードしてください", type=["pdf"])

if uploaded_file is not None:
    with st.spinner("PDFを読み込み中..."):
        def extract_text_from_pdf(file):
            all_text = ""
            with pdfplumber.open(file) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        all_text += text + "\n"
            return all_text

        text = extract_text_from_pdf(uploaded_file)
        st.success("✅ PDFテキストを抽出しました！")
        st.write("📖 抽出された冒頭部分：")
        st.code(text[:500] + "..." if len(text) > 500 else text)

    # --- 文分割 ---
    sentences = re.split(r'[。！？]', text)
    sentences = [s.strip() for s in sentences if s.strip()]

    # --- 時制分類 ---
    def get_tense(sentence):
        if re.search(r'(た|だった|ました|でした)[^ぁ-んァ-ヶ一-龠]*$', sentence):
            return "過去形"
        else:
            return "現在・未来形"

    data = [{"文": s, "区分": get_tense(s)} for s in sentences]
    df = pd.DataFrame(data)

    # ===== 🥧 時制の割合 =====
    st.subheader("📈 時制の割合（文数ベース）")
    tense_counts = df["区分"].value_counts()
    fig_ratio, ax_ratio = plt.subplots(figsize=(5,5))
    ax_ratio.pie(
        tense_counts,
        labels=tense_counts.index,
        autopct="%1.1f%%",
        startangle=90,
        colors=["cornflowerblue", "orange"]
    )
    ax_ratio.axis("equal")
    ax_ratio.set_title("過去形 vs 現在・未来形 の割合")
    st.pyplot(fig_ratio)

    st.dataframe(pd.DataFrame(tense_counts).rename(columns={"区分":"文数"}))

    # --- 文末語尾抽出 ---
    def extract_sentence_ending(s):
        match = re.search(r'(である|となります|になります|いたします|でした|だった|ます|ました|です|だ)$', s)
        return match.group(1) if match else None

    endings = [extract_sentence_ending(s) for s in sentences if extract_sentence_ending(s)]
    ending_counts = Counter(endings)
    df_endings = pd.DataFrame(ending_counts.items(), columns=["語尾", "出現回数"]).sort_values("出現回数", ascending=False)

    # --- 棒グラフ ---
    st.subheader("📊 文末語尾の出現頻度")
    st.dataframe(df_endings, use_container_width=True)

    fig1, ax1 = plt.subplots(figsize=(6,4))
    ax1.barh(df_endings["語尾"], df_endings["出現回数"], color="steelblue")
    ax1.invert_yaxis()
    ax1.set_title("文末語尾の出現頻度", fontsize=14)
    ax1.set_xlabel("出現回数")
    st.pyplot(fig1)

    # --- 時制別頻出語 ---
    st.subheader("🕰 時制別頻出語（上位20語）")
    tokenizer = Tokenizer()
    def extract_words(text):
        words = []
        for token in tokenizer.tokenize(text):
            pos = token.part_of_speech.split(',')[0]
            if pos in ["名詞", "動詞", "形容詞"]:
                words.append(token.base_form)
        return words

    word_freq = {}
    for label, group in df.groupby("区分"):
        words = []
        for sentence in group["文"]:
            words.extend(extract_words(sentence))
        word_freq[label] = Counter(words).most_common(20)

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### 🔵 過去形で頻出した単語")
        past_df = pd.DataFrame(word_freq.get("過去形", []), columns=["単語", "出現回数"])
        st.dataframe(past_df)
        if not past_df.empty:
            fig2, ax2 = plt.subplots(figsize=(6,4))
            ax2.barh(past_df["単語"], past_df["出現回数"], color="cornflowerblue")
            ax2.invert_yaxis()
            ax2.set_title("過去形：頻出単語")
            st.pyplot(fig2)

    with col2:
        st.markdown("#### 🟠 現在・未来形で頻出した単語")
        future_df = pd.DataFrame(word_freq.get("現在・未来形", []), columns=["単語", "出現回数"])
        st.dataframe(future_df)
        if not future_df.empty:
            fig3, ax3 = plt.subplots(figsize=(6,4))
            ax3.barh(future_df["単語"], future_df["出現回数"], color="orange")
            ax3.invert_yaxis()
            ax3.set_title("現在・未来形：頻出単語")
            st.pyplot(fig3)

    csv = df_endings.to_csv(index=False).encode('utf-8-sig')
    st.download_button("📥 文末語尾集計結果をCSVでダウンロード", data=csv, file_name="語尾集計結果.csv", mime="text/csv")

else:
    st.info("👆 上のボックスから統合報告書PDFファイルを選択してください。")
