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
from scipy.stats import chi2_contingency, fisher_exact

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
    if not isinstance(txt, str): return txt
    try: return converter.do(txt)
    except: return txt

# ===== Streamlit設定 =====
st.set_page_config(page_title="統合報告書PDF語尾・時制分析アプリ", layout="wide")
st.title("📄 統合報告書PDF語尾・時制分析アプリ")
st.write("企業の統合報告書PDFから文末語尾・時制・キーワード傾向を分析します。")

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

    # ===== 🥧 時制の割合（グラフはローマ字） =====
    st.subheader("📈 時制の割合（グラフ＝ローマ字）")
    tense_counts = df["区分"].value_counts()
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
    st.dataframe(pd.DataFrame(tense_counts).rename(columns={"区分":"文数"}))

    # ===== 文末語尾抽出 =====
    def extract_sentence_ending(s):
        s = re.sub(r'[。、\s]+$', '', s)
        target = s[-10:]
        m = re.search(r'(でした|だった|ます|ました|です|する|した|なる|である)$', target)
        return m.group(1) if m else None

    endings = [extract_sentence_ending(s) for s in sentences if extract_sentence_ending(s)]
    ending_counts = Counter(endings)
    df_end = pd.DataFrame(ending_counts.items(), columns=["語尾","出現回数"]).sort_values("出現回数",ascending=False)

    st.subheader("📊 文末語尾の出現頻度（グラフ＝ローマ字）")
    st.dataframe(df_end, use_container_width=True)
    fig1, ax1 = plt.subplots(figsize=(6,4))
    ax1.barh([to_roman(w) for w in df_end["語尾"]], df_end["出現回数"], color="steelblue")
    ax1.invert_yaxis()
    ax1.set_title("Sentence Endings Frequency (Romaji)", fontsize=13)
    ax1.set_xlabel("Count")
    st.pyplot(fig1)

    # ===== 📏 特定語の出現頻度と統計比較 =====
    st.subheader("📏 特定語の出現頻度・割合・統計検定")
    user_input = st.text_input("カウントしたい語をカンマ区切りで入力してください（例：成長,方針,未来）")

    if user_input:
        keywords = [w.strip() for w in user_input.split(",") if w.strip()]
        results = []
        total_past = len(df[df["区分"]=="過去形"])
        total_future = len(df[df["区分"]=="現在・未来形"])

        for word in keywords:
            past_contains = df[df["区分"]=="過去形"]["文"].apply(lambda x: word in x).sum()
            future_contains = df[df["区分"]=="現在・未来形"]["文"].apply(lambda x: word in x).sum()

            # 割合
            past_ratio = past_contains / total_past * 100 if total_past else 0
            future_ratio = future_contains / total_future * 100 if total_future else 0

            # 2×2表
            table = [[past_contains, total_past - past_contains],
                     [future_contains, total_future - future_contains]]

            try:
                chi2, p, dof, ex = chi2_contingency(table)
            except ValueError:
                # 0がある場合はFisher
                _, p = fisher_exact(table)

            results.append({
                "語": word,
                "過去形_文数": past_contains,
                "現在・未来形_文数": future_contains,
                "過去形_割合(%)": round(past_ratio, 2),
                "現在・未来形_割合(%)": round(future_ratio, 2),
                "p値": round(p, 4)
            })

        df_stats = pd.DataFrame(results).sort_values("p値")
        st.dataframe(df_stats, use_container_width=True)

        # --- グラフ化（ローマ字ラベル） ---
        fig_kw, ax_kw = plt.subplots(figsize=(6, 4))
        ax_kw.barh([to_roman(w) for w in df_stats["語"]], df_stats["過去形_文数"], color="cornflowerblue", label="Past")
        ax_kw.barh([to_roman(w) for w in df_stats["語"]], df_stats["現在・未来形_文数"], color="orange", left=df_stats["過去形_文数"], label="Present/Future")
        ax_kw.invert_yaxis()
        ax_kw.set_title("Keyword Count by Tense (Romaji)", fontsize=13)
        ax_kw.set_xlabel("Sentence Count")
        ax_kw.legend()
        st.pyplot(fig_kw)

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
