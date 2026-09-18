import json
from pathlib import Path
import threading
from tkinter import filedialog, messagebox
import customtkinter as ctk
from web_scraper.client import HttpClient
from web_scraper.engine import ScraperEngine
from web_scraper.exporter import DataExporter
from web_scraper.models import ItemRule, PaginationConfig, ScrapeJob
from web_scraper.parser import HtmlParser
from web_scraper.presets import get_preset, list_presets

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


class ScraperApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Web Scraper Engine")
        self.geometry("1100x720")
        self.minsize(950, 600)

        self.engine = ScraperEngine()
        self.scraped_items: list[dict] = []
        self.field_rules: list[ItemRule] = []

        self.setup_ui()
        self.load_default_rules()

    def setup_ui(self) -> None:
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.left_panel = ctk.CTkScrollableFrame(self, width=380, corner_radius=0)
        self.left_panel.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        self.setup_left_panel()

        self.right_panel = ctk.CTkFrame(self, corner_radius=0)
        self.right_panel.grid(row=0, column=1, sticky="nsew", padx=(0, 10), pady=10)
        self.right_panel.grid_columnconfigure(0, weight=1)
        self.right_panel.grid_rowconfigure(1, weight=1)

        self.setup_right_panel()

    def setup_left_panel(self) -> None:
        title_label = ctk.CTkLabel(
            self.left_panel,
            text="Scraper Configuration",
            font=ctk.CTkFont(size=18, weight="bold"),
        )
        title_label.pack(anchor="w", pady=(0, 12))

        preset_frame = ctk.CTkFrame(self.left_panel)
        preset_frame.pack(fill="x", pady=4)
        ctk.CTkLabel(preset_frame, text="Load Preset:").pack(side="left", padx=5)
        self.preset_menu = ctk.CTkOptionMenu(
            preset_frame,
            values=["(Custom)"] + list_presets(),
            command=self.on_preset_selected,
        )
        self.preset_menu.pack(side="right", fill="x", expand=True, padx=5)

        url_label = ctk.CTkLabel(self.left_panel, text="Target URL:")
        url_label.pack(anchor="w", pady=(8, 2))
        self.url_entry = ctk.CTkEntry(
            self.left_panel,
            placeholder_text="https://quotes.toscrape.com",
        )
        self.url_entry.pack(fill="x", pady=(0, 8))

        container_label = ctk.CTkLabel(self.left_panel, text="Container Selector (CSS):")
        container_label.pack(anchor="w", pady=(4, 2))
        self.container_entry = ctk.CTkEntry(
            self.left_panel,
            placeholder_text="div.quote",
        )
        self.container_entry.pack(fill="x", pady=(0, 8))

        rule_header = ctk.CTkFrame(self.left_panel, fg_color="transparent")
        rule_header.pack(fill="x", pady=(10, 4))
        ctk.CTkLabel(
            rule_header,
            text="Field Rules",
            font=ctk.CTkFont(weight="bold"),
        ).pack(side="left")
        add_rule_btn = ctk.CTkButton(
            rule_header,
            text="+ Add Field",
            width=80,
            height=24,
            command=self.open_add_rule_dialog,
        )
        add_rule_btn.pack(side="right")

        self.rules_frame = ctk.CTkFrame(self.left_panel)
        self.rules_frame.pack(fill="x", pady=4)

        pagination_label = ctk.CTkLabel(
            self.left_panel,
            text="Pagination",
            font=ctk.CTkFont(weight="bold"),
        )
        pagination_label.pack(anchor="w", pady=(12, 4))

        self.strategy_var = ctk.StringVar(value="next_link")
        strat_frame = ctk.CTkFrame(self.left_panel)
        strat_frame.pack(fill="x", pady=4)
        ctk.CTkRadioButton(
            strat_frame,
            text="Next Link",
            variable=self.strategy_var,
            value="next_link",
        ).pack(side="left", padx=5, pady=4)
        ctk.CTkRadioButton(
            strat_frame,
            text="Page Param",
            variable=self.strategy_var,
            value="page_param",
        ).pack(side="left", padx=5, pady=4)
        ctk.CTkRadioButton(
            strat_frame,
            text="None",
            variable=self.strategy_var,
            value="none",
        ).pack(side="left", padx=5, pady=4)

        next_label = ctk.CTkLabel(self.left_panel, text="Next Link Selector:")
        next_label.pack(anchor="w", pady=(4, 2))
        self.next_sel_entry = ctk.CTkEntry(
            self.left_panel,
            placeholder_text="li.next > a",
        )
        self.next_sel_entry.pack(fill="x", pady=(0, 8))

        limits_frame = ctk.CTkFrame(self.left_panel, fg_color="transparent")
        limits_frame.pack(fill="x", pady=4)
        limits_frame.grid_columnconfigure(0, weight=1)
        limits_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(limits_frame, text="Max Pages:").grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(limits_frame, text="Delay (s):").grid(row=0, column=1, sticky="w")

        self.pages_entry = ctk.CTkEntry(limits_frame)
        self.pages_entry.insert(0, "2")
        self.pages_entry.grid(row=1, column=0, sticky="ew", padx=(0, 4))

        self.delay_entry = ctk.CTkEntry(limits_frame)
        self.delay_entry.insert(0, "0.5")
        self.delay_entry.grid(row=1, column=1, sticky="ew", padx=(4, 0))

        options_frame = ctk.CTkFrame(self.left_panel, fg_color="transparent")
        options_frame.pack(fill="x", pady=8)

        self.robots_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            options_frame,
            text="Respect robots.txt",
            variable=self.robots_var,
        ).pack(anchor="w", pady=2)

        self.cache_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            options_frame,
            text="Cache responses to disk",
            variable=self.cache_var,
        ).pack(anchor="w", pady=2)

        action_frame = ctk.CTkFrame(self.left_panel, fg_color="transparent")
        action_frame.pack(fill="x", pady=(16, 8))
        action_frame.grid_columnconfigure(0, weight=1)
        action_frame.grid_columnconfigure(1, weight=1)

        self.start_btn = ctk.CTkButton(
            action_frame,
            text="Start Scraping",
            fg_color="#2e7d32",
            hover_color="#1b5e20",
            command=self.start_scraping,
        )
        self.start_btn.grid(row=0, column=0, sticky="ew", padx=(0, 4))

        self.cancel_btn = ctk.CTkButton(
            action_frame,
            text="Cancel",
            fg_color="#c62828",
            hover_color="#8e0000",
            state="disabled",
            command=self.cancel_scraping,
        )
        self.cancel_btn.grid(row=0, column=1, sticky="ew", padx=(4, 0))

    def setup_right_panel(self) -> None:
        top_bar = ctk.CTkFrame(self.right_panel, fg_color="transparent")
        top_bar.grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 4))

        self.status_label = ctk.CTkLabel(
            top_bar,
            text="Ready to scrape",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#90caf9",
        )
        self.status_label.pack(side="left", padx=6)

        self.progress_bar = ctk.CTkProgressBar(top_bar, width=180)
        self.progress_bar.set(0)
        self.progress_bar.pack(side="left", padx=10)

        export_menu = ctk.CTkOptionMenu(
            top_bar,
            values=["Export JSON", "Export CSV", "Export Markdown", "Export SQLite"],
            command=self.on_export_selected,
            width=130,
        )
        export_menu.pack(side="right", padx=6)

        self.tabs = ctk.CTkTabview(self.right_panel)
        self.tabs.grid(row=1, column=0, sticky="nsew", padx=8, pady=4)

        self.tab_results = self.tabs.add("Results Table")
        self.tab_json = self.tabs.add("JSON Viewer")
        self.tab_selector = self.tabs.add("Selector Tester")
        self.tab_logs = self.tabs.add("Logs")

        self.setup_results_tab()
        self.setup_json_tab()
        self.setup_selector_tab()
        self.setup_logs_tab()

    def setup_results_tab(self) -> None:
        self.tab_results.grid_columnconfigure(0, weight=1)
        self.tab_results.grid_rowconfigure(0, weight=1)

        self.results_textbox = ctk.CTkTextbox(self.tab_results, wrap="none")
        self.results_textbox.grid(row=0, column=0, sticky="nsew", padx=4, pady=4)

    def setup_json_tab(self) -> None:
        self.tab_json.grid_columnconfigure(0, weight=1)
        self.tab_json.grid_rowconfigure(0, weight=1)

        self.json_textbox = ctk.CTkTextbox(self.tab_json, wrap="none")
        self.json_textbox.grid(row=0, column=0, sticky="nsew", padx=4, pady=4)

    def setup_selector_tab(self) -> None:
        self.tab_selector.grid_columnconfigure(0, weight=1)
        self.tab_selector.grid_rowconfigure(2, weight=1)

        test_bar = ctk.CTkFrame(self.tab_selector, fg_color="transparent")
        test_bar.grid(row=0, column=0, sticky="ew", padx=4, pady=4)
        test_bar.grid_columnconfigure(0, weight=3)
        test_bar.grid_columnconfigure(1, weight=2)

        self.test_url_entry = ctk.CTkEntry(
            test_bar,
            placeholder_text="Target URL...",
        )
        self.test_url_entry.grid(row=0, column=0, sticky="ew", padx=(0, 4))

        self.test_sel_entry = ctk.CTkEntry(
            test_bar,
            placeholder_text="CSS Selector (e.g. h1, div.card, span.price)...",
        )
        self.test_sel_entry.grid(row=0, column=1, sticky="ew", padx=4)

        test_btn = ctk.CTkButton(
            test_bar,
            text="Test Selector",
            width=100,
            command=self.run_selector_test,
        )
        test_btn.grid(row=0, column=2, padx=(4, 0))

        self.test_results_box = ctk.CTkTextbox(self.tab_selector, wrap="none")
        self.test_results_box.grid(row=2, column=0, sticky="nsew", padx=4, pady=4)

    def setup_logs_tab(self) -> None:
        self.tab_logs.grid_columnconfigure(0, weight=1)
        self.tab_logs.grid_rowconfigure(0, weight=1)

        self.log_box = ctk.CTkTextbox(self.tab_logs, wrap="char")
        self.log_box.grid(row=0, column=0, sticky="nsew", padx=4, pady=4)

    def log(self, text: str) -> None:
        self.log_box.insert("end", f"{text}\n")
        self.log_box.see("end")

    def load_default_rules(self) -> None:
        self.url_entry.insert(0, "https://quotes.toscrape.com")
        self.container_entry.insert(0, "div.quote")
        self.next_sel_entry.insert(0, "li.next > a")

        self.field_rules = [
            ItemRule(name="quote", selector="span.text", extract="text"),
            ItemRule(name="author", selector="small.author", extract="text"),
            ItemRule(name="author_link", selector="span > a", extract="href"),
            ItemRule(name="tags", selector="div.tags", extract="text"),
        ]
        self.render_rules_list()

    def render_rules_list(self) -> None:
        for widget in self.rules_frame.winfo_children():
            widget.destroy()

        for idx, rule in enumerate(self.field_rules):
            row_frame = ctk.CTkFrame(self.rules_frame)
            row_frame.pack(fill="x", pady=2, padx=2)

            info_text = f"{rule.name} -> '{rule.selector}' ({rule.extract})"
            ctk.CTkLabel(
                row_frame,
                text=info_text,
                anchor="w",
                font=ctk.CTkFont(size=11),
            ).pack(side="left", padx=6, fill="x", expand=True)

            del_btn = ctk.CTkButton(
                row_frame,
                text="✕",
                width=24,
                height=20,
                fg_color="#c62828",
                hover_color="#8e0000",
                command=lambda i=idx: self.remove_rule(i),
            )
            del_btn.pack(side="right", padx=4)

    def remove_rule(self, index: int) -> None:
        if 0 <= index < len(self.field_rules):
            self.field_rules.pop(index)
            self.render_rules_list()

    def open_add_rule_dialog(self) -> None:
        dialog = ctk.CTkToplevel(self)
        dialog.title("Add Field Rule")
        dialog.geometry("380x360")
        dialog.transient(self)
        dialog.grab_set()

        ctk.CTkLabel(dialog, text="Field Name:").pack(anchor="w", padx=16, pady=(12, 2))
        name_entry = ctk.CTkEntry(dialog, placeholder_text="e.g. price")
        name_entry.pack(fill="x", padx=16, pady=(0, 6))

        ctk.CTkLabel(dialog, text="CSS Selector:").pack(anchor="w", padx=16, pady=(4, 2))
        sel_entry = ctk.CTkEntry(dialog, placeholder_text="e.g. span.price")
        sel_entry.pack(fill="x", padx=16, pady=(0, 6))

        ctk.CTkLabel(dialog, text="Extract Type:").pack(anchor="w", padx=16, pady=(4, 2))
        extract_menu = ctk.CTkOptionMenu(
            dialog,
            values=["text", "href", "src", "html", "attr"],
        )
        extract_menu.pack(fill="x", padx=16, pady=(0, 6))

        ctk.CTkLabel(dialog, text="Attr Name (if type=attr):").pack(anchor="w", padx=16, pady=(4, 2))
        attr_entry = ctk.CTkEntry(dialog, placeholder_text="e.g. data-id")
        attr_entry.pack(fill="x", padx=16, pady=(0, 6))

        ctk.CTkLabel(dialog, text="Type Cast:").pack(anchor="w", padx=16, pady=(4, 2))
        cast_menu = ctk.CTkOptionMenu(
            dialog,
            values=["str", "int", "float", "bool", "list"],
        )
        cast_menu.pack(fill="x", padx=16, pady=(0, 12))

        def on_save() -> None:
            f_name = name_entry.get().strip()
            f_sel = sel_entry.get().strip()
            if not f_name:
                messagebox.showerror("Error", "Field name is required")
                return
            new_rule = ItemRule(
                name=f_name,
                selector=f_sel,
                extract=extract_menu.get(),
                attr_name=attr_entry.get().strip() or None,
                cast=cast_menu.get(),
            )
            self.field_rules.append(new_rule)
            self.render_rules_list()
            dialog.destroy()

        ctk.CTkButton(dialog, text="Add Rule", command=on_save).pack(fill="x", padx=16, pady=8)

    def on_preset_selected(self, preset_name: str) -> None:
        if preset_name == "(Custom)":
            return
        preset = get_preset(preset_name)
        if not preset:
            return
        self.url_entry.delete(0, "end")
        self.url_entry.insert(0, preset.url)

        self.container_entry.delete(0, "end")
        if preset.container_selector:
            self.container_entry.insert(0, preset.container_selector)

        self.strategy_var.set(preset.pagination.strategy)
        self.next_sel_entry.delete(0, "end")
        if preset.pagination.next_selector:
            self.next_sel_entry.insert(0, preset.pagination.next_selector)

        self.field_rules = list(preset.rules)
        self.render_rules_list()
        self.log(f"Loaded preset '{preset_name}'.")

    def run_selector_test(self) -> None:
        url = self.test_url_entry.get().strip() or self.url_entry.get().strip()
        selector = self.test_sel_entry.get().strip()
        if not url or not selector:
            messagebox.showwarning("Warning", "Please provide both URL and Selector.")
            return

        self.test_results_box.delete("1.0", "end")
        self.test_results_box.insert("end", f"Fetching {url} to test '{selector}'...\n")

        def test_worker() -> None:
            client = HttpClient()
            resp = client.fetch(url)
            if not resp.is_success:
                self.after(
                    0,
                    lambda: self.test_results_box.insert(
                        "end",
                        f"Fetch failed: HTTP {resp.status_code}\n",
                    ),
                )
                return

            parser = HtmlParser()
            matches = parser.query_selector(resp.html, selector, limit=10)

            def show_results() -> None:
                self.test_results_box.delete("1.0", "end")
                self.test_results_box.insert(
                    "end",
                    f"Found {len(matches)} elements matching '{selector}':\n\n",
                )
                for idx, match in enumerate(matches, 1):
                    self.test_results_box.insert("end", f"--- Match {idx} [{match['tag']}] ---\n")
                    self.test_results_box.insert("end", f"Text: {match['text']}\n")
                    self.test_results_box.insert("end", f"Attrs: {json.dumps(match['attributes'])}\n")
                    self.test_results_box.insert("end", f"Snippet: {match['html_snippet']}\n\n")

            self.after(0, show_results)

        threading.Thread(target=test_worker, daemon=True).start()

    def start_scraping(self) -> None:
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showwarning("Warning", "Target URL cannot be empty.")
            return

        try:
            max_pages = int(self.pages_entry.get().strip())
        except ValueError:
            max_pages = 1

        try:
            delay = float(self.delay_entry.get().strip())
        except ValueError:
            delay = 0.5

        pagination = PaginationConfig(
            strategy=self.strategy_var.get(),
            next_selector=self.next_sel_entry.get().strip() or None,
            max_pages=max_pages,
        )

        job = ScrapeJob(
            url=url,
            container_selector=self.container_entry.get().strip() or None,
            rules=list(self.field_rules),
            pagination=pagination,
            rate_limit_delay=delay,
            respect_robots_txt=self.robots_var.get(),
            use_cache=self.cache_var.get(),
        )

        self.start_btn.configure(state="disabled")
        self.cancel_btn.configure(state="normal")
        self.status_label.configure(text="Scraping in progress...", text_color="#ffb74d")
        self.progress_bar.set(0)
        self.log(f"Starting scrape job for: {url}")
        self.engine.reset_cancellation()

        def worker() -> None:
            def on_progress(page: int, count: int, curr_url: str) -> None:
                def update_ui() -> None:
                    pct = min(1.0, page / max(1, max_pages))
                    self.progress_bar.set(pct)
                    self.status_label.configure(
                        text=f"Page {page}/{max_pages} ({count} items)",
                    )
                    self.log(f"Fetched page {page}: {curr_url} ({count} items)")

                self.after(0, update_ui)

            result = self.engine.run(job, progress_callback=on_progress)

            def finalize_ui() -> None:
                self.scraped_items = result.items
                self.start_btn.configure(state="normal")
                self.cancel_btn.configure(state="disabled")
                self.progress_bar.set(1.0)
                self.status_label.configure(
                    text=f"Finished! {result.total_items} items in {result.duration_seconds:.2f}s",
                    text_color="#81c784",
                )
                self.log(
                    f"Job completed. Scraped {result.total_items} items across {result.total_pages} page(s).",
                )

                if result.errors:
                    for err in result.errors:
                        self.log(f"Error: {err}")

                self.render_scraped_data()

            self.after(0, finalize_ui)

        threading.Thread(target=worker, daemon=True).start()

    def cancel_scraping(self) -> None:
        self.engine.cancel()
        self.status_label.configure(text="Cancelling...", text_color="#e57373")
        self.log("Cancellation requested...")

    def render_scraped_data(self) -> None:
        self.json_textbox.delete("1.0", "end")
        self.json_textbox.insert(
            "end",
            json.dumps(self.scraped_items, indent=2, ensure_ascii=False),
        )

        self.results_textbox.delete("1.0", "end")
        if not self.scraped_items:
            self.results_textbox.insert("end", "No items scraped.")
            return

        keys = list(self.scraped_items[0].keys())
        col_width = 24
        header_row = "".join(f"{k[:col_width - 2]:<{col_width}}" for k in keys)
        separator = "=" * len(header_row)

        self.results_textbox.insert("end", f"{header_row}\n{separator}\n")

        for item in self.scraped_items:
            row_str = "".join(
                f"{str(item.get(k, ''))[:col_width - 2]:<{col_width}}"
                for k in keys
            )
            self.results_textbox.insert("end", f"{row_str}\n")

    def on_export_selected(self, choice: str) -> None:
        if not self.scraped_items:
            messagebox.showinfo("Export", "No scraped items to export.")
            return

        if "JSON" in choice:
            file_path = filedialog.asksaveasfilename(
                defaultextension=".json",
                filetypes=[("JSON Files", "*.json")],
            )
            if file_path:
                DataExporter.export_json(self.scraped_items, file_path)
                messagebox.showinfo("Exported", f"Exported to {file_path}")
        elif "CSV" in choice:
            file_path = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV Files", "*.csv")],
            )
            if file_path:
                DataExporter.export_csv(self.scraped_items, file_path)
                messagebox.showinfo("Exported", f"Exported to {file_path}")
        elif "Markdown" in choice:
            file_path = filedialog.asksaveasfilename(
                defaultextension=".md",
                filetypes=[("Markdown Files", "*.md")],
            )
            if file_path:
                DataExporter.export_markdown(self.scraped_items, file_path)
                messagebox.showinfo("Exported", f"Exported to {file_path}")
        elif "SQLite" in choice:
            file_path = filedialog.asksaveasfilename(
                defaultextension=".db",
                filetypes=[("SQLite DB", "*.db;*.sqlite")],
            )
            if file_path:
                DataExporter.export_sqlite(self.scraped_items, file_path)
                messagebox.showinfo("Exported", f"Exported to {file_path}")


def run_gui() -> None:
    app = ScraperApp()
    app.mainloop()


if __name__ == "__main__":
    run_gui()
