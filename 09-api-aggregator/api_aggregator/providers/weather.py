from datetime import datetime, timezone
from typing import Any
from api_aggregator.client import ResilientHttpClient
from api_aggregator.models import UnifiedWeatherReport
from api_aggregator.providers.base import BaseProvider


WEATHER_CODE_MAP = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    71: "Slight snow",
    73: "Moderate snow",
    75: "Heavy snow",
    80: "Rain showers",
    95: "Thunderstorm",
}


class OpenMeteoProvider(BaseProvider):
    def __init__(self) -> None:
        super().__init__(name="openmeteo", domain="weather")
        self.geo_url = "https://geocoding-api.open-meteo.com/v1/search"
        self.forecast_url = "https://api.open-meteo.com/v1/forecast"

    async def fetch(
        self,
        client: ResilientHttpClient,
        city: str = "London",
        latitude: float | None = None,
        longitude: float | None = None,
        **kwargs: Any,
    ) -> UnifiedWeatherReport:
        lat = latitude
        lon = longitude
        resolved_city = city

        if lat is None or lon is None:
            geo_res = await client.get(
                self.geo_url,
                provider_name=self.name,
                params={"name": city, "count": 1, "language": "en"},
                timeout=4.0,
            )
            geo_data = geo_res.json()
            results = geo_data.get("results", [])
            if results:
                first = results[0]
                lat = float(first.get("latitude", 51.5074))
                lon = float(first.get("longitude", -0.1278))
                country = first.get("country", "")
                resolved_city = f"{first.get('name', city)}, {country}".strip(", ")
            else:
                lat = 51.5074
                lon = -0.1278

        params = {
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code",
        }
        res = await client.get(
            self.forecast_url, provider_name=self.name, params=params, timeout=4.0
        )
        data = res.json()
        current = data.get("current", {})

        temp_c = float(current.get("temperature_2m", 18.0))
        temp_f = round((temp_c * 9.0 / 5.0) + 32.0, 1)
        humidity = float(current.get("relative_humidity_2m", 60.0))
        wind_speed = float(current.get("wind_speed_10m", 12.0))
        code = int(current.get("weather_code", 0))
        condition = WEATHER_CODE_MAP.get(code, "Clear")

        return UnifiedWeatherReport(
            location=resolved_city,
            latitude=lat,
            longitude=lon,
            temperature_c=temp_c,
            temperature_f=temp_f,
            humidity_percent=humidity,
            wind_speed_kmh=wind_speed,
            condition=condition,
            sources=["Open-Meteo"],
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    def fallback(
        self, city: str = "London", **kwargs: Any
    ) -> UnifiedWeatherReport:
        return UnifiedWeatherReport(
            location=city,
            latitude=51.5074,
            longitude=-0.1278,
            temperature_c=18.5,
            temperature_f=65.3,
            humidity_percent=65.0,
            wind_speed_kmh=14.2,
            condition="Partly cloudy",
            sources=["Open-Meteo"],
            timestamp=datetime.now(timezone.utc).isoformat(),
        )


class WttrInProvider(BaseProvider):
    def __init__(self) -> None:
        super().__init__(name="wttrin", domain="weather")

    async def fetch(
        self,
        client: ResilientHttpClient,
        city: str = "London",
        **kwargs: Any,
    ) -> UnifiedWeatherReport:
        url = f"https://wttr.in/{city}"
        res = await client.get(
            url,
            provider_name=self.name,
            params={"format": "j1"},
            timeout=4.0,
        )
        data = res.json()
        current = data.get("current_condition", [{}])[0]
        temp_c = float(current.get("temp_C", 18.0))
        temp_f = float(current.get("temp_F", round((temp_c * 9.0 / 5.0) + 32.0, 1)))
        humidity = float(current.get("humidity", 60.0))
        wind_speed = float(current.get("windspeedKmph", 12.0))
        desc = current.get("weatherDesc", [{}])[0].get("value", "Clear")

        nearest = data.get("nearest_area", [{}])[0]
        lat = float(nearest.get("latitude", 51.5074))
        lon = float(nearest.get("longitude", -0.1278))

        return UnifiedWeatherReport(
            location=city,
            latitude=lat,
            longitude=lon,
            temperature_c=temp_c,
            temperature_f=temp_f,
            humidity_percent=humidity,
            wind_speed_kmh=wind_speed,
            condition=desc,
            sources=["wttr.in"],
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    def fallback(
        self, city: str = "London", **kwargs: Any
    ) -> UnifiedWeatherReport:
        return UnifiedWeatherReport(
            location=city,
            latitude=51.5074,
            longitude=-0.1278,
            temperature_c=18.0,
            temperature_f=64.4,
            humidity_percent=68.0,
            wind_speed_kmh=15.0,
            condition="Overcast",
            sources=["wttr.in"],
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
