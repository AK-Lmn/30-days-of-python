from typing import Any
from api_aggregator.client import ResilientHttpClient
from api_aggregator.models import UnifiedCryptoRate
from api_aggregator.providers.base import BaseProvider


class CoinGeckoProvider(BaseProvider):
    def __init__(self) -> None:
        super().__init__(name="coingecko", domain="crypto")
        self.base_url = "https://api.coingecko.com/api/v3/simple/price"
        self._symbol_map = {
            "btc": "bitcoin",
            "eth": "ethereum",
            "sol": "solana",
            "ada": "cardano",
            "doge": "dogecoin",
            "xrp": "ripple",
        }

    async def fetch(
        self,
        client: ResilientHttpClient,
        symbols: list[str] | None = None,
        **kwargs: Any,
    ) -> list[UnifiedCryptoRate]:
        requested_symbols = [s.lower() for s in (symbols or ["btc", "eth", "sol"])]
        ids = [self._symbol_map.get(s, s) for s in requested_symbols]

        params = {
            "ids": ",".join(ids),
            "vs_currencies": "usd",
            "include_24hr_change": "true",
            "include_market_cap": "true",
            "include_24hr_vol": "true",
        }

        response = await client.get(
            self.base_url, provider_name=self.name, params=params, timeout=4.0
        )
        data = response.json()
        results: list[UnifiedCryptoRate] = []

        rev_map = {v: k.upper() for k, v in self._symbol_map.items()}
        for cid, info in data.items():
            sym = rev_map.get(cid, cid.upper()[:4])
            price = float(info.get("usd", 0.0))
            change = float(info.get("usd_24h_change", 0.0))
            mcap = float(info.get("usd_market_cap", 0.0)) if "usd_market_cap" in info else None
            vol = float(info.get("usd_24h_vol", 0.0)) if "usd_24h_vol" in info else None

            results.append(
                UnifiedCryptoRate(
                    symbol=sym,
                    name=cid.capitalize(),
                    price_usd=price,
                    change_24h_percent=round(change, 2),
                    market_cap=mcap,
                    volume_24h=vol,
                    sources=["CoinGecko"],
                )
            )
        return results

    def fallback(
        self, symbols: list[str] | None = None, **kwargs: Any
    ) -> list[UnifiedCryptoRate]:
        requested = [s.upper() for s in (symbols or ["BTC", "ETH", "SOL"])]
        mock_map = {
            "BTC": UnifiedCryptoRate(
                symbol="BTC",
                name="Bitcoin",
                price_usd=68500.0,
                change_24h_percent=2.45,
                market_cap=1350000000000.0,
                volume_24h=28400000000.0,
                sources=["CoinGecko"],
            ),
            "ETH": UnifiedCryptoRate(
                symbol="ETH",
                name="Ethereum",
                price_usd=3550.0,
                change_24h_percent=1.82,
                market_cap=425000000000.0,
                volume_24h=14500000000.0,
                sources=["CoinGecko"],
            ),
            "SOL": UnifiedCryptoRate(
                symbol="SOL",
                name="Solana",
                price_usd=165.0,
                change_24h_percent=4.12,
                market_cap=76000000000.0,
                volume_24h=4100000000.0,
                sources=["CoinGecko"],
            ),
        }
        return [mock_map[s] for s in requested if s in mock_map]


