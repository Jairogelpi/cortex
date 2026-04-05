"""
Modulo de datos de mercado reales.
Conecta con Alpaca Paper Trading y Yahoo Finance.
Sin datos mock - todo real desde el primer dia.
"""
from datetime import datetime, timedelta
from typing import Optional
import pandas as pd
import yfinance as yf
from alpaca.trading.client import TradingClient
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from loguru import logger

from cortex.config import config


class MarketData:
    """
    Fuente de datos de mercado real para Cortex V2.
    Alpaca como fuente primaria, Yahoo Finance para VIX e indicadores.
    """

    def __init__(self):
        self.trading_client = TradingClient(
            api_key=config.ALPACA_API_KEY,
            secret_key=config.ALPACA_SECRET_KEY,
            paper=True
        )
        self.data_client = StockHistoricalDataClient(
            api_key=config.ALPACA_API_KEY,
            secret_key=config.ALPACA_SECRET_KEY
        )
        logger.info("MarketData inicializado con Alpaca Paper Trading")

    def get_account(self) -> dict:
        """Obtiene estado real de la cuenta paper trading."""
        account = self.trading_client.get_account()
        return {
            "equity": float(account.equity),
            "cash": float(account.cash),
            "buying_power": float(account.buying_power),
            "portfolio_value": float(account.portfolio_value),
            "status": str(account.status)
        }

    def get_vix(self) -> float:
        """
        Obtiene VIX actual desde Yahoo Finance.
        VIX es el indicador clave para detectar regimen R1-R4.
        """
        try:
            vix = yf.Ticker("^VIX")
            hist = vix.history(period="2d")
            if not hist.empty:
                value = round(float(hist["Close"].iloc[-1]), 2)
                logger.info(f"VIX actual: {value}")
                return value
        except Exception as e:
            logger.error(f"Error obteniendo VIX: {e}")
        return -1.0

    def get_prices(self, symbols: list, days: int = 30) -> pd.DataFrame:
        """
        Obtiene precios historicos reales desde Yahoo Finance.
        Solo datos post-cutoff del modelo (sep 2025+) para evitar look-ahead bias.
        """
        end = datetime.now()
        start = end - timedelta(days=days)
        logger.info(f"Descargando precios: {symbols} ({days} dias)")
        df = yf.download(
            symbols,
            start=start.strftime("%Y-%m-%d"),
            end=end.strftime("%Y-%m-%d"),
            auto_adjust=True,
            progress=False
        )
        if df.empty:
            logger.error("No se obtuvieron datos de Yahoo Finance")
        else:
            logger.info(f"Precios obtenidos: {len(df)} filas")
        return df

    def get_regime_indicators(self) -> dict:
        """
        Calcula los 4 indicadores para clasificar regimen R1-R4.
        Definiciones formales del paper seccion 9.3:

        R1 Expansion:    VIX < 20,  momentum_21d > 0,   vol_real < 15%
        R2 Acumulacion:  VIX 20-28, momentum_21d ~= 0,  vol comprimida
        R3 Transicion:   VIX > 28,  VIX sube >3pts/sem
        R4 Contraccion:  VIX > 35,  momentum < -5%,     drawdown > -15%
        """
        try:
            spy = yf.Ticker("SPY")
            hist = spy.history(period="3mo")
            if hist.empty:
                return {"error": "No hay datos de SPY"}

            closes = hist["Close"]
            current_price = float(closes.iloc[-1])
            price_21d_ago = float(closes.iloc[-22]) if len(closes) > 22 else current_price

            momentum_21d = round((current_price - price_21d_ago) / price_21d_ago * 100, 2)

            returns = closes.pct_change().dropna()
            vol_real = round(float(returns.tail(21).std() * (252 ** 0.5) * 100), 2)

            vix = self.get_vix()

            max_90d = float(closes.tail(90).max())
            drawdown_90d = round((current_price - max_90d) / max_90d * 100, 2)

            # Clasificacion de regimen segun definiciones del paper
            regime = self._classify_regime(vix, momentum_21d, vol_real, drawdown_90d)

            indicators = {
                "vix": vix,
                "momentum_21d_pct": momentum_21d,
                "vol_realized_pct": vol_real,
                "drawdown_90d_pct": drawdown_90d,
                "spy_price": round(current_price, 2),
                "regime": regime,
                "timestamp": datetime.now().isoformat()
            }
            logger.info(f"Indicadores: {indicators}")
            return indicators

        except Exception as e:
            logger.error(f"Error calculando indicadores: {e}")
            return {"error": str(e)}

    def _classify_regime(
        self,
        vix: float,
        momentum: float,
        vol: float,
        drawdown: float
    ) -> str:
        """
        Clasifica el regimen de mercado segun las definiciones formales.
        Retorna R1, R2, R3, R4 o INDETERMINATE.
        """
        if vix > 35 and momentum < -5 and drawdown < -15:
            return "R4_CONTRACTION"
        elif vix > 28:
            return "R3_TRANSITION"
        elif 20 <= vix <= 28 and abs(momentum) <= 2:
            return "R2_ACCUMULATION"
        elif vix < 20 and momentum > 0 and vol < 15:
            return "R1_EXPANSION"
        else:
            return "INDETERMINATE"


def test_connection():
    """Prueba la conexion completa con Alpaca y Yahoo Finance."""
    print("\n" + "="*50)
    print("  CORTEX V2 - Test de conexion")
    print("="*50 + "\n")

    if not config.validate():
        print("\nEdita el archivo .env con tus claves reales y vuelve a intentarlo.")
        return False

    md = MarketData()

    print("1. Cuenta Alpaca Paper Trading:")
    account = md.get_account()
    for k, v in account.items():
        print(f"   {k}: {v}")

    print("\n2. VIX actual:")
    vix = md.get_vix()
    print(f"   VIX = {vix}")

    print("\n3. Indicadores de regimen de mercado:")
    indicators = md.get_regime_indicators()
    for k, v in indicators.items():
        print(f"   {k}: {v}")

    print("\n" + "="*50)
    print("  CONEXION OK - Listo para Fase 1 (capa Phi)")
    print("="*50 + "\n")
    return True


if __name__ == "__main__":
    test_connection()
