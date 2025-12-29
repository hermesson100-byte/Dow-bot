import os
import yfinance as yf
import pandas as pd
import requests
from ta.volume import VolumeWeightedAveragePrice

# 🔐 Pegamos do GitHub Secrets
BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID   = os.environ["CHAT_ID"]

YM  = "YM=F"
VIX = "^VIX"
SPX = "^GSPC"


def flat(df):
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df


print("Baixando dados...")

ym  = flat(yf.download(YM,  period="3mo", interval="1d", auto_adjust=True, progress=False)).reset_index()
spx = flat(yf.download(SPX, period="3mo", interval="1d", auto_adjust=True, progress=False)).reset_index()
vix = flat(yf.download(VIX, period="3mo", interval="1d", auto_adjust=True, progress=False)).reset_index()

ym = ym.dropna()

# ===== GAP / VWAP / SPX / VIX =====
ym["PrevClose"]   = ym["Close"].shift(1)
ym["GapPct"]      = (ym["Open"] - ym["PrevClose"]) / ym["PrevClose"]
ym["IntradayPct"] = (ym["Close"] - ym["Open"]) / ym["Open"]

vwap = VolumeWeightedAveragePrice(
    high=ym["High"], low=ym["Low"], close=ym["Close"], volume=ym["Volume"]
)
ym["VWAP"] = vwap.volume_weighted_average_price()

last = ym.iloc[-1]
prev = ym.iloc[-2]

vix_today = vix.iloc[-1]["Close"]
spx_today = spx.iloc[-1]["Close"] - spx.iloc[-2]["Close"]

# ===== SCORE =====
score = 0

if last["GapPct"] > 0: score += 1
if last["GapPct"] < 0: score -= 1

if last["Open"] > prev["VWAP"]: score += 1
if last["Open"] < prev["VWAP"]: score -= 1

if spx_today > 0: score += 1
if spx_today < 0: score -= 1

if vix_today > 20: score -= 1
elif vix_today < 15: score += 1


if score >= 2:
    sugestao = "BUY favorecido (aguardar confirmar)"
elif score <= -2:
    sugestao = "SELL favorecido (aguardar confirmar)"
else:
    sugestao = "NO TRADE (esperar)"

msg = f"""
📊 DOW — PRÉ-ABERTURA
📅 {last['Date'].strftime('%d/%m/%Y')}

Gap: {round(last['GapPct']*100,2)}%
VWAP ontem: {"acima" if last["Open"] > prev["VWAP"] else "abaixo"}
VIX: {round(vix_today,2)}
SPX: {"positivo" if spx_today>0 else "negativo"}

Score: {score}
➡ {sugestao}
"""

requests.post(
    f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
    json={"chat_id": CHAT_ID, "text": msg}
)

print("✔ Mensagem enviada!")
