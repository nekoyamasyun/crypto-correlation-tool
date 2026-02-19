import streamlit as st
import ccxt
import pandas as pd
import numpy as np
import time
import requests
from scipy.stats import linregress

# ==========================================
# 🎨 ページ設定 & 視認性特化型ダークUI
# ==========================================
st.set_page_config(
    page_title="Antigravity: 相関両建てスキャナー",
    page_icon="⚔️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CSS Magic ---
st.markdown("""
<style>
    /* 全体の背景 */
    .stApp { background: linear-gradient(135deg, #0b0f19 0%, #111625 100%); color: #FFFFFF; }
    
    /* テキスト基本色（強制ホワイト・最強版） */
    h1, h2, h3, h4, h5, h6, p, label, span, div, li, small { color: #FFFFFF !important; }
    
    /* サイドバーの説明文（Caption）も強制的に白くする */
    .stCaption, div[data-testid="stCaptionContainer"] p, .stMarkdown p { 
        color: #FFFFFF !important; 
        opacity: 1 !important; 
        font-size: 0.95em;
        text-shadow: 0px 0px 3px rgba(0,0,0,0.8); /* 背景と同化しないよう影を強化 */
    }
    
    /* ドロップダウン選択後の文字色を黒に（ここだけ例外） */
    div[data-baseweb="select"] div { color: #000000 !important; font-weight: bold; }
    div[data-baseweb="popover"] div, div[data-baseweb="menu"] li { color: #000000 !important; }

    /* サイドバー */
    section[data-testid="stSidebar"] { background-color: rgba(20, 25, 40, 0.98); border-right: 1px solid rgba(255, 255, 255, 0.15); }
    
    /* タイトル */
    h1 {
        background: linear-gradient(90deg, #4facfe 0%, #00f2fe 100%);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        font-weight: 800 !important; letter-spacing: 2px; text-shadow: 0 0 20px rgba(0, 242, 255, 0.3);
    }
    
    /* ボタン */
    div.stButton > button {
        background: linear-gradient(90deg, #00C9FF 0%, #92FE9D 100%);
        color: #000000 !important; border: none; border-radius: 8px;
        font-weight: 900; font-size: 1.2rem; text-transform: uppercase; letter-spacing: 1px;
        box-shadow: 0 0 15px rgba(0, 201, 255, 0.5);
    }
    div.stButton > button:hover {
        transform: translateY(-2px); box-shadow: 0 0 25px rgba(0, 201, 255, 0.8); color: #000000 !important;
    }
    
    /* SurfAIボタン */
    .surf-button {
        display: inline-block; background: linear-gradient(45deg, #FF512F 0%, #DD2476 100%);
        color: white !important; padding: 12px 24px; border-radius: 50px; text-decoration: none;
        font-weight: bold; box-shadow: 0 4px 15px rgba(221, 36, 118, 0.4); border: 1px solid rgba(255,255,255,0.5);
    }
    
    /* データテーブル */
    div[data-testid="stDataFrame"] {
        background-color: rgba(255, 255, 255, 0.05); border: 1px solid rgba(255, 255, 255, 0.2); border-radius: 8px;
    }
    
    /* ロジック説明ボックス */
    .logic-box {
        background-color: rgba(255, 255, 255, 0.05);
        border-left: 5px solid #00F2FF;
        padding: 15px;
        margin: 20px 0;
        border-radius: 5px;
    }
</style>
""", unsafe_allow_html=True)

st.title("⚔️ ANTIGRAVITY")
st.markdown("### QUANTITATIVE CORRELATION SCANNER")

# --- ロジック開示エリア ---
with st.expander("ℹ️ このデータの抽出・計算ロジックについて（クリックで展開）"):
    st.markdown("""
    <div class="logic-box">
        <h4>🛠️ アルゴリズムの仕組み</h4>
        <ol>
            <li><b>市場データの取得</b>: CoinGeckoのデータベースから、指定されたセクター（AI, Memeなど）に属する銘柄リストを取得します。</li>
            <li><b>クロスチェック</b>: 取得した銘柄のうち、世界最大の流動性を誇る <b>Binance</b> で現物取引可能な銘柄のみを厳選します。</li>
            <li><b>時系列分析</b>: 過去のローソク足データを取得し、以下の指標を計算します。
                <ul>
                    <li><b>相関係数 (Correlation)</b>: 銘柄同士の価格連動性（0.6以上で「同族」とみなす）。</li>
                    <li><b>Zスコア (Z-Score)</b>: 現在の価格差（レシオ）が、平均からどれだけ乖離しているか（標準偏差）。</li>
                    <li><b>スロープ (Slope)</b>: レシオチャートの傾き。ショート側が相対的に弱くなっているトレンドを検出。</li>
                </ul>
            </li>
        </ol>
        ※本ツールはAPIを通じてリアルタイム（または直近）の確定足データを取得・計算しています。
    </div>
    """, unsafe_allow_html=True)

st.warning("""
【重要】 このツールの勝率や指標は過去データに基づく概算値です。
ポジションを取る際は、必ずリアルタイムでの個別分析を行ってください。
より高精度なAI分析が必要な場合は、以下の SurfAI を推奨します。
""")
st.markdown("""
<div style="text-align: center; margin: 20px 0;">
    <a href="https://asksurf.ai/?r=0AJI90QG40KZ" target="_blank" class="surf-button">
        🚀 SurfAI でプロ級の分析を行う (asksurf.ai)
    </a>
</div>
""", unsafe_allow_html=True)
st.markdown("---")

# ==========================================
# ⚙️ サイドバー (説明付き)
# ==========================================
st.sidebar.header("⚙️ SYSTEM CONFIG")

st.sidebar.markdown("### 1. SCOPE (範囲)")
st.sidebar.caption("市場のどの範囲を探索するか設定します。")

TOP_MCAP = st.sidebar.slider(
    "時価総額上位 (Top N)", 50, 500, 200, step=50,
    help="例: 「200」にすると、時価総額ランキング1位〜200位の主要銘柄のみを分析対象にします。"
)

TIMEFRAME = st.sidebar.selectbox(
    "足種 (Timeframe)", ['1d (日足)', '4h (4時間足)', '1h (1時間足)'], index=0,
    help="どの期間のローソク足で分析するか選びます。大きなトレンドを見るなら「日足」、短期なら「1時間足」がおすすめです。"
)
TIMEFRAME_MAP = {'1d (日足)': '1d', '4h (4時間足)': '4h', '1h (1時間足)': '1h'}
SELECTED_TIMEFRAME = TIMEFRAME_MAP[TIMEFRAME]

LIMIT = st.sidebar.slider(
    "分析期間 (Candles)", 30, 365, 90,
    help="過去何本分のローソク足を使って計算するか設定します。推奨は90本です。"
)

st.sidebar.markdown("### 2. SECTORS (セクター)")
st.sidebar.caption("互いに同じジャンルのトークンを選ぶことで相関性を高め、より安定的な勝率を狙います。")

SECTOR_MAP = {
    'ミームコイン (Meme)': 'meme-token', 'レイヤー1 (L1)': 'layer-1', 'AI (人工知能)': 'artificial-intelligence',
    'ゲーム (GameFi)': 'gaming', 'DeFi (分散型金融)': 'decentralized-finance-defi',
    'Solanaエコシステム': 'solana-ecosystem', 'Ethereumエコシステム': 'ethereum-ecosystem',
    'RWA (現実資産)': 'real-world-assets-rwa', 'メタバース': 'metaverse', 'ストレージ': 'storage'
}
SECTOR_MODE = st.sidebar.radio("モード選択", ["全て対象 (Full Scan)", "個別選択 (Manual)"])

if SECTOR_MODE == "全て対象 (Full Scan)":
    TARGET_CATEGORIES = list(SECTOR_MAP.values())
else:
    DEFAULT_SELECTIONS = ['ミームコイン (Meme)', 'レイヤー1 (L1)', 'AI (人工知能)']
    SELECTED_SECTORS_JP = st.sidebar.multiselect(
        "対象セクター", list(SECTOR_MAP.keys()), default=DEFAULT_SELECTIONS,
        help="ここで選んだセクターの中でペアを探します。"
    )
    TARGET_CATEGORIES = [SECTOR_MAP[jp] for jp in SELECTED_SECTORS_JP]

st.sidebar.markdown("### 3. FILTERS (条件)")
st.sidebar.caption("抽出するペアの厳しさを設定します。")

KINGS = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'BNB/USDT']
FIXED_LONGS = st.sidebar.multiselect(
    "👑 ロング固定銘柄 (Optional)", options=KINGS, default=[],
    help="これを選択すると、「買い」側が必ず選択した銘柄（例: BTC）になります。堅実なトレード向け。"
)

