import streamlit as st
import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import os
import time

def get_unique_filename(base_path):
    """
    既存のファイルと重複しない一意のファイル名を生成する
    """
    if not os.path.exists(base_path):
        return base_path

    # ファイル名とその拡張子を分割
    base_name, ext = os.path.splitext(base_path)
    counter = 1

    # 一意のファイル名が見つかるまでループ
    while True:
        new_path = f"{base_name}_{counter}{ext}"
        if not os.path.exists(new_path):
            return new_path
        counter += 1

def generate_page_url(image_url):
    """画像URLからページURLを生成する関数"""
    try:
        # コロン以降の部分を取得
        if '：' in image_url:
            image_url = image_url.split('：')[1].strip()

        # URLの標準化（アンダースコアをスラッシュに置換）
        normalized_url = image_url.replace('https_', 'https://').replace('_', '/')

        # 不要な文字の削除（ファイル拡張子など）
        for ext in ['.jpg', '.jpeg', '.png', '.JPG', '.JPEG', '.PNG']:
            if normalized_url.lower().endswith(ext.lower()):
                normalized_url = normalized_url[:-len(ext)]
                break

        # 末尾のアンダースコアとスラッシュを削除
        normalized_url = normalized_url.rstrip('_/.')

        # 商品IDを抽出
        product_match = re.search(r'shopdetail[/_](\d+)', normalized_url)
        if product_match:
            product_id = product_match.group(1)
            return f"https://wazawaza-select.jp/shopdetail/{product_id}/"

        st.error(f"商品IDを抽出できませんでした: {image_url}")
        return None

    except Exception as e:
        st.error(f"URL解析エラー: {str(e)}")
        return None

def fetch_description_ext(page_url):
    """ページURLからdetailExtTxtまたはM_categoryImageの内容を取得する関数"""
    try:
        # アクセス間隔を設ける
        time.sleep(1)

        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36'
        }
        response = requests.get(page_url, headers=headers, timeout=10)

        # 404エラーの場合
        if response.status_code == 404:
            st.warning(f"現在準備中のページです：{page_url}")
            return "商品情報は準備中です"

        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        description = soup.find('div', class_='detailExtTxt')
        return description.text.strip() if description else "商品情報は準備中です"

    except Exception as e:
        # エラーメッセージを表示せず、デフォルトの文言を返す
        return "商品情報は準備中です"

def fetch_description_txt(page_url):
    """ページURLからdetailTxtの内容を取得する関数"""
    try:
        response = requests.get(page_url)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        # URLがカテゴリーページの場合は空文字を返す
        if '/shopbrand/ct' in page_url:
            return ""

        description = soup.find('div', class_='detailTxt')
        return description.text.strip() if description else ""
    except Exception as e:
        # エラーメッセージを表示せず、空文字を返す
        return ""

# 現在の日付を取得
current_date = datetime.now()

# プルダウンに表示する月の範囲を制限（現在日付から2ヶ月分）
month_options = []
for i in range(2):  # 現在日付から2ヶ月分
    # 月を計算
    target_date = current_date + timedelta(days=i * 30)
    target_month = target_date.strftime("%Y年%m月")

    # 月ごとの「1日〜15日」と「16日〜月末日」の選択肢を追加（重複しないようにする）
    if target_month not in [option.split(' ')[0] for option in month_options]:
        month_options.append(f"{target_month} 1日〜15日掲載分")
        month_options.append(f"{target_month} 16日〜月末日掲載分")

# デフォルト値の設定
current_day = current_date.day
current_month = current_date.strftime("%Y年%m月")
default_index = 0

if 1 <= current_day <= 15:
    # 1日〜15日の場合、同月の16日〜月末を選択
    default_index = month_options.index(f"{current_month} 16日〜月末日掲載分")
else:
    # 16日以降の場合、翌月の1日〜15日を選択
    next_month = (current_date + timedelta(days=30)).strftime("%Y年%m月")
    default_index = month_options.index(f"{next_month} 1日〜15日掲載分")

