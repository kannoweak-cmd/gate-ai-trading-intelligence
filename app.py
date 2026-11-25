import streamlit as st
import pandas as pd
import requests
import numpy as np
from datetime import datetime, timezone

API = "https://api.gateio.ws/api/v4"

st.set_page_config(page_title="Gate AI Trading Intelligence", page_icon="📊", layout="wide")
st.title("📊 GATE AI TRADING INTELLIGENCE")
st.caption("Versi perbaikan • Data publik Gate.io • Mode edukasi dan simulasi, bukan rekomendasi investasi")

st.markdown("""
<style>
.stApp {background: #0b1220; color: #e5e7eb;}
[data-testid="stMetric"] {background: #111c2e; padding: 14px; border-radius: 10px;}
</style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=60, show_spinner=False)
def get_tickers():
    response = requests.get(f"{API}/spot/tickers", timeout=25,
                            headers={"Accept": "application/json", "User-Agent": "GateDashboard/1.1"})
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, list) or not payload:
        raise ValueError("Respons daftar harga dari Gate.io kosong atau formatnya tidak sesuai.")
    df = pd.DataFrame(payload)
    required = ["currency_pair", "last", "change_percentage", "quote_volume"]
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError("Kolom data harga tidak ditemukan: " + ", ".join(missing))
    df["quote_volume_num"] = pd.to_numeric(df["quote_volume"], errors="coerce")
    df["last_num"] = pd.to_numeric(df["last"], errors="coerce")
    df["change_num"] = pd.to_numeric(df["change_percentage"], errors="coerce")
    df = df[df["currency_pair"].astype(str).str.endswith("_USDT")]
    df = df.dropna(subset=["last_num"]).sort_values("quote_volume_num", ascending=False).head(100)
    return df.reset_index(drop=True)

@st.cache_data(ttl=60, show_spinner=False)
def get_candles(pair, interval, limit=150):
    response = requests.get(
        f"{API}/spot/candlesticks",
        params={"currency_pair": pair, "interval": interval, "limit": limit},
        timeout=25,
        headers={"Accept": "application/json", "User-Agent": "GateDashboard/1.1"}
    )
    response.raise_for_status()
    rows = response.json()
    if not isinstance(rows, list) or not rows:
        raise ValueError(f"Data candle untuk {pair} kosong dari Gate.io.")
    # Format Gate.io: timestamp, quote_volume, close, high, low, open, base_volume
    parsed = []
    for row in rows:
        if isinstance(row, (list, tuple)) and len(row) >= 7:
            parsed.append(row[:7])
    if not parsed:
        raise ValueError("Format data candle dari Gate.io tidak dikenali.")
    df = pd.DataFrame(parsed, columns=["time", "quote_volume", "close", "high", "low", "open", "base_volume"])
    for col in ["close", "high", "low", "open", "base_volume"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["time"] = pd.to_datetime(pd.to_numeric(df["time"], errors="coerce"), unit="s", utc=True, errors="coerce")
    df = df.dropna(subset=["time", "close"]).sort_values("time").reset_index(drop=True)
    return df

def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(window=period, min_periods=period).mean()
    loss = (-delta.clip(upper=0)).rolling(window=period, min_periods=period).mean()
    # Hindari pembagian dengan nol dan nilai NA yang dapat memicu error pada beberapa versi pandas.
    rs = gain / loss.where(loss != 0, np.nan)
    result = 100 - (100 / (1 + rs))
    result = result.where(loss != 0, 100)
    result = result.where(~((gain == 0) & (loss == 0)), 50)
    return result

with st.sidebar:
    st.header("Panel Direktur")
    st.write("Status sistem: 🟢 Dashboard aktif")
    st.write("Sumber data: Gate.io Public API")
    st.write("Akses: hanya-baca, tanpa API key")
    st.divider()
    interval_label = st.selectbox("Timeframe grafik", ["15 menit", "1 jam", "4 jam", "1 hari"])
    interval = {"15 menit": "15m", "1 jam": "1h", "4 jam": "4h", "1 hari": "1d"}[interval_label]
    if st.button("🔄 Refresh data", width="stretch"):
        st.cache_data.clear()
        st.rerun()

try:
    with st.spinner("Mengambil data pasar dari Gate.io..."):
        tickers = get_tickers()
    if tickers.empty:
        st.warning("Belum ada pasangan USDT yang tersedia dari Gate.io.")
        st.stop()

    col1, col2, col3 = st.columns(3)
    col1.metric("Pasangan USDT dipantau", len(tickers))
    col2.metric("Pembaruan terakhir (UTC)", datetime.now(timezone.utc).strftime("%H:%M:%S"))
    col3.metric("Mode", "Paper / Edukasi")

    st.subheader("Pemantauan pasar — 100 pasangan USDT teratas berdasarkan volume")
    market_view = tickers[["currency_pair", "last_num", "change_num", "quote_volume_num"]].copy()
    market_view.columns = ["Pasangan", "Harga terakhir (USDT)", "Perubahan 24 jam (%)", "Volume quote"]
    st.dataframe(market_view, width="stretch", hide_index=True)

    st.subheader("Analisis teknikal edukatif")
    pairs = tickers["currency_pair"].tolist()
    default_pair = "BTC_USDT" if "BTC_USDT" in pairs else pairs[0]
    pair = st.selectbox("Pilih pasangan", pairs, index=pairs.index(default_pair))
    with st.spinner(f"Mengambil candle {pair}..."):
        candles = get_candles(pair, interval)

    if len(candles) < 30:
        st.info(f"Data candle yang diterima hanya {len(candles)} baris; belum cukup untuk indikator.")
    else:
        candles["EMA20"] = candles["close"].ewm(span=20, adjust=False).mean()
        candles["EMA50"] = candles["close"].ewm(span=50, adjust=False).mean()
        candles["RSI14"] = calculate_rsi(candles["close"])
        latest = candles.iloc[-1]
        x, y, z = st.columns(3)
        x.metric("Harga candle terakhir", f"{latest['close']:.8g} USDT")
        y.metric("RSI 14", "—" if pd.isna(latest["RSI14"]) else f"{latest['RSI14']:.1f}")
        trend = "EMA20 di atas EMA50" if latest["EMA20"] > latest["EMA50"] else "EMA20 di bawah EMA50"
        z.metric("Kondisi EMA", trend)
        chart_data = candles.set_index("time")[["close", "EMA20", "EMA50"]]
        st.line_chart(chart_data, width="stretch")
        st.caption("Indikator hanya untuk pembelajaran. Bukan instruksi beli/jual dan tidak menjamin hasil.")

    st.subheader("Struktur karyawan AI — rancangan organisasi")
    roles = [
        ("CEO AI", "Mengawasi alur dan kualitas laporan"),
        ("Kepala Trading", "Mengkoordinasikan riset; tidak mengeksekusi transaksi"),
        ("Market Analyst", "Memantau kondisi pasar"),
        ("Technical Analyst", "Mengkaji tren dan struktur harga"),
        ("Fundamental Analyst", "Mengkaji informasi proyek dari sumber publik"),
        ("News Analyst", "Mencatat berita dan sentimen dengan sumber"),
        ("RSI & MACD Analyst", "Mengkaji momentum"),
        ("Fibonacci Analyst", "Mengkaji level retracement"),
        ("Volume Analyst", "Mengkaji aktivitas volume"),
        ("Chart Analyst", "Mengkaji pola grafik"),
        ("Risk Manager", "Menguji skenario risiko simulasi"),
        ("Signal Manager", "Merangkum perbedaan pendapat analis"),
        ("Performance Analyst", "Mengukur hasil simulasi"),
        ("Report Manager", "Menyusun laporan"),
    ]
    left, right = st.columns(2)
    for i, (role, task) in enumerate(roles):
        with (left if i % 2 == 0 else right):
            st.markdown(f"**{i+1}. {role}**  \n{task}")

except requests.RequestException as exc:
    st.error("Tidak dapat mengambil data dari Gate.io. Periksa koneksi atau coba lagi nanti.")
    st.code(str(exc))
except Exception as exc:
    st.error("Terjadi kesalahan saat memproses data.")
    st.code(f"{type(exc).__name__}: {exc}")
    st.info("Catat pesan teknis di atas jika masalah masih terjadi.")

st.divider()
st.caption("Aplikasi ini hanya untuk pemantauan dan pembelajaran. Tidak menyediakan nasihat keuangan, sinyal transaksi, leverage, atau eksekusi order.")
