from datetime import datetime
from pathlib import Path
import threading
import time
from typing import List, Optional
import customtkinter as ctk
from tkinter import filedialog, messagebox

from website_monitor.checker import check_target
from website_monitor.db import (
    add_target,
    delete_target,
    get_all_target_stats,
    get_recent_checks,
    init_db,
    list_incidents,
    list_targets,
)
from website_monitor.engine import MonitorEngine
from website_monitor.exporter import export_to_csv, export_to_json, export_to_markdown, save_export
from website_monitor.models import CheckResult, MonitorTarget


class WebsiteMonitorGUI(ctk.CTk):
    def __init__(self):
        super().__init__()

        init_db()
        self.engine = MonitorEngine()
        self.is_monitoring_active = False
        self.monitor_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()

        self.title("Website Monitor — Uptime & Health Control Center")
        self.geometry("1100x720")
        self.minsize(900, 600)
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._build_sidebar()
        self._build_main_views()
        self.show_view("dashboard")
        self.refresh_data()

    def _build_sidebar(self):
        self.sidebar_frame = ctk.CTkFrame(self, width=220, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(7, weight=1)

        self.logo_label = ctk.CTkLabel(
            self.sidebar_frame,
            text="Website Monitor",
            font=ctk.CTkFont(size=20, weight="bold"),
        )
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 5))

        self.subtitle_label = ctk.CTkLabel(
            self.sidebar_frame,
            text="Uptime & SLA Watcher",
            font=ctk.CTkFont(size=12),
            text_color="gray",
        )
        self.subtitle_label.grid(row=1, column=0, padx=20, pady=(0, 20))

        self.btn_dashboard = ctk.CTkButton(
            self.sidebar_frame,
            text="📊  Dashboard",
            anchor="w",
            command=lambda: self.show_view("dashboard"),
        )
        self.btn_dashboard.grid(row=2, column=0, padx=15, pady=5, sticky="ew")

        self.btn_monitors = ctk.CTkButton(
            self.sidebar_frame,
            text="🌐  Monitors",
            anchor="w",
            command=lambda: self.show_view("monitors"),
        )
        self.btn_monitors.grid(row=3, column=0, padx=15, pady=5, sticky="ew")

        self.btn_incidents = ctk.CTkButton(
            self.sidebar_frame,
            text="🚨  Incidents",
            anchor="w",
            command=lambda: self.show_view("incidents"),
        )
        self.btn_incidents.grid(row=4, column=0, padx=15, pady=5, sticky="ew")

        self.btn_logs = ctk.CTkButton(
            self.sidebar_frame,
            text="📜  Live Logs",
            anchor="w",
            command=lambda: self.show_view("logs"),
        )
        self.btn_logs.grid(row=5, column=0, padx=15, pady=5, sticky="ew")

        self.btn_export = ctk.CTkButton(
            self.sidebar_frame,
            text="📁  Export Reports",
            anchor="w",
            command=lambda: self.show_view("export"),
        )
        self.btn_export.grid(row=6, column=0, padx=15, pady=5, sticky="ew")

        self.bottom_control_frame = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent")
        self.bottom_control_frame.grid(row=8, column=0, padx=15, pady=20, sticky="ew")

        self.btn_check_all = ctk.CTkButton(
            self.bottom_control_frame,
            text="⚡ Check All Now",
            fg_color="#1f538d",
            hover_color="#14375e",
            command=self.trigger_check_all,
        )
        self.btn_check_all.pack(fill="x", pady=5)

        self.switch_monitor = ctk.CTkSwitch(
            self.bottom_control_frame,
            text="Auto Monitoring",
            command=self.toggle_monitoring,
        )
        self.switch_monitor.pack(fill="x", pady=10)

    def _build_main_views(self):
        self.views = {}

        self.views["dashboard"] = ctk.CTkFrame(self, corner_radius=0)
        self._build_dashboard_view(self.views["dashboard"])

        self.views["monitors"] = ctk.CTkFrame(self, corner_radius=0)
        self._build_monitors_view(self.views["monitors"])

        self.views["incidents"] = ctk.CTkFrame(self, corner_radius=0)
        self._build_incidents_view(self.views["incidents"])

        self.views["logs"] = ctk.CTkFrame(self, corner_radius=0)
        self._build_logs_view(self.views["logs"])

        self.views["export"] = ctk.CTkFrame(self, corner_radius=0)
        self._build_export_view(self.views["export"])

    def show_view(self, view_name: str):
        for name, frame in self.views.items():
            if name == view_name:
                frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
            else:
                frame.grid_forget()
        self.refresh_data()

    def _build_dashboard_view(self, frame: ctk.CTkFrame):
        frame.grid_columnconfigure((0, 1, 2, 3), weight=1)
        frame.grid_rowconfigure(2, weight=1)

        title_label = ctk.CTkLabel(
            frame,
            text="System Health & SLA Overview",
            font=ctk.CTkFont(size=22, weight="bold"),
        )
        title_label.grid(row=0, column=0, columnspan=4, sticky="w", pady=(0, 15))

        self.card_total = self._create_kpi_card(frame, "Monitored", "0", 0)
        self.card_uptime = self._create_kpi_card(frame, "Avg Uptime", "100.0%", 1, color="#2ecc71")
        self.card_outages = self._create_kpi_card(frame, "Active Outages", "0", 2, color="#e74c3c")
        self.card_latency = self._create_kpi_card(frame, "Avg Latency", "0 ms", 3, color="#3498db")

        targets_section_label = ctk.CTkLabel(
            frame,
            text="Monitored Endpoints",
            font=ctk.CTkFont(size=16, weight="bold"),
        )
        targets_section_label.grid(row=1, column=0, columnspan=4, sticky="w", pady=(20, 5))

        self.dash_scroll_frame = ctk.CTkScrollableFrame(frame)
        self.dash_scroll_frame.grid(row=2, column=0, columnspan=4, sticky="nsew", pady=5)
        self.dash_scroll_frame.grid_columnconfigure(1, weight=1)

    def _create_kpi_card(
        self, parent: ctk.CTkFrame, title: str, default_val: str, col: int, color: Optional[str] = None
    ) -> ctk.CTkLabel:
        card = ctk.CTkFrame(parent, corner_radius=8)
        card.grid(row=1, column=col, padx=6, pady=5, sticky="ew")

        lbl_title = ctk.CTkLabel(card, text=title, font=ctk.CTkFont(size=12), text_color="gray")
        lbl_title.pack(padx=10, pady=(8, 0))

        lbl_val = ctk.CTkLabel(
            card,
            text=default_val,
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=color if color else "white",
        )
        lbl_val.pack(padx=10, pady=(2, 8))
        return lbl_val

    def _build_monitors_view(self, frame: ctk.CTkFrame):
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(1, weight=1)

        add_box = ctk.CTkFrame(frame)
        add_box.grid(row=0, column=0, sticky="ew", pady=(0, 15), padx=5)
        add_box.grid_columnconfigure(1, weight=1)

        lbl = ctk.CTkLabel(add_box, text="Add New Target", font=ctk.CTkFont(size=16, weight="bold"))
        lbl.grid(row=0, column=0, columnspan=4, sticky="w", padx=15, pady=(10, 5))

        ctk.CTkLabel(add_box, text="Name:").grid(row=1, column=0, padx=(15, 5), pady=5, sticky="e")
        self.entry_name = ctk.CTkEntry(add_box, placeholder_text="e.g. Production API")
        self.entry_name.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

        ctk.CTkLabel(add_box, text="URL:").grid(row=1, column=2, padx=(10, 5), pady=5, sticky="e")
        self.entry_url = ctk.CTkEntry(add_box, placeholder_text="https://api.example.com/health")
        self.entry_url.grid(row=1, column=3, padx=(5, 15), pady=5, sticky="ew")

        ctk.CTkLabel(add_box, text="Method:").grid(row=2, column=0, padx=(15, 5), pady=5, sticky="e")
        self.combo_method = ctk.CTkComboBox(add_box, values=["GET", "POST", "HEAD", "PUT"], width=100)
        self.combo_method.set("GET")
        self.combo_method.grid(row=2, column=1, padx=5, pady=5, sticky="w")

        ctk.CTkLabel(add_box, text="Keyword:").grid(row=2, column=2, padx=(10, 5), pady=5, sticky="e")
        self.entry_keyword = ctk.CTkEntry(add_box, placeholder_text="Expected text in body (optional)")
        self.entry_keyword.grid(row=2, column=3, padx=(5, 15), pady=5, sticky="ew")

        btn_save = ctk.CTkButton(
            add_box,
            text="+ Add Target",
            fg_color="#27ae60",
            hover_color="#1e8449",
            command=self.handle_add_target,
        )
        btn_save.grid(row=3, column=3, padx=(5, 15), pady=(5, 10), sticky="e")

        self.monitors_scroll = ctk.CTkScrollableFrame(frame)
        self.monitors_scroll.grid(row=1, column=0, sticky="nsew", padx=5)
        self.monitors_scroll.grid_columnconfigure(1, weight=1)

    def _build_incidents_view(self, frame: ctk.CTkFrame):
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(1, weight=1)

        header_frame = ctk.CTkFrame(frame, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        header_frame.grid_columnconfigure(0, weight=1)

        lbl = ctk.CTkLabel(header_frame, text="Outage & Incident History", font=ctk.CTkFont(size=20, weight="bold"))
        lbl.grid(row=0, column=0, sticky="w")

        btn_refresh = ctk.CTkButton(header_frame, text="↻ Refresh", width=90, command=self.refresh_incidents)
        btn_refresh.grid(row=0, column=1, sticky="e")

        self.incidents_scroll = ctk.CTkScrollableFrame(frame)
        self.incidents_scroll.grid(row=1, column=0, sticky="nsew")
        self.incidents_scroll.grid_columnconfigure(0, weight=1)

    def _build_logs_view(self, frame: ctk.CTkFrame):
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(1, weight=1)

        header_frame = ctk.CTkFrame(frame, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        header_frame.grid_columnconfigure(0, weight=1)

        lbl = ctk.CTkLabel(header_frame, text="Real-Time Health Check Log", font=ctk.CTkFont(size=20, weight="bold"))
        lbl.grid(row=0, column=0, sticky="w")

        btn_refresh = ctk.CTkButton(header_frame, text="↻ Refresh", width=90, command=self.refresh_logs)
        btn_refresh.grid(row=0, column=1, sticky="e")

        self.txt_logs = ctk.CTkTextbox(frame, wrap="none", font=ctk.CTkFont(family="Consolas", size=12))
        self.txt_logs.grid(row=1, column=0, sticky="nsew")

    def _build_export_view(self, frame: ctk.CTkFrame):
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(2, weight=1)

        lbl = ctk.CTkLabel(frame, text="Export Health & SLA Reports", font=ctk.CTkFont(size=20, weight="bold"))
        lbl.grid(row=0, column=0, sticky="w", pady=(0, 10))

        btn_box = ctk.CTkFrame(frame)
        btn_box.grid(row=1, column=0, sticky="ew", pady=(0, 15))

        btn_exp_md = ctk.CTkButton(btn_box, text="Export Markdown (.md)", command=lambda: self.do_export("md"))
        btn_exp_md.pack(side="left", padx=10, pady=10)

        btn_exp_json = ctk.CTkButton(btn_box, text="Export JSON (.json)", command=lambda: self.do_export("json"))
        btn_exp_json.pack(side="left", padx=10, pady=10)

        btn_exp_csv = ctk.CTkButton(btn_box, text="Export CSV (.csv)", command=lambda: self.do_export("csv"))
        btn_exp_csv.pack(side="left", padx=10, pady=10)

        self.txt_export_preview = ctk.CTkTextbox(frame, wrap="none", font=ctk.CTkFont(family="Consolas", size=12))
        self.txt_export_preview.grid(row=2, column=0, sticky="nsew")

    def handle_add_target(self):
        name = self.entry_name.get().strip()
        url = self.entry_url.get().strip()
        method = self.combo_method.get().strip()
        keyword = self.entry_keyword.get().strip() or None

        if not url:
            messagebox.showerror("Validation Error", "URL cannot be empty.")
            return

        try:
            target = MonitorTarget(url=url, name=name or url, method=method, keyword=keyword)
            add_target(target)
            self.entry_name.delete(0, "end")
            self.entry_url.delete(0, "end")
            self.entry_keyword.delete(0, "end")
            self.refresh_data()
            messagebox.showinfo("Success", f"Added monitor target: {target.name}")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def handle_delete_target(self, target_id: int):
        if messagebox.askyesno("Confirm Delete", "Are you sure you want to delete this target?"):
            delete_target(target_id)
            self.refresh_data()

    def handle_check_single(self, target: MonitorTarget):
        threading.Thread(target=self._run_single_check, args=(target,), daemon=True).start()

    def _run_single_check(self, target: MonitorTarget):
        self.engine.check_target_sync(target)
        self.after(0, self.refresh_data)

    def trigger_check_all(self):
        threading.Thread(target=self._run_check_all_thread, daemon=True).start()

    def _run_check_all_thread(self):
        self.engine.check_all()
        self.after(0, self.refresh_data)

    def toggle_monitoring(self):
        if self.switch_monitor.get() == 1:
            self.is_monitoring_active = True
            self.stop_event.clear()
            self.monitor_thread = threading.Thread(target=self._monitoring_worker, daemon=True)
            self.monitor_thread.start()
        else:
            self.is_monitoring_active = False
            self.stop_event.set()

    def _monitoring_worker(self):
        while not self.stop_event.is_set():
            self.engine.check_all()
            self.after(0, self.refresh_data)
            for _ in range(30):
                if self.stop_event.is_set():
                    break
                time.sleep(1)

    def refresh_data(self):
        self.refresh_dashboard()
        self.refresh_monitors()
        self.refresh_incidents()
        self.refresh_logs()
        self.refresh_export_preview()

    def refresh_dashboard(self):
        stats = get_all_target_stats(hours=24)
        total = len(stats)
        self.card_total.configure(text=str(total))

        if total > 0:
            avg_uptime = sum(s.uptime_percentage for s in stats) / total
            self.card_uptime.configure(text=f"{avg_uptime:.1f}%")
            outages = sum(1 for s in stats if s.active_incident)
            self.card_outages.configure(text=str(outages))
            avg_latency = sum(s.avg_latency_ms for s in stats) / total
            self.card_latency.configure(text=f"{avg_latency:.1f} ms")
        else:
            self.card_uptime.configure(text="100.0%")
            self.card_outages.configure(text="0")
            self.card_latency.configure(text="0 ms")

        for child in self.dash_scroll_frame.winfo_children():
            child.destroy()

        if not stats:
            lbl = ctk.CTkLabel(self.dash_scroll_frame, text="No monitors configured yet.", text_color="gray")
            lbl.pack(pady=20)
            return

        for s in stats:
            row_frame = ctk.CTkFrame(self.dash_scroll_frame)
            row_frame.pack(fill="x", padx=5, pady=4)
            row_frame.grid_columnconfigure(1, weight=1)

            status_color = "#2ecc71" if s.last_is_up is True else ("#e74c3c" if s.last_is_up is False else "gray")
            status_text = "UP" if s.last_is_up is True else ("DOWN" if s.last_is_up is False else "WAIT")

            badge = ctk.CTkLabel(
                row_frame,
                text=status_text,
                fg_color=status_color,
                text_color="white",
                corner_radius=6,
                width=50,
            )
            badge.grid(row=0, column=0, padx=10, pady=8)

            name_box = ctk.CTkFrame(row_frame, fg_color="transparent")
            name_box.grid(row=0, column=1, sticky="w", padx=5)

            ctk.CTkLabel(name_box, text=s.target_name, font=ctk.CTkFont(weight="bold")).pack(anchor="w")
            ctk.CTkLabel(name_box, text=s.target_url, text_color="gray", font=ctk.CTkFont(size=11)).pack(anchor="w")

            latency_text = f"{s.last_latency_ms:.1f} ms" if s.last_latency_ms is not None else "—"
            ctk.CTkLabel(row_frame, text=latency_text, width=80).grid(row=0, column=2, padx=10)

            uptime_color = "#2ecc71" if s.uptime_percentage >= 99.0 else "#f39c12"
            ctk.CTkLabel(
                row_frame,
                text=f"{s.uptime_percentage:.1f}%",
                text_color=uptime_color,
                font=ctk.CTkFont(weight="bold"),
                width=70,
            ).grid(row=0, column=3, padx=10)

    def refresh_monitors(self):
        targets = list_targets()
        for child in self.monitors_scroll.winfo_children():
            child.destroy()

        if not targets:
            lbl = ctk.CTkLabel(self.monitors_scroll, text="No targets yet. Add your first target above.", text_color="gray")
            lbl.pack(pady=20)
            return

        for t in targets:
            row_frame = ctk.CTkFrame(self.monitors_scroll)
            row_frame.pack(fill="x", padx=5, pady=4)
            row_frame.grid_columnconfigure(1, weight=1)

            method_lbl = ctk.CTkLabel(
                row_frame,
                text=t.method,
                font=ctk.CTkFont(size=11, weight="bold"),
                fg_color="#34495e",
                corner_radius=4,
                width=45,
            )
            method_lbl.grid(row=0, column=0, padx=10, pady=8)

            name_box = ctk.CTkFrame(row_frame, fg_color="transparent")
            name_box.grid(row=0, column=1, sticky="w", padx=5)

            ctk.CTkLabel(name_box, text=t.name, font=ctk.CTkFont(weight="bold")).pack(anchor="w")
            ctk.CTkLabel(name_box, text=t.url, text_color="gray", font=ctk.CTkFont(size=11)).pack(anchor="w")

            btn_check = ctk.CTkButton(
                row_frame,
                text="Check",
                width=65,
                fg_color="#2980b9",
                command=lambda target=t: self.handle_check_single(target),
            )
            btn_check.grid(row=0, column=2, padx=5)

            btn_del = ctk.CTkButton(
                row_frame,
                text="Delete",
                width=65,
                fg_color="#c0392b",
                hover_color="#922b21",
                command=lambda tid=t.id: self.handle_delete_target(tid),
            )
            btn_del.grid(row=0, column=3, padx=(5, 10))

    def refresh_incidents(self):
        incidents = list_incidents(limit=30)
        for child in self.incidents_scroll.winfo_children():
            child.destroy()

        if not incidents:
            lbl = ctk.CTkLabel(self.incidents_scroll, text="All systems nominal. No incidents recorded.", text_color="#2ecc71")
            lbl.pack(pady=30)
            return

        for inc in incidents:
            card = ctk.CTkFrame(self.incidents_scroll)
            card.pack(fill="x", padx=5, pady=4)
            card.grid_columnconfigure(1, weight=1)

            status_color = "#2ecc71" if inc.resolved else "#e74c3c"
            status_str = "RESOLVED" if inc.resolved else "ACTIVE OUTAGE"

            badge = ctk.CTkLabel(
                card,
                text=status_str,
                fg_color=status_color,
                text_color="white",
                corner_radius=6,
                width=110,
            )
            badge.grid(row=0, column=0, padx=10, pady=8)

            info_box = ctk.CTkFrame(card, fg_color="transparent")
            info_box.grid(row=0, column=1, sticky="w", padx=5)

            ctk.CTkLabel(info_box, text=inc.target_name or f"Target #{inc.target_id}", font=ctk.CTkFont(weight="bold")).pack(anchor="w")
            ctk.CTkLabel(info_box, text=f"Root cause: {inc.reason}", text_color="gray", font=ctk.CTkFont(size=11)).pack(anchor="w")

            dur_str = f"{int(inc.duration_seconds)}s" if inc.duration_seconds is not None else "Ongoing"
            ctk.CTkLabel(card, text=f"Duration: {dur_str}", width=100).grid(row=0, column=2, padx=10)

    def refresh_logs(self):
        logs = get_recent_checks(limit=60)
        self.txt_logs.delete("1.0", "end")
        lines = []
        for log in logs:
            st = "UP" if log.is_up else "DOWN"
            ts = log.checked_at.replace("T", " ")[:19]
            name = log.target_name or str(log.target_id)
            code_str = str(log.status_code) if log.status_code is not None else "ERR"
            line = f"[{ts}] [{st:4}] {name:<20} {code_str:<4} {log.response_time_ms:>6.1f}ms"
            if log.error_message:
                line += f" | {log.error_message}"
            lines.append(line)
        self.txt_logs.insert("1.0", "\n".join(lines))

    def refresh_export_preview(self):
        stats = get_all_target_stats(hours=24)
        incidents = list_incidents(limit=10)
        preview_text = export_to_markdown(stats, incidents)
        self.txt_export_preview.delete("1.0", "end")
        self.txt_export_preview.insert("1.0", preview_text)

    def do_export(self, fmt: str):
        stats = get_all_target_stats(hours=24)
        incidents = list_incidents(limit=50)

        ext_map = {"md": "*.md", "json": "*.json", "csv": "*.csv"}
        def_file = f"website_monitor_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{fmt}"

        file_path = filedialog.asksaveasfilename(
            defaultextension=f".{fmt}",
            initialfile=def_file,
            filetypes=[(f"{fmt.upper()} files", ext_map[fmt]), ("All files", "*.*")],
        )
        if not file_path:
            return

        if fmt == "json":
            content = export_to_json(stats, incidents)
        elif fmt == "csv":
            content = export_to_csv(stats)
        else:
            content = export_to_markdown(stats, incidents)

        save_export(content, Path(file_path))
        messagebox.showinfo("Export Successful", f"Saved report to:\n{file_path}")


def run_gui():
    app = WebsiteMonitorGUI()
    app.mainloop()


if __name__ == "__main__":
    run_gui()
