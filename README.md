# 📊 IntegratedReport-TenseAnalyzer
**統合報告書PDFに特化した日本語語尾・時制分析アプリ**

このツールは、企業の統合報告書（Integrated Report）などの日本語PDFから  
文末の語尾（例：「です」「ました」「である」など）を自動抽出し、  
文体の特徴（丁寧・叙述・未来志向など）を可視化します。

---

## 🚀 特徴
- PDFファイルをアップロードするだけで自動分析
- 「です／ます／でした／だった」などの語尾頻度を棒グラフ表示
- 文を自動的に過去形／現在・未来形に分類
- 各時制で頻出する単語を抽出・可視化（経営メッセージ傾向分析に有用）

---

## 🧩 使用技術
- Python 3.10+
- [Streamlit](https://streamlit.io/)
- [pdfplumber](https://github.com/jsvine/pdfplumber)
- [Janome](https://mocobeta.github.io/janome/)
- Matplotlib + japanize-matplotlib

---

## 📦 セットアップ

```bash
git clone https://github.com/あなたのユーザー名/IntegratedReport-TenseAnalyzer.git
cd IntegratedReport-TenseAnalyzer
pip install -r requirements.txt
