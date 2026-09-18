import threading
from tkinter import messagebox
import customtkinter as ctk
from price_tracker.db import Database
from price_tracker.exporter import Exporter
from price_tracker.extractor import PriceExtractor
from price_tracker.models import Product
from price_tracker.scraper import WebScraper
from price_tracker.tracker import PriceTracker

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


class AddProductDialog(ctk.CTkToplevel):
    def __init__(self, parent: ctk.CTk, on_save_callback: object):
        super().__init__(parent)
        self.on_save_callback = on_save_callback
        self.title("Add Product to Track")
        self.geometry("520x460")
        self.resizable(False, False)

        self.grid_columnconfigure(0, weight=1)

        title_label = ctk.CTkLabel(self, text="Track New Product", font=ctk.CTkFont(size=18, weight="bold"))
        title_label.pack(pady=(15, 10))

        self.name_entry = ctk.CTkEntry(self, placeholder_text="Product Name (e.g. Sony WH-1000XM5)", width=440)
        self.name_entry.pack(pady=6)

        self.url_entry = ctk.CTkEntry(self, placeholder_text="Product URL (https://...)", width=440)
        self.url_entry.pack(pady=6)

        self.selector_entry = ctk.CTkEntry(
            self, placeholder_text="CSS Selector (Optional, e.g. .price or leave empty)", width=440
        )
        self.selector_entry.pack(pady=6)

        self.target_entry = ctk.CTkEntry(
            self, placeholder_text="Target Price (e.g. 299.99 or leave empty)", width=440
        )
        self.target_entry.pack(pady=6)

        self.currency_entry = ctk.CTkEntry(self, placeholder_text="Currency (Default: USD)", width=440)
        self.currency_entry.pack(pady=6)

        self.tag_entry = ctk.CTkEntry(self, placeholder_text="Category / Tag (e.g. Audio, Tech)", width=440)
        self.tag_entry.pack(pady=6)

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=(15, 10))

        test_btn = ctk.CTkButton(
            btn_frame, text="Test URL", width=120, fg_color="#334155", hover_color="#475569", command=self.test_fetch
        )
        test_btn.pack(side="left", padx=8)

        save_btn = ctk.CTkButton(btn_frame, text="Add Product", width=140, command=self.save_product)
        save_btn.pack(side="left", padx=8)

        cancel_btn = ctk.CTkButton(
            btn_frame, text="Cancel", width=100, fg_color="#64748b", hover_color="#475569", command=self.destroy
        )
        cancel_btn.pack(side="left", padx=8)

        self.status_label = ctk.CTkLabel(self, text="", text_color="gray", font=ctk.CTkFont(size=12))
        self.status_label.pack(pady=5)

    def test_fetch(self) -> None:
        url = self.url_entry.get().strip()
        if not url:
            self.status_label.configure(text="Please enter a URL first.", text_color="red")
            return

        self.status_label.configure(text="Testing fetch...", text_color="cyan")

        def run():
            scraper = WebScraper()
            extractor = PriceExtractor()
            html, err = scraper.fetch_html(url)
            if err:
                self.status_label.configure(text=f"Error: {err}", text_color="red")
                return
            res = extractor.extract(html, custom_selector=self.selector_entry.get().strip())
            if res.success and res.price is not None:
                if not self.name_entry.get() and res.title:
                    self.name_entry.insert(0, res.title)
                self.status_label.configure(
                    text=f"Found: {res.currency} {res.price:.2f} ({'In Stock' if res.in_stock else 'Out'})",
                    text_color="green",
                )
            else:
                self.status_label.configure(text=f"Could not parse price: {res.error}", text_color="yellow")

        threading.Thread(target=run, daemon=True).start()

    def save_product(self) -> None:
        url = self.url_entry.get().strip()
        name = self.name_entry.get().strip()
        if not url:
            messagebox.showerror("Validation Error", "URL is required.")
            return
        if not name:
            name = url.split("/")[-1] or "New Product"

        target_price = None
        target_str = self.target_entry.get().strip()
        if target_str:
            try:
                target_price = float(target_str)
            except ValueError:
                messagebox.showerror("Validation Error", "Target price must be a valid number.")
                return

        currency = self.currency_entry.get().strip().upper() or "USD"
        tag = self.tag_entry.get().strip()
        selector = self.selector_entry.get().strip()

        product = Product(
            name=name,
            url=url,
            selector=selector,
            target_price=target_price,
            currency=currency,
            tag=tag,
        )

        if callable(self.on_save_callback):
            self.on_save_callback(product)

        self.destroy()