# 日付選択プルダウンの追加（デフォルト値を設定）
selected_date_range = st.selectbox(
    "掲載日付を選択してください",
    month_options,
    index=default_index
)

st.write(f"選択された期間: {selected_date_range}")

st.write("画像URLを3つ入力してください（.jpg形式のみ）")

# ユーザー入力
image_urls = st.text_area("画像URLを貼り付け", height=150).split("\n")

# 1. カテゴリー判定と並び替え関連の関数を先に定義
def map_urls_by_category(urls):
    """コロンの前の商品カテゴリ名でURLをマッピングする関数"""
    url_map = {
        "名物": None,
        "獲れたて": None,
        "季節の和菓子": None
    }

    # カテゴリ名の変換マップを拡張
    category_map = {
        # 名物関連
        "名物": "名物",
        "名物の味": "名物",
        "名物料理": "名物",
        "名店の味": "名物",

        # 獲れたて関連
        "獲れたて": "獲れたて",
        "採れたて": "獲れたて",
        "とれたて": "獲れたて",
        "収穫": "獲れたて",

        # 季節の和菓子関連
        "季節の和菓子": "季節の和菓子",
        "和菓子": "季節の和菓子",
        "季節菓子": "季節の和菓子",
        "季節の菓子": "季節の和菓子",
        "伝統菓子": "季節の和菓子"
    }

    for url in urls:
        if '：' not in url:
            continue

        # コロンで分割して商品カテゴリ名を取得
        category, url_value = url.split('：', 1)
        category = category.strip()

        # カテゴリ名を標準化して保存
        if category in category_map:
            url_map[category_map[category]] = url_value.strip()
        else:
            # カテゴリ名が完全一致しない場合、部分一致で確認
            matched = False
            for known_category, standard_category in category_map.items():
                if known_category in category or category in known_category:
                    url_map[standard_category] = url_value.strip()
                    matched = True
                    break

            if not matched:
                st.warning(f"認識できないカテゴリ名です: {category}")

    # すべてのカテゴリにURLが割り当てられているか確認
    if None in url_map.values():
        missing = [k for k, v in url_map.items() if v is None]
        st.error(f"以下のカテゴリのURLが見つかりませんでした: {', '.join(missing)}")
        return None

    return url_map

# 2. HTML生成関数を定義
def generate_pc_html(base_url, date_suffix, original_urls):
    """PC用のHTMLコードを生成する関数"""
    # URLをカテゴリごとにマッピング
    url_map = map_urls_by_category(original_urls)
    if not url_map:
        st.error("URLのマッピングに失敗しました。")
        st.stop()
        return None

    html = f"""
        <p class="imadake_main" style="width: 50%; margin: 10px 2% 100px 0; padding: 0; float: left;">
            <img src="{base_url}/imadake_img1_{date_suffix}.png" alt="今だけ、ここだけ" class="fade-img">
            <img src="{base_url}/imadake_img2_{date_suffix}.png" alt="今だけ、ここだけ" class="fade-img">
            <img src="{base_url}/imadake_img3_{date_suffix}.png" alt="今だけ、ここだけ" class="fade-img">
        </p>
    """

    # カテゴリ順でリンクを生成
    categories = [
        ("名物", "imadake_img1s"),
        ("獲れたて", "imadake_img2s"),
        ("季節の和菓子", "imadake_img3s")
    ]

    for category, img_prefix in categories:
        html += f"""
        <p class="imadake_right" style="margin: 0 0 20px 0; padding: 0; float: left;width:45%;">
            <a href="{generate_page_url(url_map[category])}">
                <img src="{base_url}/{img_prefix}_{date_suffix}.png" alt="{category}" class="w100">
            </a>
        </p>
        """

    return html