st.sidebar.markdown("---")
st.sidebar.caption("📊 **相関 (Correlation)**: 銘柄同士の「仲良し度」です。0.6を下回ると連動性が薄れ、両建てのリスクヘッジ効果が弱まります。")
CORR_THRESHOLD = st.sidebar.slider(
    "Min Correlation", 0.0, 1.0, 0.60, step=0.05
)

# --- ★ Zスコア説明の修正箇所 ---
st.sidebar.caption("""
📏 **乖離 (Z-Score)**: 平均値からの距離（絶対値）です。
* **狙い目**: **±2.0以上**（絶対値）が推奨です。
* **意味**: **「+2.0以上（上がりすぎ）」** または **「-2.0以下（下がりすぎ）」** の状態です。統計的に約95%の確率で起きない異常事態です。
* **期待値**: ゴムが上下どちらかに限界まで伸び切っているため、**「平均値に戻ろうとする力（リバウンド）」** が発生します。その歪みを狙います。
""")
Z_SCORE_ENTRY = st.sidebar.slider(
    "Min Z-Score (絶対値)", 0.0, 5.0, 1.5, step=0.1
)

st.sidebar.caption("""
🏆 **勝率 (Win Rate)**
**「分析期間中、日足ベースでロング側が勝った日の割合」**です。
例：勝率60%＝期間中の6割の日数は、持っているだけで含み益が増えたことを意味します。構造的な強さの指標です。
""")
MIN_WIN_RATE = st.sidebar.slider(
    "Min Win Rate (%)", 0.0, 100.0, 55.0, step=1.0
) / 100.0

