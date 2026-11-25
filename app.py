import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timezone

API = "https://api.gateio.ws/api/v4"

st.set_page_config(page_title="Gate AI Trading Intelligence", page_icon="📊", layout="wide")

st.markdown("""
<style>
.stApp {background: #0b1220; color: #e5e7eb;}
[data-testid="stMetric"] {background: #111c2e; padding: 14px; border-radius: 10px;}
</style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=60)
def get_tickers():
    r = requests.get(f"{API}/spot/tickers", timeout=20)
    r.raise_for_status()
    data = r.json()
    df = pd.DataFrame(data)
    if df.empty:
        return df
    df["quote_volume_num"] = pd.to_numeric(df.get("quote_volume"), errors="coerce")
    df["last_num"] = pd.to_numeric(df.get("last"), errors="coerce")
    df["change_num"] = pd.to_numeric(df.get("change_percentage"), errors="coerce")
    df = df[df["currency_pair"].str.endswith("_USDT", na=False)]
    df = df.sort_values("quote_volume_num", ascending=False).head(100)
    return df

@st.cache_data(ttl=60)
def get_candles(pair, interval, limit=150):
    r = requests.get(
        f"{API}/spot/candlesticks",
        params={"currency_pair": pair, "interval": interval, "limit": limit},
        timeout=20
    )
    r.raise_for_status()
    rows = r.json()
    # Gate format: [timestamp, quote_volume, close, high, low, open, base_volume]
    df = pd.DataFrame(rows, columns=["time", "quote_volume", "close", "high", "low", "open", "base_volume"])
    for c in ["close", "high", "low", "open", "base_volume"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["time"] = pd.to_datetime(pd.to_numeric(df["time"]), unit="s", utc=True)
    return df.sort_values("time")

def rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss.replace(0, pd.NA)
    return 100 - (100 / (1 + rs))

st.title("📊 GATE AI TRADING INTELLIGENCE")
st.caption("Versi 1.0 • Data publik Gate.io • Mode edukasi dan simulasi — bukan rekomendasi investasi")

with st.sidebar:
    st.header("Panel Direktur")
    st.write("Status sistem: 🟢 Dashboard aktif")
    st.write("Sumber data: Gate.io Public API")
    st.write("Akses: hanya-baca, tanpa API key")
    st.divider()
    interval_label = st.selectbox("Timeframe grafik", ["15 menit", "1 jam", "4 jam", "1 hari"])
    interval_map = {"15 menit": "15m", "1 jam": "1h", "4 jam": "4h", "1 hari": "1d"}
    interval = interval_map[interval_label]
    st.caption("Pembaruan data otomatis saat halaman dimuat; gunakan tombol Refresh untuk mengambil data terbaru.")
    if st.button("🔄 Refresh data"):
        st.cache_data.clear()
        st.rerun()

try:
    tickers = get_tickers()
    if tickers.empty:
        st.warning("Belum ada data yang diterima dari Gate.io.")
        st.stop()

    a, b, c = st.columns(3)
    a.metric("Pasangan USDT dipantau", len(tickers))
    b.metric("Pembaruan terakhir (UTC)", datetime.now(timezone.utc).strftime("%H:%M:%S"))
    c.metric("Mode", "Paper / Edukasi")

    st.subheader("Pemantauan pasar — 100 pasangan USDT teratas berdasarkan volume")
    view = tickers[["currency_pair", "last_num", "change_num", "quote_volume_num"]].copy()
    view.columns = ["Pasangan", "Harga terakhir (USDT)", "Perubahan 24 jam (%)", "Volume quote"]
    st.dataframe(view, use_container_width=True, hide_index=True)

    st.subheader("Analisis teknikal edukatif")
    pairs = tickers["currency_pair"].tolist()
    default_pair = "BTC_USDT" if "BTC_USDT" in pairs else pairs[0]
    pair = st.selectbox("Pilih pasangan", pairs, index=pairs.index(default_pair))
    candles = get_candles(pair, interval)
    if len(candles) < 30:
        st.info("Data candle belum cukup untuk menghitung indikator.")
    else:
        candles["EMA20"] = candles["close"].ewm(span=20, adjust=False).mean()
        candles["EMA50"] = candles["close"].ewm(span=50, adjust=False).mean()
        candles["RSI14"] = rsi(candles["close"])
        latest = candles.iloc[-1]
        x, y, z = st.columns(3)
        x.metric("Harga candle terakhir", f"{latest['close']:.8g} USDT")
        y.metric("RSI 14", "—" if pd.isna(latest["RSI14"]) else f"{latest['RSI14']:.1f}")
        trend = "EMA20 di atas EMA50" if latest["EMA20"] > latest["EMA50"] else "EMA20 di bawah EMA50"
        z.metric("Kondisi EMA", trend)
        st.line_chart(candles.set_index("time")[["close", "EMA20", "EMA50"]], use_container_width=True)
        st.caption("Interpretasi indikator bersifat edukatif dan tidak menghasilkan instruksi beli/jual. RSI/EMA dapat keliru, terutama saat pasar volatil.")

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
    cols = st.columns(2)
    for i, (role, task) in enumerate(roles):
        with cols[i % 2]:
            st.markdown(f"**{i+1}. {role}**  \n{task}")

except requests.RequestException as e:
    st.error("Tidak dapat mengambil data dari Gate.io saat ini.")
    st.code(str(e))
    st.info("Periksa koneksi internet atau coba lagi beberapa saat kemudian.")
except Exception as e:
    st.error("Terjadi kesalahan saat memproses data.")
    st.code(str(e))

st.divider()
st.caption("Peringatan: aplikasi ini untuk pemantauan dan pembelajaran. Tidak menyediakan nasihat keuangan, sinyal transaksi, leverage, maupun eksekusi order.")