class PriceTrackerApp(ctk.CTk):
    def __init__(self, db: Database | None = None):
        super().__init__()
        self.db = db or Database()
        self.tracker = PriceTracker(db=self.db)
        self.exporter = Exporter()

        self.title("Price Tracker — Desktop Dashboard")
        self.geometry("980x680")
        self.minsize(860, 560)

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._build_sidebar()
        self._build_main_content()
        self.load_products_table()

    def _build_sidebar(self) -> None:
        self.sidebar_frame = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(6, weight=1)

        logo_label = ctk.CTkLabel(
            self.sidebar_frame, text="🏷️ Price Tracker", font=ctk.CTkFont(size=20, weight="bold")
        )
        logo_label.grid(row=0, column=0, padx=20, pady=(20, 20))

        self.btn_products = ctk.CTkButton(
            self.sidebar_frame, text="Products", command=lambda: self.switch_tab("products")
        )
        self.btn_products.grid(row=1, column=0, padx=20, pady=8)

        self.btn_history = ctk.CTkButton(
            self.sidebar_frame,
            text="History & Stats",
            fg_color="transparent",
            hover_color="#334155",
            command=lambda: self.switch_tab("history"),
        )
        self.btn_history.grid(row=2, column=0, padx=20, pady=8)

        self.btn_alerts = ctk.CTkButton(
            self.sidebar_frame,
            text="Alerts Feed",
            fg_color="transparent",
            hover_color="#334155",
            command=lambda: self.switch_tab("alerts"),
        )
        self.btn_alerts.grid(row=3, column=0, padx=20, pady=8)

        self.btn_export = ctk.CTkButton(
            self.sidebar_frame,
            text="Export Data",
            fg_color="transparent",
            hover_color="#334155",
            command=lambda: self.switch_tab("export"),
        )
        self.btn_export.grid(row=4, column=0, padx=20, pady=8)

    def _build_main_content(self) -> None:
        self.container = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.container.grid(row=0, column=1, sticky="nsew", padx=15, pady=15)
        self.container.grid_columnconfigure(0, weight=1)
        self.container.grid_rowconfigure(0, weight=1)

        self.tab_products = ctk.CTkFrame(self.container, fg_color="transparent")
        self.tab_history = ctk.CTkFrame(self.container, fg_color="transparent")
        self.tab_alerts = ctk.CTkFrame(self.container, fg_color="transparent")
        self.tab_export = ctk.CTkFrame(self.container, fg_color="transparent")

        self._setup_products_tab()
        self._setup_history_tab()
        self._setup_alerts_tab()
        self._setup_export_tab()

        self.tab_products.grid(row=0, column=0, sticky="nsew")

    def switch_tab(self, name: str) -> None:
        for tab in [self.tab_products, self.tab_history, self.tab_alerts, self.tab_export]:
            tab.grid_forget()

        self.btn_products.configure(fg_color="transparent")
        self.btn_history.configure(fg_color="transparent")
        self.btn_alerts.configure(fg_color="transparent")
        self.btn_export.configure(fg_color="transparent")

        if name == "products":
            self.tab_products.grid(row=0, column=0, sticky="nsew")
            self.btn_products.configure(fg_color=["#3B8ED0", "#1F6AA5"])
            self.load_products_table()
        elif name == "history":
            self.tab_history.grid(row=0, column=0, sticky="nsew")
            self.btn_history.configure(fg_color=["#3B8ED0", "#1F6AA5"])
            self.load_history_view()
        elif name == "alerts":
            self.tab_alerts.grid(row=0, column=0, sticky="nsew")
            self.btn_alerts.configure(fg_color=["#3B8ED0", "#1F6AA5"])
            self.load_alerts_table()
        elif name == "export":
            self.tab_export.grid(row=0, column=0, sticky="nsew")
            self.btn_export.configure(fg_color=["#3B8ED0", "#1F6AA5"])

    def _setup_products_tab(self) -> None:
        self.tab_products.grid_columnconfigure(0, weight=1)
        self.tab_products.grid_rowconfigure(1, weight=1)

        toolbar = ctk.CTkFrame(self.tab_products, fg_color="transparent")
        toolbar.grid(row=0, column=0, sticky="ew", pady=(0, 10))

        add_btn = ctk.CTkButton(toolbar, text="+ Add Product", width=120, command=self.open_add_dialog)
        add_btn.pack(side="left", padx=(0, 8))

        check_btn = ctk.CTkButton(
            toolbar,
            text="🔄 Check All Now",
            width=130,
            fg_color="#059669",
            hover_color="#047857",
            command=self.check_all_background,
        )
        check_btn.pack(side="left", padx=8)

        self.prod_status_label = ctk.CTkLabel(toolbar, text="", font=ctk.CTkFont(size=12), text_color="gray")
        self.prod_status_label.pack(side="left", padx=15)

        self.products_scroll = ctk.CTkScrollableFrame(self.tab_products)
        self.products_scroll.grid(row=1, column=0, sticky="nsew")
        self.products_scroll.grid_columnconfigure(0, weight=1)

    def _setup_history_tab(self) -> None:
        self.tab_history.grid_columnconfigure(0, weight=1)
        self.tab_history.grid_rowconfigure(2, weight=1)

        selector_frame = ctk.CTkFrame(self.tab_history, fg_color="transparent")
        selector_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))

        ctk.CTkLabel(selector_frame, text="Select Product:", font=ctk.CTkFont(weight="bold")).pack(
            side="left", padx=(0, 10)
        )
        self.product_combo = ctk.CTkOptionMenu(
            selector_frame, values=["(No products)"], command=self.on_product_selected, width=280
        )
        self.product_combo.pack(side="left", padx=5)

        self.stats_cards_frame = ctk.CTkFrame(self.tab_history)
        self.stats_cards_frame.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        self.stats_cards_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)

        self.card_current = self._create_stat_card(self.stats_cards_frame, "Current Price", "─", 0)
        self.card_lowest = self._create_stat_card(self.stats_cards_frame, "All-Time Low", "─", 1)
        self.card_target = self._create_stat_card(self.stats_cards_frame, "Target Price", "─", 2)
        self.card_change = self._create_stat_card(self.stats_cards_frame, "Total Change", "─", 3)

        self.history_scroll = ctk.CTkScrollableFrame(self.tab_history)
        self.history_scroll.grid(row=2, column=0, sticky="nsew")
        self.history_scroll.grid_columnconfigure(0, weight=1)

    def _create_stat_card(self, parent: ctk.CTkFrame, title: str, val: str, col: int) -> ctk.CTkLabel:
        frame = ctk.CTkFrame(parent, corner_radius=8)
        frame.grid(row=0, column=col, padx=5, pady=5, sticky="nsew")
        ctk.CTkLabel(frame, text=title, font=ctk.CTkFont(size=12, weight="normal"), text_color="gray").pack(pady=(8, 2))
        lbl = ctk.CTkLabel(frame, text=val, font=ctk.CTkFont(size=16, weight="bold"))
        lbl.pack(pady=(2, 8))
        return lbl

    def _setup_alerts_tab(self) -> None:
        self.tab_alerts.grid_columnconfigure(0, weight=1)
        self.tab_alerts.grid_rowconfigure(1, weight=1)

        toolbar = ctk.CTkFrame(self.tab_alerts, fg_color="transparent")
        toolbar.grid(row=0, column=0, sticky="ew", pady=(0, 10))

        clear_btn = ctk.CTkButton(
            toolbar,
            text="Clear All Alerts",
            width=120,
            fg_color="#dc2626",
            hover_color="#b91c1c",
            command=self.clear_alerts_ui,
        )
        clear_btn.pack(side="left", padx=5)

        self.alerts_scroll = ctk.CTkScrollableFrame(self.tab_alerts)
        self.alerts_scroll.grid(row=1, column=0, sticky="nsew")
        self.alerts_scroll.grid_columnconfigure(0, weight=1)

    def _setup_export_tab(self) -> None:
        self.tab_export.grid_columnconfigure(0, weight=1)

        header = ctk.CTkLabel(self.tab_export, text="Export & Reports", font=ctk.CTkFont(size=20, weight="bold"))
        header.pack(pady=(20, 20))

        box = ctk.CTkFrame(self.tab_export, width=500)
        box.pack(pady=10)

        json_btn = ctk.CTkButton(box, text="Export to JSON", width=220, command=lambda: self.run_export("json"))
        json_btn.pack(pady=10, padx=20)

        csv_btn = ctk.CTkButton(box, text="Export to CSV", width=220, command=lambda: self.run_export("csv"))
        csv_btn.pack(pady=10, padx=20)

        md_btn = ctk.CTkButton(box, text="Export to Markdown Report", width=220, command=lambda: self.run_export("md"))
        md_btn.pack(pady=10, padx=20)

        self.export_status_lbl = ctk.CTkLabel(self.tab_export, text="", font=ctk.CTkFont(size=13), text_color="gray")
        self.export_status_lbl.pack(pady=15)

    def load_products_table(self) -> None:
        for widget in self.products_scroll.winfo_children():
            widget.destroy()

        products = self.db.list_products()
        if not products:
            empty_lbl = ctk.CTkLabel(
                self.products_scroll,
                text="No products being tracked yet.\nClick '+ Add Product' to start tracking.",
                text_color="gray",
            )
            empty_lbl.pack(pady=40)
            return

        for p in products:
            card = ctk.CTkFrame(self.products_scroll, corner_radius=6)
            card.pack(fill="x", pady=4, padx=5)
            card.grid_columnconfigure(1, weight=1)

            badge_color = "#10b981" if p.in_stock else "#ef4444"
            badge_text = "IN STOCK" if p.in_stock else "OUT OF STOCK"
            badge = ctk.CTkLabel(
                card,
                text=badge_text,
                fg_color=badge_color,
                corner_radius=4,
                font=ctk.CTkFont(size=10, weight="bold"),
                width=80,
            )
            badge.grid(row=0, column=0, padx=10, pady=10)

            name_frame = ctk.CTkFrame(card, fg_color="transparent")
            name_frame.grid(row=0, column=1, sticky="w", padx=5)
            ctk.CTkLabel(name_frame, text=p.name, font=ctk.CTkFont(size=14, weight="bold"), anchor="w").pack(
                anchor="w"
            )
            ctk.CTkLabel(
                name_frame, text=p.url[:60] + ("..." if len(p.url) > 60 else ""), font=ctk.CTkFont(size=11), text_color="gray"
            ).pack(anchor="w")

            curr_price = f"{p.currency} {p.current_price:.2f}" if p.current_price is not None else "Unchecked"
            price_color = "#34d399" if (p.target_price and p.current_price and p.current_price <= p.target_price) else "white"
            price_lbl = ctk.CTkLabel(card, text=curr_price, font=ctk.CTkFont(size=16, weight="bold"), text_color=price_color)
            price_lbl.grid(row=0, column=2, padx=15)

            actions_frame = ctk.CTkFrame(card, fg_color="transparent")
            actions_frame.grid(row=0, column=3, padx=10)

            check_btn = ctk.CTkButton(
                actions_frame,
                text="Check",
                width=65,
                fg_color="#334155",
                hover_color="#475569",
                command=lambda pid=p.id: self.check_single_background(pid),
            )
            check_btn.pack(side="left", padx=4)

            del_btn = ctk.CTkButton(
                actions_frame,
                text="✕",
                width=35,
                fg_color="#dc2626",
                hover_color="#b91c1c",
                command=lambda pid=p.id: self.delete_product_ui(pid),
            )
            del_btn.pack(side="left", padx=2)

    def load_history_view(self) -> None:
        products = self.db.list_products()
        if not products:
            self.product_combo.configure(values=["(No products)"])
            self.product_combo.set("(No products)")
            return

        values = [f"{p.id}: {p.name}" for p in products]
        self.product_combo.configure(values=values)
        if values:
            self.product_combo.set(values[0])
            self.on_product_selected(values[0])

    def on_product_selected(self, choice: str) -> None:
        if not choice or ":" not in choice:
            return
        product_id = int(choice.split(":")[0])
        stats = self.db.get_product_stats(product_id)
        product = self.db.get_product(product_id)

        if not product or not stats:
            return

        c_str = f"{product.currency} {stats.current_price:.2f}" if stats.current_price else "─"
        l_str = f"{product.currency} {stats.lowest_price:.2f}" if stats.lowest_price else "─"
        t_str = f"{product.currency} {product.target_price:.2f}" if product.target_price else "─"
        ch_str = f"{stats.price_change_percentage:+.1f}%" if stats.price_change_percentage is not None else "0.0%"

        self.card_current.configure(text=c_str)
        self.card_lowest.configure(text=l_str)
        self.card_target.configure(text=t_str)
        self.card_change.configure(text=ch_str)

        for w in self.history_scroll.winfo_children():
            w.destroy()

        records = self.db.get_price_history(product_id)
        if not records:
            ctk.CTkLabel(self.history_scroll, text="No price recordings yet.", text_color="gray").pack(pady=20)
            return

        for r in reversed(records):
            row = ctk.CTkFrame(self.history_scroll, corner_radius=4)
            row.pack(fill="x", pady=2, padx=5)
            row.grid_columnconfigure(0, weight=1)

            time_str = r.recorded_at[:19].replace("T", " ")
            ctk.CTkLabel(row, text=time_str, font=ctk.CTkFont(size=12), text_color="gray").grid(
                row=0, column=0, sticky="w", padx=10, pady=6
            )
            ctk.CTkLabel(
                row, text=f"{r.currency} {r.price:.2f}", font=ctk.CTkFont(size=13, weight="bold")
            ).grid(row=0, column=1, padx=15, pady=6)
            stock_txt = "In Stock" if r.in_stock else "Out of Stock"
            ctk.CTkLabel(row, text=stock_txt, font=ctk.CTkFont(size=11), text_color="gray").grid(
                row=0, column=2, padx=10, pady=6
            )

    def load_alerts_table(self) -> None:
        for w in self.alerts_scroll.winfo_children():
            w.destroy()

        alerts = self.db.get_alerts(limit=50)
        if not alerts:
            ctk.CTkLabel(self.alerts_scroll, text="No alerts recorded yet.", text_color="gray").pack(pady=30)
            return

        for a in alerts:
            card = ctk.CTkFrame(self.alerts_scroll, corner_radius=6)
            card.pack(fill="x", pady=3, padx=5)
            card.grid_columnconfigure(1, weight=1)

            type_color = "#34d399" if "REACHED" in a.alert_type else "#fbbf24"
            ctk.CTkLabel(
                card,
                text=a.alert_type,
                fg_color=type_color,
                text_color="black",
                corner_radius=4,
                font=ctk.CTkFont(size=10, weight="bold"),
                width=110,
            ).grid(row=0, column=0, padx=10, pady=8)

            detail = ctk.CTkFrame(card, fg_color="transparent")
            detail.grid(row=0, column=1, sticky="w", padx=5)
            ctk.CTkLabel(detail, text=a.product_name, font=ctk.CTkFont(size=13, weight="bold"), anchor="w").pack(
                anchor="w"
            )
            ctk.CTkLabel(detail, text=a.message, font=ctk.CTkFont(size=11), text_color="gray", anchor="w").pack(
                anchor="w"
            )

            ctk.CTkLabel(
                card, text=f"{a.currency} {a.new_price:.2f}", font=ctk.CTkFont(size=14, weight="bold")
            ).grid(row=0, column=2, padx=15)

    def clear_alerts_ui(self) -> None:
        self.db.clear_alerts()
        self.load_alerts_table()

    def open_add_dialog(self) -> None:
        dialog = AddProductDialog(self, on_save_callback=self.on_product_added)
        dialog.grab_set()

    def on_product_added(self, product: Product) -> None:
        pid = self.db.add_product(product)
        self.load_products_table()
        self.check_single_background(pid)

    def check_single_background(self, product_id: int | None) -> None:
        if product_id is None:
            return
        self.prod_status_label.configure(text=f"Checking product #{product_id}...", text_color="cyan")

        def run():
            self.tracker.check_product(product_id)
            self.after(0, lambda: self.prod_status_label.configure(text="Check complete", text_color="green"))
            self.after(0, self.load_products_table)

        threading.Thread(target=run, daemon=True).start()

    def check_all_background(self) -> None:
        self.prod_status_label.configure(text="Checking all products...", text_color="cyan")

        def run():
            self.tracker.check_all(delay_seconds=0.3)
            self.after(0, lambda: self.prod_status_label.configure(text="All checked", text_color="green"))
            self.after(0, self.load_products_table)

        threading.Thread(target=run, daemon=True).start()

    def delete_product_ui(self, product_id: int | None) -> None:
        if product_id is None:
            return
        if messagebox.askyesno("Confirm Delete", f"Delete tracked product #{product_id}?"):
            self.db.delete_product(product_id)
            self.load_products_table()

    def run_export(self, fmt: str) -> None:
        products = self.db.list_products()
        if not products:
            self.export_status_lbl.configure(text="No products to export.", text_color="red")
            return

        if fmt == "json":
            history_map = {p.id: self.db.get_price_history(p.id) for p in products if p.id}
            path = self.exporter.export_json(products, history_map)
        elif fmt == "csv":
            path = self.exporter.export_csv(products)
        else:
            path = self.exporter.export_markdown(products)

        self.export_status_lbl.configure(text=f"Exported successfully to:\n{path}", text_color="green")


def run_gui() -> None:
    app = PriceTrackerApp()
    app.mainloop()


if __name__ == "__main__":
    run_gui()
