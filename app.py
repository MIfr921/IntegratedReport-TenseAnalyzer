import streamlit as st
import pdfplumber
import re
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib import font_manager
from collections import Counter
from janome.tokenizer import Tokenizer
from pykakasi import kakasi
import os, requests

# ===== フォント設定（Cloud対応） =====
FONT_URL = "https://github.com/googlefonts/noto-cjk/raw/main/Sans/OTF/Japanese/NotoSansCJKjp-Regular.otf"
FONT_PATH = "NotoSansCJKjp-Regular.otf"
if not os.path.exists(FONT_PATH):
    r = requests.get(FONT_URL)
    with open(FONT_PATH, "wb") as f:
        f.write(r.content)
plt.rcParams['font.family'] = font_manager.FontProperties(fname=FONT_PATH).get_name()
plt.rcParams['axes.unicode_minus'] = False

# ===== Romaji変換器 =====
kakasi_inst = kakasi()
kakasi_inst.setMode("H", "a")
kakasi_inst.setMode("K", "a")
kakasi_inst.setMode("J", "a")
converter = kakasi_inst.getConverter()
def to_roman(txt):
    """日本語をローマ字に変換"""
    if not isinstance(txt, str): return txt
    try: return converter.do(txt)
    except: return txt

# ===== Streamlit設定 =====
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

    # ===== 文分割 =====
    sentences = re.split(r'[。！？]', text)
    sentences = [s.strip() for s in sentences if s.strip()]

    # ===== 時制分類 =====
    def get_tense(s):
        if re.search(r'(た|だった|ました|でした)[^ぁ-んァ-ヶ一-龠]*$', s):
            return "過去形"
        else:
            return "現在・未来形"

    df = pd.DataFrame([{"文": s, "区分": get_tense(s)} for s in sentences])

    # ===== 🥧 時制割合（グラフのみローマ字） =====
    st.subheader("📈 時制の割合（グラフ＝ローマ字）")
    tense_counts = df["区分"].value_counts()

    # グラフ用にローマ字化
    labels_romaji = [to_roman(label) for label in tense_counts.index]

    fig_ratio, ax_ratio = plt.subplots(figsize=(5,5))
    ax_ratio.pie(
        tense_counts,
        labels=labels_romaji,
        autopct="%1.1f%%",
        startangle=90,
        colors=["cornflowerblue", "orange"]
    )
    ax_ratio.axis("equal")
    ax_ratio.set_title("Kako-kei vs Genzai-Mirai-kei (Ratio)")
    st.pyplot(fig_ratio)

    # 表は日本語で表示
    st.dataframe(pd.DataFrame(tense_counts).rename(columns={"区分":"文数"}))

    # ===== 文末語尾集計 =====
    def extract_sentence_ending(s):
        m = re.search(r'(である|となります|になります|いたします|でした|だった|ます|ました|です|だ)$', s)
        return m.group(1) if m else None

    endings = [extract_sentence_ending(s) for s in sentences if extract_sentence_ending(s)]
    ending_counts = Counter(endings)
    df_end = pd.DataFrame(ending_counts.items(), columns=["語尾","出現回数"]).sort_values("出現回数",ascending=False)

    # ===== 📊 文末語尾頻度（グラフ＝ローマ字） =====
    st.subheader("📊 文末語尾の出現頻度（グラフ＝ローマ字）")
    st.dataframe(df_end, use_container_width=True)

    # グラフ用ラベルをローマ字に変換
    labels_romaji = [to_roman(label) for label in df_end["語尾"]]

    fig1, ax1 = plt.subplots(figsize=(6,4))
    ax1.barh(labels_romaji, df_end["出現回数"], color="steelblue")
    ax1.invert_yaxis()
    ax1.set_title("Sentence Endings Frequency (Romaji)", fontsize=13)
    ax1.set_xlabel("Count")
    st.pyplot(fig1)

    # ===== 🕰 時制別頻出語 =====
    st.subheader("🕰 時制別頻出語（グラフ＝ローマ字）")
    tokenizer = Tokenizer()
    def extract_words(t):
        words=[]
        for tk in tokenizer.tokenize(t):
            if tk.part_of_speech.split(',')[0] in ["名詞","動詞","形容詞"]:
                words.append(tk.base_form)
        return words

    word_freq={}
    for label,grp in df.groupby("区分"):
        ws=[]
        for s in grp["文"]: ws.extend(extract_words(s))
        word_freq[label]=Counter(ws).most_common(20)

    col1,col2=st.columns(2)
    with col1:
        st.markdown("#### 🔵 過去形")
        past_df=pd.DataFrame(word_freq.get("過去形",[]),columns=["単語","出現回数"])
        st.dataframe(past_df)
        if not past_df.empty:
            fig2,ax2=plt.subplots(figsize=(6,4))
            # グラフのラベルだけローマ字化
            ax2.barh([to_roman(w) for w in past_df["単語"]], past_df["出現回数"], color="cornflowerblue")
            ax2.invert_yaxis(); ax2.set_title("Kako-kei: Frequent Words (Romaji)")
            st.pyplot(fig2)
    with col2:
        st.markdown("#### 🟠 現在・未来形")
        fut_df=pd.DataFrame(word_freq.get("現在・未来形",[]),columns=["単語","出現回数"])
        st.dataframe(fut_df)
        if not fut_df.empty:
            fig3,ax3=plt.subplots(figsize=(6,4))
            ax3.barh([to_roman(w) for w in fut_df["単語"]], fut_df["出現回数"], color="orange")
            ax3.invert_yaxis(); ax3.set_title("Genzai-Mirai-kei: Frequent Words (Romaji)")
            st.pyplot(fig3)

    # ===== CSV出力（日本語データ） =====
    csv = df_end.to_csv(index=False).encode('utf-8-sig')
    st.download_button(
        "📥 文末語尾集計結果をCSVでダウンロード（日本語）",
        data=csv,
        file_name="ending_counts_japanese.csv",
        mime="text/csv"
    )

else:
    st.info("👆 上のボックスから統合報告書PDFファイルを選択してください。")