def generate_sp_html(base_url, date_suffix, generated_page_urls, original_urls):
    """SP用のHTMLコードを生成する関数"""
    # URLをカテゴリごとにマッピング
    url_map = map_urls_by_category(original_urls)
    if not url_map:
        st.error("URLのマッピングに失敗しました。")
        st.stop()
        return None

    return f"""
        <p class="imadake_main">
            <img src="{base_url}/imadake_img1_{date_suffix}.png" alt="今だけ、ここだけ" class="fade-img">
            <img src="{base_url}/imadake_img2_{date_suffix}.png" alt="今だけ、ここだけ" class="fade-img">
            <img src="{base_url}/imadake_img3_{date_suffix}.png" alt="今だけ、ここだけ" class="fade-img">
        </p>
        <div class="imadake_right_container">
            <p class="imadake_right">
                <a href="{generate_page_url(url_map['名物'])}">
                    <img src="{base_url}/imadake_img1s_{date_suffix}.png" alt="名物" class="w100">
                </a>
            </p>
            <p class="imadake_right">
                <a href="{generate_page_url(url_map['獲れたて'])}">
                    <img src="{base_url}/imadake_img2s_{date_suffix}.png" alt="獲れたて" class="w100">
                </a>
            </p>
            <p class="imadake_right">
                <a href="{generate_page_url(url_map['季節の和菓子'])}">
                    <img src="{base_url}/imadake_img3s_{date_suffix}.png" alt="季節の和菓子" class="w100">
                </a>
            </p>
        </div>
    """

def generate_common_html(base_url, date_suffix, original_urls):
    """PC/SP共通のHTMLコードを生成する関数"""
    # URLをカテゴリごとにマッピング
    url_map = map_urls_by_category(original_urls)
    if not url_map:
        st.error("URLのマッピングに失敗しました。")
        st.stop()
        return None

    return f"""
        <p class="imadake_main">
            <img src="{base_url}/imadake_img1_{date_suffix}.png" alt="今だけ、ここだけ" class="fade-img">
            <img src="{base_url}/imadake_img2_{date_suffix}.png" alt="今だけ、ここだけ" class="fade-img">
            <img src="{base_url}/imadake_img3_{date_suffix}.png" alt="今だけ、ここだけ" class="fade-img">
        </p>
        <div class="imadake_right_container">
            <p class="imadake_right">
                <a href="{generate_page_url(url_map['名物'])}">
                    <img src="{base_url}/imadake_img1s_{date_suffix}.png" alt="名物" class="w100">
                </a>
            </p>
            <p class="imadake_right">
                <a href="{generate_page_url(url_map['獲れたて'])}">
                    <img src="{base_url}/imadake_img2s_{date_suffix}.png" alt="獲れたて" class="w100">
                </a>
            </p>
            <p class="imadake_right">
                <a href="{generate_page_url(url_map['季節の和菓子'])}">
                    <img src="{base_url}/imadake_img3s_{date_suffix}.png" alt="季節の和菓子" class="w100">
                </a>
            </p>
        </div>
    """

