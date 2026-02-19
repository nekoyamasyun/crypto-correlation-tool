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
    
    /* テキスト基本色（強制ホワイト） */
    h1, h2, h3, h4, h5, h6, p, label, span, div, li, small { color: #FFFFFF !important; }
    
    /* ドロップダウン選択後の文字色を黒に */
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
    
    /* SurfAIボタン */
    .surf-button {
        display: inline-block; background: linear-gradient(45deg, #FF512F 0%, #DD2476 100%);
        color: white !important; padding: 12px 24px; border-radius: 50px; text-decoration: none;
        font-weight: bold; box-shadow: 0 4px 15px rgba(221, 36, 118, 0.4); border: 1px solid rgba(255,255,255,0.5);
    }
</style>
""", unsafe_allow_html=True)

st.title("⚔️ ANTIGRAVITY")
st.markdown("### QUANTITATIVE CORRELATION SCANNER")

# --- ロジック開示エリア ---
with st.expander("ℹ️ このデータの抽出・計算ロジックについて（クリックで展開）"):
    st.markdown("""
    <div style="background-color: rgba(255, 255, 255, 0.05); border-left: 5px solid #00F2FF; padding: 15px; border-radius: 5px;">
        <h4>🛠️ アルゴリズムの仕組み</h4>
        <ol>
            <li><b>市場データの取得</b>: CoinGecko API(Demo Key使用)から指定セクターの銘柄リストを取得します。</li>
            <li><b>クロスチェック</b>: 取得した銘柄のうち <b>MEXC</b> で取引可能な銘柄のみを厳選します。</li>
            <li><b>時系列分析</b>: 相関係数、Zスコア、Slope(トレンド)をリアルタイム計算します。</li>
        </ol>
    </div>
    """, unsafe_allow_html=True)

st.markdown("""
<div style="text-align: center; margin: 20px 0;">
    <a href="https://asksurf.ai/?r=0AJI90QG40KZ" target="_blank" class="surf-button">
        🚀 SurfAI でプロ級の分析を行う (asksurf.ai)
    </a>
</div>
""", unsafe_allow_html=True)

# ==========================================
# ⚙️ サイドバー
# ==========================================
st.sidebar.header("⚙️ SYSTEM CONFIG")
TOP_MCAP = st.sidebar.slider("時価総額上位 (Top N)", 50, 500, 200, step=50)
TIMEFRAME = st.sidebar.selectbox("足種 (Timeframe)", ['1d (日足)', '4h (4時間足)', '1h (1時間足)'], index=0)
TIMEFRAME_MAP = {'1d (日足)': '1d', '4h (4時間足)': '4h', '1h (1時間足)': '1h'}
SELECTED_TIMEFRAME = TIMEFRAME_MAP[TIMEFRAME]
LIMIT = st.sidebar.slider("分析期間 (Candles)", 30, 365, 90)

SECTOR_MAP = {
    'ミームコイン (Meme)': 'meme-token', 'レイヤー1 (L1)': 'layer-1', 'AI (人工知能)': 'artificial-intelligence',
    'ゲーム (GameFi)': 'gaming', 'DeFi (分散型金融)': 'decentralized-finance-defi',
    'Solanaエコシステム': 'solana-ecosystem', 'Ethereumエコシステム': 'ethereum-ecosystem',
    'RWA (現実資産)': 'real-world-assets-rwa', 'メタバース': 'metaverse', 'ストレージ': 'storage'
}
SECTOR_MODE = st.sidebar.radio("モード選択", ["全て対象 (Full Scan)", "個別選択 (Manual)"])
TARGET_CATEGORIES = list(SECTOR_MAP.values()) if SECTOR_MODE == "全て対象 (Full Scan)" else [SECTOR_MAP[jp] for jp in st.sidebar.multiselect("対象セクター", list(SECTOR_MAP.keys()), default=['ミームコイン (Meme)', 'レイヤー1 (L1)', 'AI (人工知能)'])]

KINGS = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'BNB/USDT']
FIXED_LONGS = st.sidebar.multiselect("👑 ロング固定銘柄", options=KINGS, default=[])
CORR_THRESHOLD = st.sidebar.slider("Min Correlation", 0.0, 1.0, 0.60, step=0.05)
Z_SCORE_ENTRY = st.sidebar.slider("Min Z-Score (絶対値)", 0.0, 5.0, 1.5, step=0.1)
MIN_WIN_RATE = st.sidebar.slider("Min Win Rate (%)", 0.0, 100.0, 55.0, step=1.0) / 100.0

# ==========================================
# 🧠 分析ロジック (APIキー対応 & MEXC版)
# ==========================================

# 猫山さんの専用APIキー
CG_API_KEY = "CG-eLp3pfiS69mDXdUy4pP9NBHW"

@st.cache_data(ttl=3600)
def get_coingecko_data(limit, categories):
    url = "https://api.coingecko.com/api/v3/coins/markets"
    headers = {"accept": "application/json", "x-cg-demo-api-key": CG_API_KEY}
    symbol_categories = {}
    
    try:
        p_market = {'vs_currency': 'usd', 'order': 'market_cap_desc', 'per_page': limit, 'page': 1}
        resp = requests.get(url, params=p_market, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        top_symbols = [item['symbol'].upper() for item in data]
        for sym in top_symbols: symbol_categories[sym] = set()

        bar = st.progress(0, text="Initializing Sector Data...")
        for i, cat in enumerate(categories):
            cat_name = [k for k,v in SECTOR_MAP.items() if v == cat][0] if cat in SECTOR_MAP.values() else cat
            bar.progress((i+1)/len(categories), text=f"Scanning Sector: {cat_name}")
            p_cat = {'vs_currency': 'usd', 'category': cat, 'order': 'market_cap_desc', 'per_page': 100}
            try:
                c_resp = requests.get(url, params=p_cat, headers=headers, timeout=15)
                if c_resp.status_code == 200:
                    for item in c_resp.json():
                        s = item['symbol'].upper()
                        if s in symbol_categories: symbol_categories[s].add(cat)
                time.sleep(1.5) 
            except: pass
        bar.empty()
        return top_symbols, symbol_categories
    except Exception as e:
        st.error(f"CoinGecko API Error: {e}")
        return [], {}

@st.cache_data(ttl=3600)
def filter_mexc_symbols(cg_symbols):
    exchange = ccxt.mexc() # ← ここをMEXCに変更！
    try: markets = exchange.load_markets()
    except Exception as e: 
        st.error(f"取引所エラー: {e}") 
        return []
    target = []
    for k in KINGS: 
        if k not in target: target.append(k)
    for sym in cg_symbols:
        bsym = f"{sym}/USDT"
        if bsym in markets and bsym not in target: target.append(bsym)
    return target

@st.cache_data(ttl=600)
def fetch_ohlcv_data(symbols, timeframe, limit):
    exchange = ccxt.mexc() # ← ここをMEXCに変更！
    df_dict = {}
    bar = st.progress(0, text="Fetching Market Data...")
    for i, sym in enumerate(symbols):
        try:
            ohlcv = exchange.fetch_ohlcv(sym, timeframe=timeframe, limit=limit)
            closes = [x[4] for x in ohlcv]
            if len(closes) == limit: df_dict[sym] = closes
            time.sleep(0.1) 
        except: pass
        if i % 10 == 0: bar.progress((i+1)/len(symbols), text=f"Processing: {sym}")
    bar.empty()
    return pd.DataFrame(df_dict)

def calculate_slope_winrate(series):
    slope, _, _, _, _ = linregress(np.arange(len(series)), series)
    pct = series.pct_change().dropna()
    win = len(pct[pct < 0]) / len(pct) if len(pct) > 0 else 0
    return slope, win

# --- メイン実行ボタン ---
if st.button("最良の相関ペアを分析🎯", type="primary"):
    with st.spinner('Connecting to CoinGecko via Private Key...'):
        cg_symbols, cats_map = get_coingecko_data(TOP_MCAP, TARGET_CATEGORIES)
        
        if len(cg_symbols) == 0:
            st.cache_data.clear()
    
    if cg_symbols:
        target_symbols = filter_mexc_symbols(cg_symbols) # 関数名を変更
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
                    c1, c2 = cats_map.get(s1.split('/')[0], set()), cats_map.get(s2.split('/')[0], set())
                    common = c1.intersection(c2)
                    if not common: continue
                    corr = df[s1].corr(df[s2])
                    if corr < CORR_THRESHOLD: continue
                    ratio = df[s2] / df[s1]
                    z = (ratio.iloc[-1] - ratio.mean()) / ratio.std()
                    if pd.isna(z) or abs(z) < Z_SCORE_ENTRY: continue
                    slope, win = calculate_slope_winrate(ratio)
                    if slope >= 0 or win < MIN_WIN_RATE: continue
                    norm_slope = (slope / ratio.mean()) * 100
                    cat_disp = [k for k,v in SECTOR_MAP.items() if v == list(common)[0]]
                    results.append({'Long': s1, 'Short': s2, 'Sector': cat_disp[0] if cat_disp else list(common)[0], 'WinRate': win * 100, 'Corr': corr, 'Z-Score': z, 'Slope': norm_slope})
        
        if results:
            res_df = pd.DataFrame(results).sort_values(by=['Slope'], ascending=[True])
            st.balloons()
            st.markdown(f"### 🎯 {len(res_df)} OPPORTUNITIES FOUND")
            st.dataframe(res_df, column_config={
                "WinRate": st.column_config.ProgressColumn("勝率 (Win%)", format="%.1f%%", min_value=0, max_value=100),
                "Corr": st.column_config.ProgressColumn("相関 (Corr)", format="%.3f", min_value=0, max_value=1),
                "Z-Score": st.column_config.NumberColumn("乖離 (Z)", format="%.2f"),
                "Slope": st.column_config.NumberColumn("Slope (下落トレンド)", format="%.4f")
            }, use_container_width=True, height=600)
        else:
            st.error("No pairs found. Try relaxing the filters.")