# ==========================================
# 🧠 分析ロジック
# ==========================================

@st.cache_data(ttl=3600)
def get_coingecko_data(limit, categories):
    url = "https://api.coingecko.com/api/v3/coins/markets"
    symbol_categories = {}
    try:
        p_market = {'vs_currency': 'usd', 'order': 'market_cap_desc', 'per_page': limit, 'page': 1, 'sparkline': 'false'}
        resp = requests.get(url, params=p_market, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        top_symbols = [item['symbol'].upper() for item in data]
        for sym in top_symbols: symbol_categories[sym] = set()

        bar = st.progress(0, text="Initializing Sector Data...")
        for i, cat in enumerate(categories):
            cat_name = [k for k,v in SECTOR_MAP.items() if v == cat][0] if cat in SECTOR_MAP.values() else cat
            bar.progress((i+1)/len(categories), text=f"Scanning Sector: {cat_name}")
            p_cat = {'vs_currency': 'usd', 'category': cat, 'order': 'market_cap_desc', 'per_page': 100, 'page': 1, 'sparkline': 'false'}
            try:
                c_resp = requests.get(url, params=p_cat, timeout=10)
                if c_resp.status_code == 200:
                    for item in c_resp.json():
                        s = item['symbol'].upper()
                        if s in symbol_categories: symbol_categories[s].add(cat)
                time.sleep(1.2)
            except: pass
        bar.empty()
        return top_symbols, symbol_categories
    except Exception as e:
        st.error(f"Data Error: {e}")
        return [], {}

@st.cache_data(ttl=3600)
def filter_binance_symbols(cg_symbols):
    exchange = ccxt.binance()
    try: markets = exchange.load_markets()
    except: return []
    target = []
    for k in KINGS: 
        if k not in target: target.append(k)
    for sym in cg_symbols:
        bsym = f"{sym}/USDT"
        if bsym in markets and bsym not in target: target.append(bsym)
    return target

@st.cache_data(ttl=600)
def fetch_ohlcv_data(symbols, timeframe, limit):
    exchange = ccxt.binance()
    df_dict = {}
    bar = st.progress(0, text="Fetching Market Data...")
    for i, sym in enumerate(symbols):
        try:
            ohlcv = exchange.fetch_ohlcv(sym, timeframe=timeframe, limit=limit)
            closes = [x[4] for x in ohlcv]
            if len(closes) == limit: df_dict[sym] = closes
            time.sleep(0.05)
        except: pass
        if i % 10 == 0: bar.progress((i+1)/len(symbols), text=f"Processing: {sym}")
    bar.empty()
    return pd.DataFrame(df_dict)

def calculate_slope_winrate(series):
    # 下落トレンド(Short/Longが下がる)が勝ち
    slope, _, _, _, _ = linregress(np.arange(len(series)), series)
    pct = series.pct_change().dropna()
    # レシオが下がった日(pct < 0)の割合
    win = len(pct[pct < 0]) / len(pct) if len(pct) > 0 else 0
    return slope, win

# --- メイン実行ボタン ---
if st.button("最良の相関ペアを分析🎯", type="primary"):
    
    with st.spinner('Accessing Neural Database...'):
        cg_symbols, cats_map = get_coingecko_data(TOP_MCAP, TARGET_CATEGORIES)
    
    if cg_symbols:
        target_symbols = filter_binance_symbols(cg_symbols)
        st.success(f"Target Acquired: {len(target_symbols)} Assets")
        df = fetch_ohlcv_data(target_symbols, SELECTED_TIMEFRAME, LIMIT)
        
        results = []
        cols = df.columns
        with st.spinner('Computing Correlations & Alpha...'):
            for i in range(len(cols)):
                for j in range(len(cols)):
                    s1, s2 = cols[i], cols[j]
                    if s1 == s2: continue

                    if FIXED_LONGS and (s1 not in FIXED_LONGS): continue
                    
                    c1 = cats_map.get(s1.split('/')[0], set())
                    c2 = cats_map.get(s2.split('/')[0], set())
                    common = c1.intersection(c2)
                    if not common: continue
                    
                    corr = df[s1].corr(df[s2])
                    if corr < CORR_THRESHOLD: continue
                    
                    # Ratio = Short / Long
                    ratio = df[s2] / df[s1]
                    
                    z = (ratio.iloc[-1] - ratio.mean()) / ratio.std()
                    if pd.isna(z) or abs(z) < Z_SCORE_ENTRY: continue
                    
                    slope, win = calculate_slope_winrate(ratio)
                    
                    # Slopeは「0以下（右肩下がり）」が良い
                    if slope >= 0 or win < MIN_WIN_RATE: continue
                    
                    norm_slope = (slope / ratio.mean()) * 100

                    cat_disp = [k for k,v in SECTOR_MAP.items() if v == list(common)[0]]
                    results.append({
                        'Long': s1, 'Short': s2,
                        'Sector': cat_disp[0] if cat_disp else list(common)[0],
                        'WinRate': win * 100, 
                        'Corr': corr, 
                        'Z-Score': z, 
                        'Slope': norm_slope
                    })
        
        if results:
            res_df = pd.DataFrame(results)
            res_df = res_df.sort_values(by=['Slope'], ascending=[True])
            
            st.balloons()
            st.markdown(f"### 🎯 {len(res_df)} OPPORTUNITIES FOUND")
            
            # データの見方（ソフト表現版）
            st.markdown("""
            <div class="info-box">
                <div class="info-title">💡 データの見方：右肩下がり (Short ÷ Long) が優位性のカギ</div>
                <ul>
                    <li>
                        <b>Slope (下落トレンド)</b>: <b>マイナスの数値が大きいほど、ショート側が相対的に弱い状態です。</b>
                        <ul>
                            <li>レシオチャート（Short ÷ Long）が右肩下がりであることは、構造的に有利なポジションであることを示唆します。</li>
                            <li>Slopeがマイナスであれば、時間の経過とともにポジションが有利になりやすい傾向があります。</li>
                        </ul>
                    </li>
                    <li>
                        <b>乖離 (Z-Score)</b>: 平均値からの乖離度合い。
                        <ul>
                            <li><b>プラスの場合</b>: ショート側の価格が一時的に上昇（割高）している状態。統計的に平均回帰（リバウンド）の期待値が生じる局面です。</li>
                            <li><b>マイナスの場合</b>: すでに大きく下落している状態。トレンドフォローの検討材料となります。</li>
                        </ul>
                    </li>
                    <li><b>勝率</b>: 期間中にレシオが下落した（ロング側が強かった）日の割合です。</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)
            
            st.dataframe(
                res_df,
                column_config={
                    "Long": st.column_config.TextColumn("買い (Long)", help="Buy this asset"),
                    "Short": st.column_config.TextColumn("売り (Short)", help="Sell this asset"),
                    "Sector": "セクター",
                    "WinRate": st.column_config.ProgressColumn("勝率 (Win%)", format="%.1f%%", min_value=0, max_value=100),
                    "Corr": st.column_config.ProgressColumn("相関 (Corr)", format="%.3f", min_value=0, max_value=1),
                    "Z-Score": st.column_config.NumberColumn("乖離 (Z)", format="%.2f"),
                    "Slope": st.column_config.NumberColumn("Slope (下落トレンド)", format="%.4f", help="マイナスが大きいほど、ショート側が弱い傾向にあります"),
                },
                use_container_width=True,
                height=800
            )
        else:
            st.error("No pairs found. Try relaxing the filters.")