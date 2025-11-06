import streamlit as st
import pdfplumber
import re
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib import font_manager
from collections import Counter
from janome.tokenizer import Tokenizer

# ===== 日本語フォント設定 =====
# Google Notoフォントを優先的に使用
plt.rcParams['font.family'] = 'Noto Sans CJK JP'
plt.rcParams['axes.unicode_minus'] = False  # マイナス記号の文字化け対策
# ===== タイトル =====
st.set_page_config(page_title="PDF語尾・時制分析アプリ", layout="wide")
st.title("📄 PDF語尾・時制分析アプリ")
st.write("PDFから文末語尾と、過去形／現在形の頻出単語を分析します。")

# ===== PDFアップロード =====
uploaded_file = st.file_uploader("分析したいPDFファイルをアップロードしてください", type=["pdf"])

if uploaded_file is not None:
    with st.spinner("PDFを読み込み中..."):
        def extract_text_from_pdf(file):
            all_text = ""
            with pdfplumber.open(file) as pdf:
                for page in pdf.pages:
                    all_text += page.extract_text() + "\n"
            return all_text

        text = extract_text_from_pdf(uploaded_file)
        st.success("PDFテキストを抽出しました！")
        st.write("📖 抽出された冒頭部分：")
        st.code(text[:500] + "..." if len(text) > 500 else text)

    # ===== 文の分割 =====
    sentences = re.split(r'[。！？]', text)
    sentences = [s.strip() for s in sentences if s.strip()]

    # ===== 語尾判定 =====
    def get_tense(sentence):
        if re.search(r'(た|だった|ました|でした)[^ぁ-んァ-ヶ一-龠]*$', sentence):
            return "過去形"
        else:
            return "現在・未来形"

    data = [{"文": s, "区分": get_tense(s)} for s in sentences]
    df = pd.DataFrame(data)

    # ===== 語尾集計 =====
    def extract_sentence_ending(s):
        match = re.search(r'(である|となります|になります|いたします|でした|だった|ます|ました|です|だ)$', s)
        return match.group(1) if match else None

    endings = [extract_sentence_ending(s) for s in sentences if extract_sentence_ending(s)]
    ending_counts = Counter(endings)
    df_endings = pd.DataFrame(ending_counts.items(), columns=["語尾", "出現回数"]).sort_values("出現回数", ascending=False)

    # ===== 表と棒グラフ =====
    st.subheader("📊 文末語尾の出現頻度")
    st.dataframe(df_endings, use_container_width=True)

    fig1, ax1 = plt.subplots(figsize=(6,4))
    ax1.barh(df_endings["語尾"], df_endings["出現回数"], color="steelblue")
    ax1.invert_yaxis()
    ax1.set_title("文末語尾の出現頻度", fontsize=14)
    ax1.set_xlabel("出現回数")
    st.pyplot(fig1)

    # ===== 時制別頻出語抽出 =====
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

    # 過去形
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

    # 現在・未来形
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
else:
    st.info("👆 上のボックスからPDFファイルを選択してください。")