class CoinbaseProvider(BaseProvider):
    def __init__(self) -> None:
        super().__init__(name="coinbase", domain="crypto")
        self.url = "https://api.coinbase.com/v2/exchange-rates?currency=USD"

    async def fetch(
        self,
        client: ResilientHttpClient,
        symbols: list[str] | None = None,
        **kwargs: Any,
    ) -> list[UnifiedCryptoRate]:
        requested = [s.upper() for s in (symbols or ["BTC", "ETH", "SOL"])]
        response = await client.get(self.url, provider_name=self.name, timeout=4.0)
        data = response.json()
        rates = data.get("data", {}).get("rates", {})

        results: list[UnifiedCryptoRate] = []
        for sym in requested:
            if sym in rates:
                rate_per_usd = float(rates[sym])
                if rate_per_usd > 0:
                    price_usd = round(1.0 / rate_per_usd, 2)
                    results.append(
                        UnifiedCryptoRate(
                            symbol=sym,
                            name=sym,
                            price_usd=price_usd,
                            change_24h_percent=0.0,
                            sources=["Coinbase"],
                        )
                    )
        return results

    def fallback(
        self, symbols: list[str] | None = None, **kwargs: Any
    ) -> list[UnifiedCryptoRate]:
        requested = [s.upper() for s in (symbols or ["BTC", "ETH", "SOL"])]
        mock_map = {
            "BTC": UnifiedCryptoRate(
                symbol="BTC",
                name="BTC",
                price_usd=68540.0,
                change_24h_percent=2.50,
                sources=["Coinbase"],
            ),
            "ETH": UnifiedCryptoRate(
                symbol="ETH",
                name="ETH",
                price_usd=3555.0,
                change_24h_percent=1.90,
                sources=["Coinbase"],
            ),
            "SOL": UnifiedCryptoRate(
                symbol="SOL",
                name="SOL",
                price_usd=164.8,
                change_24h_percent=4.05,
                sources=["Coinbase"],
            ),
        }
        return [mock_map[s] for s in requested if s in mock_map]


class BinanceProvider(BaseProvider):
    def __init__(self) -> None:
        super().__init__(name="binance", domain="crypto")
        self.url = "https://api.binance.com/api/v3/ticker/24hr"

    async def fetch(
        self,
        client: ResilientHttpClient,
        symbols: list[str] | None = None,
        **kwargs: Any,
    ) -> list[UnifiedCryptoRate]:
        requested = [s.upper() for s in (symbols or ["BTC", "ETH", "SOL"])]
        pair_to_sym = {f"{s}USDT": s for s in requested}

        results: list[UnifiedCryptoRate] = []
        for pair, sym in pair_to_sym.items():
            try:
                response = await client.get(
                    self.url,
                    provider_name=self.name,
                    params={"symbol": pair},
                    timeout=3.0,
                )
                data = response.json()
                price = float(data.get("lastPrice", 0.0))
                change = float(data.get("priceChangePercent", 0.0))
                high = float(data.get("highPrice", 0.0))
                low = float(data.get("lowPrice", 0.0))
                vol = float(data.get("quoteVolume", 0.0))

                results.append(
                    UnifiedCryptoRate(
                        symbol=sym,
                        name=sym,
                        price_usd=price,
                        change_24h_percent=round(change, 2),
                        high_24h=high,
                        low_24h=low,
                        volume_24h=vol,
                        sources=["Binance"],
                    )
                )
            except Exception:
                continue

        return results

    def fallback(
        self, symbols: list[str] | None = None, **kwargs: Any
    ) -> list[UnifiedCryptoRate]:
        requested = [s.upper() for s in (symbols or ["BTC", "ETH", "SOL"])]
        mock_map = {
            "BTC": UnifiedCryptoRate(
                symbol="BTC",
                name="BTC",
                price_usd=68480.0,
                change_24h_percent=2.40,
                high_24h=69200.0,
                low_24h=67100.0,
                volume_24h=29000000000.0,
                sources=["Binance"],
            ),
            "ETH": UnifiedCryptoRate(
                symbol="ETH",
                name="ETH",
                price_usd=3548.0,
                change_24h_percent=1.75,
                high_24h=3620.0,
                low_24h=3480.0,
                volume_24h=14100000000.0,
                sources=["Binance"],
            ),
            "SOL": UnifiedCryptoRate(
                symbol="SOL",
                name="SOL",
                price_usd=165.2,
                change_24h_percent=4.15,
                high_24h=169.0,
                low_24h=158.0,
                volume_24h=4200000000.0,
                sources=["Binance"],
            ),
        }
        return [mock_map[s] for s in requested if s in mock_map]
