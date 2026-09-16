import json
from pathlib import Path
import threading
from tkinter import filedialog, messagebox
from typing import Any, Dict, List, Optional
import customtkinter as ctk

from api_cli.client import execute_request
from api_cli.config import DEFAULT_TIMEOUT_SECONDS
from api_cli.db import (
    clear_history,
    get_active_environment,
    get_environment,
    list_environments,
    list_history,
    list_saved_requests,
    save_request,
    set_active_environment,
)
from api_cli.exporter import export_data
from api_cli.filter import FilterError, filter_payload
from api_cli.models import Environment, RequestConfig, ResponseResult, SavedRequest


class UniversalApiApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Universal API Client")
        self.geometry("1100x750")
        self.minsize(900, 600)
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")

        self.last_response: Optional[ResponseResult] = None
        self.last_display_data: Optional[Any] = None

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._build_sidebar()
        self._build_main_panel()
        self._refresh_environments()
        self._refresh_saved_requests()
        self._refresh_history()

    def _build_sidebar(self) -> None:
        sidebar = ctk.CTkFrame(self, width=240, corner_radius=0)
        sidebar.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        sidebar.grid_rowconfigure(6, weight=1)

        title_label = ctk.CTkLabel(sidebar, text="API Explorer", font=ctk.CTkFont(size=20, weight="bold"))
        title_label.grid(row=0, column=0, padx=15, pady=(20, 10), sticky="w")

        env_label = ctk.CTkLabel(sidebar, text="Active Environment", font=ctk.CTkFont(size=12, weight="bold"))
        env_label.grid(row=1, column=0, padx=15, pady=(5, 0), sticky="w")

        self.env_combobox = ctk.CTkComboBox(sidebar, values=["None"], command=self._on_env_changed)
        self.env_combobox.grid(row=2, column=0, padx=15, pady=(5, 15), sticky="ew")

        saved_label = ctk.CTkLabel(sidebar, text="Saved Requests", font=ctk.CTkFont(size=12, weight="bold"))
        saved_label.grid(row=3, column=0, padx=15, pady=(5, 0), sticky="w")

        self.saved_scroll = ctk.CTkScrollableFrame(sidebar, height=160)
        self.saved_scroll.grid(row=4, column=0, padx=15, pady=(5, 15), sticky="ew")

        history_label = ctk.CTkLabel(sidebar, text="Recent History", font=ctk.CTkFont(size=12, weight="bold"))
        history_label.grid(row=5, column=0, padx=15, pady=(5, 0), sticky="w")

        self.history_scroll = ctk.CTkScrollableFrame(sidebar)
        self.history_scroll.grid(row=6, column=0, padx=15, pady=(5, 10), sticky="nsew")

        clear_hist_btn = ctk.CTkButton(sidebar, text="Clear History", fg_color="#444444", hover_color="#555555", command=self._on_clear_history)
        clear_hist_btn.grid(row=7, column=0, padx=15, pady=(0, 15), sticky="ew")

    def _build_main_panel(self) -> None:
        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.grid(row=0, column=1, sticky="nsew", padx=15, pady=15)
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_rowconfigure(2, weight=1)

        req_bar = ctk.CTkFrame(main_frame)
        req_bar.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        req_bar.grid_columnconfigure(1, weight=1)

        self.method_combobox = ctk.CTkComboBox(req_bar, values=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD"], width=100)
        self.method_combobox.grid(row=0, column=0, padx=(10, 5), pady=10)
        self.method_combobox.set("GET")

        self.url_entry = ctk.CTkEntry(req_bar, placeholder_text="https://api.example.com/v1/resource or {{base_url}}/users")
        self.url_entry.grid(row=0, column=1, padx=5, pady=10, sticky="ew")

        self.send_button = ctk.CTkButton(req_bar, text="Send", width=100, command=self._on_send_clicked)
        self.send_button.grid(row=0, column=2, padx=(5, 10), pady=10)

        self.req_tabview = ctk.CTkTabview(main_frame, height=150)
        self.req_tabview.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        self.req_tabview.add("Params")
        self.req_tabview.add("Headers")
        self.req_tabview.add("Body")
        self.req_tabview.add("Save")

        self.params_textbox = ctk.CTkTextbox(self.req_tabview.tab("Params"), height=80)
        self.params_textbox.pack(fill="both", expand=True, padx=5, pady=5)
        self.params_textbox.insert("0.0", "# Format: key=value (one per line)\n")

        self.headers_textbox = ctk.CTkTextbox(self.req_tabview.tab("Headers"), height=80)
        self.headers_textbox.pack(fill="both", expand=True, padx=5, pady=5)
        self.headers_textbox.insert("0.0", "Content-Type: application/json\n")

        self.body_textbox = ctk.CTkTextbox(self.req_tabview.tab("Body"), height=80)
        self.body_textbox.pack(fill="both", expand=True, padx=5, pady=5)

        save_tab = self.req_tabview.tab("Save")
        self.save_name_entry = ctk.CTkEntry(save_tab, placeholder_text="Saved Request Name (e.g. List Users)")
        self.save_name_entry.pack(side="left", fill="x", expand=True, padx=5, pady=10)
        save_btn = ctk.CTkButton(save_tab, text="Save Request", command=self._on_save_request_clicked)
        save_btn.pack(side="right", padx=5, pady=10)

        resp_container = ctk.CTkFrame(main_frame)
        resp_container.grid(row=2, column=0, sticky="nsew")
        resp_container.grid_columnconfigure(0, weight=1)
        resp_container.grid_rowconfigure(2, weight=1)

        meta_bar = ctk.CTkFrame(resp_container, fg_color="transparent")
        meta_bar.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))
        meta_bar.grid_columnconfigure(3, weight=1)

        self.status_badge = ctk.CTkLabel(meta_bar, text="Status: Ready", font=ctk.CTkFont(weight="bold"))
        self.status_badge.grid(row=0, column=0, padx=(0, 15))

        self.latency_badge = ctk.CTkLabel(meta_bar, text="Time: 0ms")
        self.latency_badge.grid(row=0, column=1, padx=(0, 15))

        self.size_badge = ctk.CTkLabel(meta_bar, text="Size: 0 B")
        self.size_badge.grid(row=0, column=2, padx=(0, 15))

        export_frame = ctk.CTkFrame(meta_bar, fg_color="transparent")
        export_frame.grid(row=0, column=4, sticky="e")
        ctk.CTkButton(export_frame, text="Export JSON", width=80, command=lambda: self._export_as("json")).pack(side="left", padx=2)
        ctk.CTkButton(export_frame, text="Export CSV", width=80, command=lambda: self._export_as("csv")).pack(side="left", padx=2)
        ctk.CTkButton(export_frame, text="Export MD", width=80, command=lambda: self._export_as("md")).pack(side="left", padx=2)

        filter_bar = ctk.CTkFrame(resp_container, fg_color="transparent")
        filter_bar.grid(row=1, column=0, sticky="ew", padx=10, pady=5)
        filter_bar.grid_columnconfigure(0, weight=1)

        self.filter_entry = ctk.CTkEntry(filter_bar, placeholder_text="JMESPath filter expression (e.g. items[?active].id or data.user)")
        self.filter_entry.grid(row=0, column=0, sticky="ew", padx=(0, 5))

        ctk.CTkButton(filter_bar, text="Filter", width=70, command=self._apply_filter).grid(row=0, column=1, padx=2)
        ctk.CTkButton(filter_bar, text="Reset", width=70, fg_color="#444444", hover_color="#555555", command=self._reset_filter).grid(row=0, column=2, padx=(2, 0))

        self.resp_tabview = ctk.CTkTabview(resp_container)
        self.resp_tabview.grid(row=2, column=0, sticky="nsew", padx=10, pady=(0, 10))
        self.resp_tabview.add("Response Body")
        self.resp_tabview.add("Headers")

        self.resp_body_textbox = ctk.CTkTextbox(self.resp_tabview.tab("Response Body"), wrap="none")
        self.resp_body_textbox.pack(fill="both", expand=True, padx=5, pady=5)

        self.resp_headers_textbox = ctk.CTkTextbox(self.resp_tabview.tab("Headers"), wrap="none")
        self.resp_headers_textbox.pack(fill="both", expand=True, padx=5, pady=5)

    def _refresh_environments(self) -> None:
        envs = list_environments()
        names = ["None"] + [e.name for e in envs]
        self.env_combobox.configure(values=names)
        active = get_active_environment()
        self.env_combobox.set(active if active in names else "None")

    def _refresh_saved_requests(self) -> None:
        for widget in self.saved_scroll.winfo_children():
            widget.destroy()

        saved_list = list_saved_requests()
        if not saved_list:
            lbl = ctk.CTkLabel(self.saved_scroll, text="No saved requests", text_color="gray")
            lbl.pack(pady=10)
            return

        for req in saved_list:
            btn = ctk.CTkButton(
                self.saved_scroll,
                text=f"{req.method} {req.name}",
                anchor="w",
                fg_color="#2b2b2b",
                hover_color="#3b3b3b",
                command=lambda r=req: self._load_saved_request(r),
            )
            btn.pack(fill="x", pady=2)

    def _refresh_history(self) -> None:
        for widget in self.history_scroll.winfo_children():
            widget.destroy()

        entries = list_history(limit=25)
        if not entries:
            lbl = ctk.CTkLabel(self.history_scroll, text="No history", text_color="gray")
            lbl.pack(pady=10)
            return

        for entry in entries:
            code_str = str(entry.status_code) if entry.status_code else "ERR"
            text_val = f"[{code_str}] {entry.method} {entry.url[:22]}..."
            btn = ctk.CTkButton(
                self.history_scroll,
                text=text_val,
                anchor="w",
                fg_color="#222222",
                hover_color="#333333",
                command=lambda e=entry: self._load_history_entry(e),
            )
            btn.pack(fill="x", pady=2)

    def _on_env_changed(self, choice: str) -> None:
        selected = None if choice == "None" else choice
        set_active_environment(selected)

    def _load_saved_request(self, req: SavedRequest) -> None:
        self.method_combobox.set(req.method)
        self.url_entry.delete(0, "end")
        self.url_entry.insert(0, req.url)

        self.headers_textbox.delete("0.0", "end")
        for k, v in req.headers.items():
            self.headers_textbox.insert("end", f"{k}: {v}\n")

        self.params_textbox.delete("0.0", "end")
        for k, v in req.query_params.items():
            self.params_textbox.insert("end", f"{k}={v}\n")

        self.body_textbox.delete("0.0", "end")
        if req.body:
            self.body_textbox.insert("0.0", req.body)

    def _load_history_entry(self, entry: Any) -> None:
        self.method_combobox.set(entry.method)
        self.url_entry.delete(0, "end")
        self.url_entry.insert(0, entry.url)

        self.headers_textbox.delete("0.0", "end")
        for k, v in entry.request_headers.items():
            self.headers_textbox.insert("end", f"{k}: {v}\n")

        self.body_textbox.delete("0.0", "end")
        if entry.request_body:
            self.body_textbox.insert("0.0", entry.request_body)

    def _on_save_request_clicked(self) -> None:
        name = self.save_name_entry.get().strip()
        url = self.url_entry.get().strip()
        if not name or not url:
            messagebox.showwarning("Input Required", "Please provide a name and URL to save.")
            return

        method = self.method_combobox.get()
        headers = self._parse_textbox_pairs(self.headers_textbox.get("0.0", "end"))
        params = self._parse_textbox_pairs(self.params_textbox.get("0.0", "end"))
        body = self.body_textbox.get("0.0", "end").strip() or None
        active_env = get_active_environment()

        req = SavedRequest(
            name=name,
            method=method,
            url=url,
            headers=headers,
            query_params=params,
            body=body,
            env_name=active_env,
            created_at="",
        )
        save_request(req)
        self._refresh_saved_requests()
        messagebox.showinfo("Saved", f"Saved request '{name}' successfully.")

    def _on_clear_history(self) -> None:
        clear_history()
        self._refresh_history()

    def _parse_textbox_pairs(self, text: str) -> Dict[str, str]:
        pairs: Dict[str, str] = {}
        for line in text.splitlines():
            clean = line.strip()
            if not clean or clean.startswith("#"):
                continue
            if ":" in clean:
                k, v = clean.split(":", 1)
                pairs[k.strip()] = v.strip()
            elif "=" in clean:
                k, v = clean.split("=", 1)
                pairs[k.strip()] = v.strip()
        return pairs

    def _on_send_clicked(self) -> None:
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showwarning("Missing URL", "Please enter a valid request URL.")
            return

        method = self.method_combobox.get()
        headers = self._parse_textbox_pairs(self.headers_textbox.get("0.0", "end"))
        params = self._parse_textbox_pairs(self.params_textbox.get("0.0", "end"))
        body_text = self.body_textbox.get("0.0", "end").strip()
        body = body_text if body_text else None

        config = RequestConfig(
            method=method,
            url=url,
            headers=headers,
            query_params=params,
            body=body,
            timeout=DEFAULT_TIMEOUT_SECONDS,
        )

        self.send_button.configure(state="disabled", text="Sending...")
        thread = threading.Thread(target=self._execute_request_worker, args=(config,), daemon=True)
        thread.start()

    def _execute_request_worker(self, config: RequestConfig) -> None:
        active_env = get_active_environment()
        try:
            result = execute_request(config, env_name=active_env, save_to_history=True)
            self.after(0, self._on_request_complete, result)
        except Exception as exc:
            self.after(0, self._on_request_error, str(exc))

    def _on_request_complete(self, result: ResponseResult) -> None:
        self.send_button.configure(state="normal", text="Send")
        self.last_response = result
        self.last_display_data = result.parsed_json() if result.parsed_json() is not None else result.body

        status_text = f"Status: {result.status_code} {result.reason_phrase}"
        color = "#4CAF50" if result.is_success else ("#F44336" if result.is_error else "#FF9800")
        self.status_badge.configure(text=status_text, text_color=color)
        self.latency_badge.configure(text=f"Time: {result.latency_ms:.1f}ms")
        self.size_badge.configure(text=f"Size: {result.size_bytes} B")

        self.resp_headers_textbox.delete("0.0", "end")
        for k, v in result.headers.items():
            self.resp_headers_textbox.insert("end", f"{k}: {v}\n")

        self._render_body_display(self.last_display_data)
        self._refresh_history()

    def _on_request_error(self, error_msg: str) -> None:
        self.send_button.configure(state="normal", text="Send")
        self.status_badge.configure(text="Status: Error", text_color="#F44336")
        self.resp_body_textbox.delete("0.0", "end")
        self.resp_body_textbox.insert("0.0", f"Error executing request:\n{error_msg}")

    def _render_body_display(self, data: Any) -> None:
        self.resp_body_textbox.delete("0.0", "end")
        if isinstance(data, (dict, list)):
            formatted = json.dumps(data, indent=2)
            self.resp_body_textbox.insert("0.0", formatted)
        else:
            self.resp_body_textbox.insert("0.0", str(data))

    def _apply_filter(self) -> None:
        if not self.last_response:
            return
        expr = self.filter_entry.get().strip()
        parsed = self.last_response.parsed_json()
        if parsed is None:
            messagebox.showinfo("Not JSON", "Response payload is not valid JSON to filter.")
            return

        try:
            filtered = filter_payload(parsed, expression=expr)
            self.last_display_data = filtered
            self._render_body_display(filtered)
        except FilterError as err:
            messagebox.showerror("Filter Error", str(err))

    def _reset_filter(self) -> None:
        self.filter_entry.delete(0, "end")
        if self.last_response:
            self.last_display_data = self.last_response.parsed_json() or self.last_response.body
            self._render_body_display(self.last_display_data)

    def _export_as(self, fmt: str) -> None:
        if self.last_display_data is None:
            messagebox.showwarning("No Data", "No response data available to export.")
            return

        file_types = {
            "json": ("JSON files", "*.json"),
            "csv": ("CSV files", "*.csv"),
            "md": ("Markdown files", "*.md"),
        }
        ext = f".{fmt}"
        target_path = filedialog.asksaveasfilename(
            defaultextension=ext,
            filetypes=[file_types.get(fmt, ("All files", "*.*"))],
        )
        if not target_path:
            return

        saved_path = export_data(self.last_display_data, target_path, format_hint=fmt)
        messagebox.showinfo("Export Successful", f"File exported successfully to:\n{saved_path}")


def run_gui() -> None:
    app = UniversalApiApp()
    app.mainloop()


if __name__ == "__main__":
    run_gui()
