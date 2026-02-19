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
        display: inline-block; background: linear-gradient(45deg, #FF512F 0