# 3. メインの処理部分
if st.button("生成"):
    valid_urls = []
    for url in image_urls:
        url = url.strip()
        if url.lower().endswith((".jpg", ".jpeg", ".png")):  # .jpegを追加し、大文字小文字を区別しないように
            valid_urls.append(url)
        else:
            st.error("URL形式を確認してください（.jpg、.jpeg、または.png形式のみ）")
            st.stop()

    if len(valid_urls) != 3:
        st.error("画像URLは3つ入力してください")
        st.stop()

    # generated_page_urlsをより早い段階で生成
    generated_page_urls = [generate_page_url(url) for url in valid_urls]

    results_ext = []  # detailExtTxtの内容を格納するリスト
    results_txt = []  # detailTxtの内容を格納するリスト
    for page_url in generated_page_urls:
        if not page_url:
            st.error(f"URL解析エラー")
            st.stop()

        description_ext = fetch_description_ext(page_url)
        description_txt = fetch_description_txt(page_url)
        results_ext.append(description_ext)
        results_txt.append(description_txt)

    # プロンプトの元となる文章を定義
    base_prompt = """
# ネット通販サイトのバナー用コピー作成プロンプト

---

## 🔧【共通前提：文字数カウントルール】

本プロンプトでは、文字数は以下のルールに従ってカウントしてください：

- 改行（\\n）および行頭・行末のスペースはカウントしない。
- 単語間に必要な半角スペースがある場合、それは1文字としてカウント。
- それ以外のスペース・改行はすべて無視した上で文字数を算出する。
- Pythonにおける以下の処理に基づいた文字数制限を厳守すること：

```python
import re
processed_text = input_text.replace('\\n', '')
processed_text = re.sub(r'(?<=\\S) (?=\\S)', '∴', processed_text)
processed_text = processed_text.replace(' ', '')
processed_text = processed_text.replace('∴', ' ')
len(processed_text)
```

※生成したデータを出力する際、文字数チェックにおいて1行でも【条件】を満たしていない行がある場合、その案全体を破棄し、条件をすべて満たすまで再生成を繰り返してください。必ず**すべての行が指定の文字数範囲内に収まること**を厳守してください。

---

## ✍️【プロンプト指示】

あなたは、バナー画像に掲示するキャッチコピーを考える**プロのコピーライター**です。
以下の【条件】および【大前提】を厳守し、*大バナー** および **横長バナー** に掲載するキャッチコピーを考案してください。
**職人のこだわり・商品の背景・魅力** を丁寧に表現し、**読者の心を動かす文章**を目指してください。

---

## ■ 作成する内容

以下の形式で、それぞれ **3案ずつ** 作成してください。

---

### 【１】大バナー用キャッチコピー（商品画像の右・左に表示）

-両側とも **日本語全角15〜20文字以内**
- 右側と左側、それぞれ「◯◯◯◯◯、◯◯◯◯◯」のように、「言葉 + 句読点 + 言葉」のレイアウトにする
- 真ん中の句読点を挟んで、両側の文字数は同程度にしてバランスを大切にする
- 「強調したいキーワード」は **ダブルクォーテーション（例:"手づくり"）**で囲み、句読点を挟んで両側の言葉にそれぞれ含める
- 商品の魅力が左右に分散しないよう、それぞれ異なる角度の訴求
    ┗ 例：
        右側キャッチコピー:"唸る"ほどの旨味、"濃厚"なイカのコク
        左側キャッチコピー：頑固"かあちゃん"の、こだわり"無添加"塩辛
        画像イメージURL：https://gigaplus.makeshop.jp/wazawaza/top/imadake/imadake_img1_20251016.png

#### 出力形式：

＃大バナー
(第1案)
・右側キャッチコピー：
・左側キャッチコピー：

(第2案)
・右側キャッチコピー：
・左側キャッチコピー：

(第3案)
・右側キャッチコピー：
・左側キャッチコピー：

---

### 【２】横長バナー用テキスト（2行構成）

- **1行目：「商品名」**
   ┗ 日本語全角8〜12文字以内、カッコや数量は不可、産地名は可

- **2行目：「〆切・お届け」などの購入促進ワード**
    ┗ 説明文の最後のカッコ内にある情報を元に
    ┗ 情報がない場合は、「揚げたての美味しさをお届け」など短いキャッチコピーで可

#### 出力形式：

＃横長バナー
(第1案)
-1行目：
-2行目：

(第2案)
-1行目：
-2行目：

(第3案)
-1行目：
-2行目：

---

## ■ 共通の表現ルール

✅ 条件1：表現・トーン
- 商品の魅力が具体的に伝わる表現を使用してください。
- 「！」（感嘆符）は使用しないでください。落ち着きと信頼感を意識してください。
- 抽象的な表現（例：絶品・至高・格別）は避け、**具体的な特徴やこだわり**を記載してください。
- 詩的すぎる表現ではなく、テンポよく自然な語り口にしてください。

✅ 条件2：語句の使用制限
- 「名店」「数量限定」などの語句は、説明文に記載がある場合のみ使用可能。
- 「食卓」「家庭」「自宅」「ご賞味ください」は**一切使用禁止です。**
- 以下の意図を持つ、気取った表現や実態から離れた表現の使用を禁止します。
  - 過度に詩的・抽象的な表現: 例「記憶に刻まれる一皿」など、感傷に寄りすぎた言葉。
  - 大げさな表現: 例「奇跡の逸品」など、商品の実態以上に飾り立てた言葉。
  - 格好つけた表現: 例「本物だけが知る領域へ」など、狙いすぎたキャッチコピー。
  - 既存の禁止リストにある以下に類する表現も同様に禁止です：
  - 「忘れられない味を。」
  - 「本当に美味しい〇〇を食べていますか。」
  - 「季節の便りをお届けします」
  - 「その信念の結晶ともいえる〇〇です。」
  - 「数字で示された品質をご堪能ください。」

✅ 条件3：読者層
- 読者は「50・60代以上の新聞読者層」、および「医師や経営者などのリピーター顧客層」です。

---

## 🧱【大前提】

- **【最重要】商品説明文に記載されていない情報の推察・創作は一切禁止します。すべての表現は、提供された説明文の事実に厳密に基づいている必要があります。意味の変わらない同義語への置換は許可しますが、推察による新たな情報の追加は禁止します。**
- **「お店売り」ではなく「職人売り」を基本**としてください。
  - （例：◯◯で話題のお店 → ❌ ／ ◯◯職人の丁寧な手仕事 → ⭕）
- 商品は、**地元で愛される逸品**または**まだ知られていないおすすめ商品**です。
- 職人のこだわりや他とは違う特徴を、**必ず具体的に**盛り込んでください。
- 締めの文に「○○の味をお楽しみください」などを使用する場合は、**商品固有の特徴を必ず記述**してください。
- 商品の魅力や背景が伝わる、**特別感のある表現**を心がけてください。
- **詩的すぎず・テンポがよく・リズムが心地よい日本語表現**
- **抽象的なワード（例：絶品、格別など）を避け、具体的な魅力で伝える**
- **事実にない日付やお届け時期の記載は厳禁**

---


それでは下記に各商品の説明文を共有します。
----------

１商品目の説明文は以下のとおりです。

＊＊＊＊＊＊＊
「＃＃＃」

--------

２商品目の説明文は以下のとおりです。

＊＊＊＊＊＊＊
「＃＃＃」

--------

３商品目の説明文は以下のとおりです。

＊＊＊＊＊＊＊
「＃＃＃」
    """;

    # URLの種類に応じてプロンプトを生成
    if any('/shopbrand/ct' in url for url in generated_page_urls):
        base_prompt = """
# ネット通販サイトのバナー用コピー作成プロンプト

商品それぞれの **大バナー** および **横長バナー** に掲載する **感情に訴えるキャッチコピー** を考案してください。
**職人のこだわり・商品の背景・魅力** を丁寧に表現し、**読者の心を動かす文章**を目指してください。

---

## ■ 作成する内容

以下の形式で、それぞれ **3案ずつ** 作成してください。

---

### 【１】大バナー用キャッチコピー（商品画像の右・左に表示）

- 右側キャッチコピー：**30〜40文字以内**
- 左側キャッチコピー：**15〜20文字以内**
- 「強調したいキーワード」は **ダブルクォーテーション（例:"手づくり"）で囲む**
- 自然な日本語での組み合わせにする
- 商品の魅力が左右に分散しないよう、それぞれ異なる角度の訴求で

#### 出力形式：

＃大バナー
(第1案)
・右側キャッチコピー：
・左側キャッチコピー：

(第2案)
・右側キャッチコピー：
・左側キャッチコピー：

(第3案)
・右側キャッチコピー：
・左側キャッチコピー：

---

### 【２】横長バナー用テキスト（2行構成）

- **1行目：「商品名」**
　┗ 10〜15文字以内、カッコや数量なし、産地名は可

- **2行目：「〆切・お届け」などの購入促進ワード**
　┗ 説明文の最後のカッコ内にある情報を元に
　┗ 情報がない場合は、「揚げたての美味しさをお届け」など短いキャッチコピーで可

#### 出力形式：

＃横長バナー
(第1案)
-1行目：
-2行目：

(第2案)
-1行目：
-2行目：

(第3案)
-1行目：
-2行目：

---

## ■ 共通の表現ルール

- **感情に訴える表現（エモーショナル）を必ず使用**
　┗ 修辞技法（比喩・反復・体言止めなど）も使用可

- **詩的すぎず・テンポがよく・リズムが心地よい日本語表現**

- **抽象的なワード（例：絶品、格別など）を避け、具体的な魅力で伝える**

- **「お店売り」ではなく「職人売り」の視点を徹底**
　┗ ×「有名店の味」 → ◎「◯◯職人の丹精込めた手しごと」

- **事実にない日付やお届け時期の記載は厳禁**

---


それでは下記に各商品の説明文を共有します。
----------

１商品目の説明文は以下のとおりです。

＊＊＊＊＊＊＊
「＃＃＃」

--------

２商品目の説明文は以下のとおりです。

＊＊＊＊＊＊＊
「＃＃＃」

--------

３商品目の説明文は以下のとおりです。

＊＊＊＊＊＊＊
「＃＃＃」
        """;

    # 説明文を挿入する部分を修正
    for i, (description_ext, description_txt) in enumerate(zip(results_ext, results_txt)):
        placeholder_ext = "＊＊＊＊＊＊＊"
        placeholder_txt = "「＃＃＃」"

        # カテゴリーページかどうかを個別に判定
        if '/shopbrand/ct' in generated_page_urls[i]:
            message = f"以下のURLのclass=\"M_categoryImage\"内にある画像の内容を参照してください\n{generated_page_urls[i]}"
            base_prompt = base_prompt.replace(placeholder_ext, message, 1)
            # カテゴリーページの場合は「＃＃＃」を削除
            base_prompt = base_prompt.replace(placeholder_txt, "", 1)
        else:
            # 通常ページの場合
            base_prompt = base_prompt.replace(placeholder_ext, description_ext, 1)
            base_prompt = base_prompt.replace(placeholder_txt, f"「{description_txt}」" if description_txt else "", 1)

    # 生成されたプロンプト
    st.subheader("生成されたプロンプト")

    # プロンプトコピー機能
    js_base_prompt = base_prompt.replace('`', '\`').replace('\\', '\\\\').replace('\n', '\\n')
    prompt_copy_html = f"""
    <script>
        function copyPrompt() {{
            var text = `{js_base_prompt}`;
            navigator.clipboard.writeText(text).then(function() {{
                alert('プロンプトをコピーしました！');
            }}, function(err) {{
                console.error('コピーに失敗しました', err);
                alert('コピーに失敗しました。');
            }});
        }}
    </script>
    <button onclick="copyPrompt()">プロンプトをコピー</button>
    """
    st.components.v1.html(prompt_copy_html, height=280)

    # ページURLの出力とコピー用ボタン
    st.subheader("生成されたページURL")
    generated_page_urls = [generate_page_url(url) for url in valid_urls]

    for i, page_url in enumerate(generated_page_urls, start=1):
        js_safe_page_url = page_url.replace('`', '\`').replace('\\', '\\\\').replace('\n', '\\n')
        url_copy_html = f"""
        <style>
            #url_area_{i} {{
                display: none;
            }}
            .url-container {{
                display: flex;
                align-items: center;
                gap: 10px; /* 要素間の間隔を設定 */
                width: 100%;
                overflow: hidden;
            }}
            .url-number {{
                flex: 0 0 auto; /* 幅を固定 */
                white-space: nowrap;
            }}
            .url-link {{
                flex: 1; /* 残りのスペースを全て使用 */
                text-align: left; /* 左揃え */
                overflow: hidden;
                text-overflow: ellipsis;
            }}
            .url-button {{
                flex: 0 0 auto; /* 幅を固定 */
            }}
        </style>
        <div class="url-container">
            <span class="url-number">商品 {i}:</span>
            <span class="url-link"><a href='{page_url}' target='_blank'>{page_url}</a></span>
            <span class="url-button">
                <button onclick="copyUrlToClipboard_{i}()">URLをコピー</button>
            </span>
        </div>
        <textarea id="url_area_{i}">{page_url}</textarea>
        <script>
            function copyUrlToClipboard_{i}() {{
                var text = `{js_safe_page_url}`;
                navigator.clipboard.writeText(text).then(function() {{
                    alert('URLをコピーしました！');
                }}, function(err) {{
                    console.error('コピーに失敗しました', err);
                    alert('コピーに失敗しました。');
                }});
            }}
        </script>
        """
        st.components.v1.html(url_copy_html, height=60)

    # HTMLコードの生成と保存
    template_dir = '/Users/akiakko0526/Library/Mobile Documents/com~apple~CloudDocs/47_CLUB_メルマガマニュアル/元データ_今だけ、ここだけ/template'

    # テンプレートファイルの存在確認 - ファイル名を修正
    pc_template_path = f"{template_dir}/template_imadake_pc.html"
    sp_template_path = f"{template_dir}/template_imadake_sp.html"

    if not os.path.exists(template_dir):
        st.error(f"テンプレートディレクトリが見つかりません: {template_dir}")
        st.stop()

    if not os.path.exists(pc_template_path):
        st.error(f"PCテンプレートファイルが見つかりません: {pc_template_path}")
        st.stop()

    if not os.path.exists(sp_template_path):
        st.error(f"SPテンプレートファイルが見つかりません: {sp_template_path}")
        st.stop()

    try:
        # 選択された日付から年と月を抽出
        date_parts = selected_date_range.split()
        year_month = date_parts[0]  # "2025年06月" の形式
        year = year_month[:4]  # 最初の4文字（年）
        month = year_month[5:7]  # 6-7文字目（月）

        # ファイル名の生成
        if "1日〜15日" in selected_date_range:
            file_date = f"{year}{month}01-15"
        else:
            file_date = f"{year}{month}16-30"

        pc_filename = f"{file_date}_imadake_pc.html"
        # sp_filename = f"{file_date}_imadake_sp.html"
        sp_filename = f"{file_date}_imadake_PC-SP共通.html"


        # 画像のベースURL
        base_url = "https://gigaplus.makeshop.jp/wazawaza/top/imadake"
        date_suffix = f"{year}{month}{'01' if '1日〜15日' in selected_date_range else '16'}"

        generated_html = generate_pc_html(base_url, date_suffix, valid_urls)

        # # PCテンプレートの読み込みと生成
        # with open(pc_template_path, 'r', encoding='utf-8') as f:
        #     pc_template = f.read()

        # generated_pc = pc_template.replace('<!-- コード生成位置 -->', generated_html)

        # # PCファイルの保存（ファイル名の重複チェック）
        # pc_output_path = f"{template_dir}/{pc_filename}"
        # pc_output_path = get_unique_filename(pc_output_path)
        # with open(pc_output_path, 'w', encoding='utf-8') as f:
        #     f.write(generated_pc)

        # SPテンプレートの読み込みと生成
        with open(sp_template_path, 'r', encoding='utf-8') as f:
            sp_template = f.read()

        generated_sp = sp_template.replace('<!-- コード生成位置 -->', generate_sp_html(base_url, date_suffix, generated_page_urls, valid_urls))

        # SPファイルの保存（ファイル名の重複チェック）
        sp_output_path = f"{template_dir}/{sp_filename}"
        sp_output_path = get_unique_filename(sp_output_path)
        with open(sp_output_path, 'w', encoding='utf-8') as f:
            f.write(generated_sp)

        # 保存完了メッセージ（SP版のみ表示）
        st.success(f"""
        HTMLファイルを保存しました：
        - PC-SP共通: {os.path.basename(sp_output_path)}
        """
        )

    except Exception as e:
        st.error(f"ファイル処理エラー: {str(e)}")
        st.stop()
