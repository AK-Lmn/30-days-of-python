import asyncio
import json
import threading
from typing import Any, Callable, Optional
import customtkinter as ctk

from api_aggregator.config import CONFIG
from api_aggregator.engine import AggregationEngine


class AggregatorGui(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.title(f"{CONFIG.app_name} Dashboard")
        self.geometry("980x640")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.engine = AggregationEngine()
        self.current_domain = "news"

        self._build_ui()

    def _build_ui(self) -> None:
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.sidebar = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        self.sidebar.grid_rowconfigure(7, weight=1)

        self.logo_label = ctk.CTkLabel(
            self.sidebar,
            text="API Aggregator",
            font=ctk.CTkFont(size=18, weight="bold"),
        )
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        self.btn_news = ctk.CTkButton(
            self.sidebar, text="Tech News", command=lambda: self._select_domain("news")
        )
        self.btn_news.grid(row=1, column=0, padx=20, pady=5)

        self.btn_crypto = ctk.CTkButton(
            self.sidebar,
            text="Crypto Rates",
            command=lambda: self._select_domain("crypto"),
        )
        self.btn_crypto.grid(row=2, column=0, padx=20, pady=5)

        self.btn_weather = ctk.CTkButton(
            self.sidebar,
            text="Weather",
            command=lambda: self._select_domain("weather"),
        )
        self.btn_weather.grid(row=3, column=0, padx=20, pady=5)

        self.btn_overview = ctk.CTkButton(
            self.sidebar,
            text="Overview",
            command=lambda: self._select_domain("overview"),
        )
        self.btn_overview.grid(row=4, column=0, padx=20, pady=5)

        self.btn_status = ctk.CTkButton(
            self.sidebar,
            text="Health & Status",
            command=lambda: self._select_domain("status"),
        )
        self.btn_status.grid(row=5, column=0, padx=20, pady=5)

        self.main_frame = ctk.CTkFrame(self, corner_radius=10)
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(2, weight=1)

        self.header_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.header_frame.grid(row=0, column=0, sticky="ew", padx=15, pady=10)

        self.title_label = ctk.CTkLabel(
            self.header_frame,
            text="Tech News Aggregator",
            font=ctk.CTkFont(size=20, weight="bold"),
        )
        self.title_label.pack(side="left")

        self.latency_badge = ctk.CTkLabel(
            self.header_frame,
            text="Ready",
            font=ctk.CTkFont(size=12),
            text_color="gray",
        )
        self.latency_badge.pack(side="right", padx=10)

        self.controls_frame = ctk.CTkFrame(self.main_frame)
        self.controls_frame.grid(row=1, column=0, sticky="ew", padx=15, pady=5)

        self.input_param = ctk.CTkEntry(
            self.controls_frame, placeholder_text="Limit (e.g. 5)", width=220
        )
        self.input_param.pack(side="left", padx=10, pady=10)

        self.btn_run = ctk.CTkButton(
            self.controls_frame,
            text="Fetch & Aggregate",
            command=self._execute_query,
        )
        self.btn_run.pack(side="left", padx=10, pady=10)

        self.mock_var = ctk.BooleanVar(value=False)
        self.check_mock = ctk.CTkCheckBox(
            self.controls_frame, text="Mock Fallback", variable=self.mock_var
        )
        self.check_mock.pack(side="left", padx=10, pady=10)

        self.result_textbox = ctk.CTkTextbox(
            self.main_frame, font=ctk.CTkFont(family="Consolas", size=12)
        )
        self.result_textbox.grid(row=2, column=0, sticky="nsew", padx=15, pady=15)

    def _select_domain(self, domain: str) -> None:
        self.current_domain = domain
        titles = {
            "news": "Tech News Aggregator",
            "crypto": "Crypto Exchange Rates",
            "weather": "Unified Weather Reports",
            "overview": "Cross-Domain Executive Overview",
            "status": "Provider Health & Circuit Status",
        }
        placeholders = {
            "news": "Item count limit (e.g. 5)",
            "crypto": "Coin symbols (e.g. BTC,ETH,SOL)",
            "weather": "City name (e.g. London)",
            "overview": "No parameters required",
            "status": "No parameters required",
        }
        self.title_label.configure(text=titles.get(domain, domain.capitalize()))
        self.input_param.delete(0, "end")
        self.input_param.configure(
            placeholder_text=placeholders.get(domain, "Parameters")
        )

    def _run_async(self, coro: Any, callback: Callable[[Any], None]) -> None:
        def worker() -> None:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                res = loop.run_until_complete(coro)
                self.after(0, lambda: callback(res))
            except Exception as exc:
                self.after(0, lambda: self._on_error(str(exc)))
            finally:
                loop.close()

        threading.Thread(target=worker, daemon=True).start()

    def _execute_query(self) -> None:
        self.latency_badge.configure(text="Aggregating...", text_color="yellow")
        self.btn_run.configure(state="disabled")
        param = self.input_param.get().strip()
        is_mock = self.mock_var.get()

        if self.current_domain == "news":
            limit = int(param) if param.isdigit() else 5
            self._run_async(
                self.engine.aggregate_news(
                    limit=limit, use_cache=False, force_mock=is_mock
                ),
                self._on_news_result,
            )
        elif self.current_domain == "crypto":
            coins = (
                [s.strip().upper() for s in param.split(",") if s.strip()]
                if param
                else ["BTC", "ETH", "SOL"]
            )
            self._run_async(
                self.engine.aggregate_crypto(
                    symbols=coins, use_cache=False, force_mock=is_mock
                ),
                self._on_crypto_result,
            )
        elif self.current_domain == "weather":
            city = param or "London"
            self._run_async(
                self.engine.aggregate_weather(
                    city=city, use_cache=False, force_mock=is_mock
                ),
                self._on_weather_result,
            )
        elif self.current_domain == "overview":
            self._run_async(
                self.engine.aggregate_overview(use_cache=False, force_mock=is_mock),
                self._on_overview_result,
            )
        elif self.current_domain == "status":
            self._run_async(self.engine.get_metrics(), self._on_status_result)

    def _on_news_result(self, envelope: Any) -> None:
        self.btn_run.configure(state="normal")
        self.latency_badge.configure(
            text=f"Latency: {envelope.latency_ms}ms", text_color="green"
        )
        self.result_textbox.delete("1.0", "end")
        text_lines = [
            f"=== Unified News Aggregation ({envelope.count} items, status={envelope.status.value}) ===",
            f"Sources Queried: {', '.join(envelope.sources_queried)}",
            f"Sources Succeeded: {', '.join(envelope.sources_succeeded)}",
            "",
        ]
        for idx, item in enumerate(envelope.data, 1):
            text_lines.append(f"[{idx}] [{item.source}] {item.title}")
            text_lines.append(
                f"    Author: {item.author} | Score: {item.score} | Comments: {item.comments_count}"
            )
            text_lines.append(f"    URL: {item.url}")
            text_lines.append(f"    Tags: {', '.join(item.tags)}")
            text_lines.append("")
        self.result_textbox.insert("1.0", "\n".join(text_lines))

    def _on_crypto_result(self, envelope: Any) -> None:
        self.btn_run.configure(state="normal")
        self.latency_badge.configure(
            text=f"Latency: {envelope.latency_ms}ms", text_color="green"
        )
        self.result_textbox.delete("1.0", "end")
        text_lines = [
            f"=== Reconciled Crypto Rates (status={envelope.status.value}) ===",
            "",
        ]
        for rate in envelope.data:
            text_lines.append(f"Symbol: {rate.symbol} ({rate.name})")
            text_lines.append(f"  Price: ${rate.price_usd:,.2f}")
            text_lines.append(f"  24h Change: {rate.change_24h_percent:+.2f}%")
            text_lines.append(f"  Cross-Exchange Spread: {rate.discrepancy_percent:.2f}%")
            text_lines.append(f"  Contributing Sources: {', '.join(rate.sources)}")
            text_lines.append("")
        self.result_textbox.insert("1.0", "\n".join(text_lines))

    def _on_weather_result(self, envelope: Any) -> None:
        self.btn_run.configure(state="normal")
        self.latency_badge.configure(
            text=f"Latency: {envelope.latency_ms}ms", text_color="green"
        )
        self.result_textbox.delete("1.0", "end")
        rep = envelope.data
        if not rep:
            self.result_textbox.insert("1.0", "No weather report found.")
            return
        text_lines = [
            f"=== Weather Report — {rep.location} ===",
            f"Coordinates: {rep.latitude:.4f}, {rep.longitude:.4f}",
            f"Condition: {rep.condition}",
            f"Temperature: {rep.temperature_c}°C ({rep.temperature_f}°F)",
            f"Humidity: {rep.humidity_percent}%",
            f"Wind Speed: {rep.wind_speed_kmh} km/h",
            f"Sources: {', '.join(rep.sources)}",
        ]
        self.result_textbox.insert("1.0", "\n".join(text_lines))

    def _on_overview_result(self, envelope: Any) -> None:
        self.btn_run.configure(state="normal")
        self.latency_badge.configure(
            text=f"Latency: {envelope.latency_ms}ms", text_color="green"
        )
        self.result_textbox.delete("1.0", "end")
        data = envelope.data
        formatted = json.dumps(data.model_dump(), indent=2)
        self.result_textbox.insert("1.0", formatted)

    def _on_status_result(self, metrics: Any) -> None:
        self.btn_run.configure(state="normal")
        self.latency_badge.configure(text="Telemetry Updated", text_color="green")
        self.result_textbox.delete("1.0", "end")
        formatted = json.dumps(metrics.model_dump(), indent=2)
        self.result_textbox.insert("1.0", formatted)

    def _on_error(self, err_msg: str) -> None:
        self.btn_run.configure(state="normal")
        self.latency_badge.configure(text="Error", text_color="red")
        self.result_textbox.delete("1.0", "end")
        self.result_textbox.insert("1.0", f"Error occurred:\n{err_msg}")


def run_gui() -> None:
    app = AggregatorGui()
    app.mainloop()
