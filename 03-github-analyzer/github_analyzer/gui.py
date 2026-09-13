import os
import threading
import tkinter.filedialog as filedialog
import tkinter.messagebox as messagebox
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import customtkinter

from github_analyzer.analyzer import (
    analyze_repo,
    analyze_user,
    compare_repositories,
    compare_users,
)
from github_analyzer.cache import ResponseCache
from github_analyzer.client import (
    AuthenticationError,
    GitHubAPIError,
    GitHubClient,
    RateLimitExceededError,
    ResourceNotFoundError,
)
from github_analyzer.exporter import (
    export_repo_to_json,
    export_repo_to_markdown,
    export_user_to_json,
    export_user_to_markdown,
    save_export_file,
)
from github_analyzer.models import ComparisonResult, RepoAnalysis, UserAnalysis

customtkinter.set_appearance_mode("Dark")
customtkinter.set_default_color_theme("blue")


class GitHubAnalyzerApp(customtkinter.CTk):
    def __init__(self):
        super().__init__()
        self.title("GitHub Analyzer — Desktop Dashboard")
        self.geometry("1000x720")
        self.minsize(850, 600)

        self.cache = ResponseCache()
        self.client = GitHubClient(cache=self.cache, use_cache=True)

        self.last_user_analysis: Optional[UserAnalysis] = None
        self.last_repo_analysis: Optional[RepoAnalysis] = None

        self._build_ui()
        self._refresh_rate_limit_async()

    def _build_ui(self) -> None:
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.tabview = customtkinter.CTkTabview(self)
        self.tabview.grid(row=0, column=0, padx=15, pady=15, sticky="nsew")

        self.tab_user = self.tabview.add("User Analysis")
        self.tab_repo = self.tabview.add("Repository Analysis")
        self.tab_compare = self.tabview.add("Comparison")
        self.tab_settings = self.tabview.add("Rate Limits & Settings")

        self._build_user_tab()
        self._build_repo_tab()
        self._build_compare_tab()
        self._build_settings_tab()

    def _build_user_tab(self) -> None:
        self.tab_user.grid_columnconfigure(0, weight=1)
        self.tab_user.grid_rowconfigure(1, weight=1)

        control_frame = customtkinter.CTkFrame(self.tab_user)
        control_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        control_frame.grid_columnconfigure(1, weight=1)

        lbl = customtkinter.CTkLabel(control_frame, text="Username:", font=customtkinter.CTkFont(weight="bold"))
        lbl.grid(row=0, column=0, padx=10, pady=10)

        self.user_entry = customtkinter.CTkEntry(control_frame, placeholder_text="e.g. octocat, torvalds")
        self.user_entry.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
        self.user_entry.bind("<Return>", lambda event: self._on_analyze_user())

        self.include_forks_var = customtkinter.BooleanVar(value=False)
        fork_chk = customtkinter.CTkCheckBox(control_frame, text="Include Forks", variable=self.include_forks_var)
        fork_chk.grid(row=0, column=2, padx=10, pady=10)

        self.user_btn = customtkinter.CTkButton(control_frame, text="Analyze User", command=self._on_analyze_user)
        self.user_btn.grid(row=0, column=3, padx=10, pady=10)

        self.user_export_btn = customtkinter.CTkButton(
            control_frame,
            text="Export Report",
            state="disabled",
            fg_color="transparent",
            border_width=1,
            command=self._on_export_user,
        )
        self.user_export_btn.grid(row=0, column=4, padx=10, pady=10)

        self.user_status_label = customtkinter.CTkLabel(control_frame, text="")
        self.user_status_label.grid(row=1, column=0, columnspan=5, padx=10, pady=(0, 5))

        self.user_content_frame = customtkinter.CTkScrollableFrame(self.tab_user)
        self.user_content_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        self.user_content_frame.grid_columnconfigure(0, weight=1)

    def _build_repo_tab(self) -> None:
        self.tab_repo.grid_columnconfigure(0, weight=1)
        self.tab_repo.grid_rowconfigure(1, weight=1)

        control_frame = customtkinter.CTkFrame(self.tab_repo)
        control_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        control_frame.grid_columnconfigure(1, weight=1)

        lbl = customtkinter.CTkLabel(control_frame, text="Repository:", font=customtkinter.CTkFont(weight="bold"))
        lbl.grid(row=0, column=0, padx=10, pady=10)

        self.repo_entry = customtkinter.CTkEntry(control_frame, placeholder_text="e.g. pallets/click, octocat/Spoon-Knife")
        self.repo_entry.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
        self.repo_entry.bind("<Return>", lambda event: self._on_analyze_repo())

        self.repo_btn = customtkinter.CTkButton(control_frame, text="Analyze Repo", command=self._on_analyze_repo)
        self.repo_btn.grid(row=0, column=2, padx=10, pady=10)

        self.repo_export_btn = customtkinter.CTkButton(
            control_frame,
            text="Export Report",
            state="disabled",
            fg_color="transparent",
            border_width=1,
            command=self._on_export_repo,
        )
        self.repo_export_btn.grid(row=0, column=3, padx=10, pady=10)

        self.repo_status_label = customtkinter.CTkLabel(control_frame, text="")
        self.repo_status_label.grid(row=1, column=0, columnspan=4, padx=10, pady=(0, 5))

        self.repo_content_frame = customtkinter.CTkScrollableFrame(self.tab_repo)
        self.repo_content_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        self.repo_content_frame.grid_columnconfigure(0, weight=1)

    def _build_compare_tab(self) -> None:
        self.tab_compare.grid_columnconfigure(0, weight=1)
        self.tab_compare.grid_rowconfigure(1, weight=1)

        control_frame = customtkinter.CTkFrame(self.tab_compare)
        control_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        control_frame.grid_columnconfigure(1, weight=1)
        control_frame.grid_columnconfigure(3, weight=1)

        lbl1 = customtkinter.CTkLabel(control_frame, text="Target 1:")
        lbl1.grid(row=0, column=0, padx=5, pady=10)

        self.target1_entry = customtkinter.CTkEntry(control_frame, placeholder_text="user or owner/repo")
        self.target1_entry.grid(row=0, column=1, padx=5, pady=10, sticky="ew")

        lbl2 = customtkinter.CTkLabel(control_frame, text="Target 2:")
        lbl2.grid(row=0, column=2, padx=5, pady=10)

        self.target2_entry = customtkinter.CTkEntry(control_frame, placeholder_text="user or owner/repo")
        self.target2_entry.grid(row=0, column=3, padx=5, pady=10, sticky="ew")

        self.compare_type_var = customtkinter.StringVar(value="auto")
        mode_seg = customtkinter.CTkSegmentedButton(
            control_frame,
            values=["auto", "repo", "user"],
            variable=self.compare_type_var,
        )
        mode_seg.grid(row=0, column=4, padx=10, pady=10)

        self.compare_btn = customtkinter.CTkButton(control_frame, text="Compare", command=self._on_compare)
        self.compare_btn.grid(row=0, column=5, padx=10, pady=10)

        self.compare_status_label = customtkinter.CTkLabel(control_frame, text="")
        self.compare_status_label.grid(row=1, column=0, columnspan=6, padx=10, pady=(0, 5))

        self.compare_content_frame = customtkinter.CTkScrollableFrame(self.tab_compare)
        self.compare_content_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        self.compare_content_frame.grid_columnconfigure(0, weight=1)

    def _build_settings_tab(self) -> None:
        self.tab_settings.grid_columnconfigure(0, weight=1)

        rate_card = customtkinter.CTkFrame(self.tab_settings)
        rate_card.grid(row=0, column=0, padx=20, pady=15, sticky="ew")
        rate_card.grid_columnconfigure(1, weight=1)

        card_title = customtkinter.CTkLabel(
            rate_card,
            text="GitHub API Rate Limit Status",
            font=customtkinter.CTkFont(size=16, weight="bold"),
        )
        card_title.grid(row=0, column=0, columnspan=2, padx=15, pady=10, sticky="w")

        self.rate_limit_label = customtkinter.CTkLabel(rate_card, text="Limit: Loading...", font=customtkinter.CTkFont(size=14))
        self.rate_limit_label.grid(row=1, column=0, padx=15, pady=5, sticky="w")

        self.rate_progress = customtkinter.CTkProgressBar(rate_card)
        self.rate_progress.grid(row=2, column=0, columnspan=2, padx=15, pady=10, sticky="ew")
        self.rate_progress.set(0.0)

        refresh_btn = customtkinter.CTkButton(rate_card, text="Refresh Quota", command=self._refresh_rate_limit_async)
        refresh_btn.grid(row=3, column=0, padx=15, pady=10, sticky="w")

        auth_card = customtkinter.CTkFrame(self.tab_settings)
        auth_card.grid(row=1, column=0, padx=20, pady=15, sticky="ew")
        auth_card.grid_columnconfigure(1, weight=1)

        auth_title = customtkinter.CTkLabel(
            auth_card,
            text="Authentication & Personal Access Token",
            font=customtkinter.CTkFont(size=16, weight="bold"),
        )
        auth_title.grid(row=0, column=0, columnspan=2, padx=15, pady=10, sticky="w")

        token_desc = customtkinter.CTkLabel(
            auth_card,
            text="Supplying a token increases your rate limit from 60 to 5,000 requests per hour.",
            text_color="gray",
        )
        token_desc.grid(row=1, column=0, columnspan=2, padx=15, pady=(0, 10), sticky="w")

        lbl_token = customtkinter.CTkLabel(auth_card, text="Token:")
        lbl_token.grid(row=2, column=0, padx=15, pady=10, sticky="w")

        self.token_entry = customtkinter.CTkEntry(auth_card, placeholder_text="ghp_xxxxxxxxxxxx", show="*")
        self.token_entry.grid(row=2, column=1, padx=15, pady=10, sticky="ew")
        current_token = self.client.token or ""
        if current_token:
            self.token_entry.insert(0, current_token)

        save_token_btn = customtkinter.CTkButton(auth_card, text="Apply Token", command=self._on_apply_token)
        save_token_btn.grid(row=3, column=0, padx=15, pady=10, sticky="w")

        cache_card = customtkinter.CTkFrame(self.tab_settings)
        cache_card.grid(row=2, column=0, padx=20, pady=15, sticky="ew")
        cache_card.grid_columnconfigure(1, weight=1)

        cache_title = customtkinter.CTkLabel(
            cache_card,
            text="Local Response Cache",
            font=customtkinter.CTkFont(size=16, weight="bold"),
        )
        cache_title.grid(row=0, column=0, columnspan=2, padx=15, pady=10, sticky="w")

        self.cache_status_label = customtkinter.CTkLabel(
            cache_card,
            text=f"Database: {self.cache.db_path}",
            text_color="gray",
        )
        self.cache_status_label.grid(row=1, column=0, columnspan=2, padx=15, pady=5, sticky="w")

        clear_cache_btn = customtkinter.CTkButton(
            cache_card,
            text="Clear Cache",
            fg_color="#A83232",
            hover_color="#852222",
            command=self._on_clear_cache,
        )
        clear_cache_btn.grid(row=2, column=0, padx=15, pady=10, sticky="w")

    def _on_apply_token(self) -> None:
        token = self.token_entry.get().strip()
        self.client = GitHubClient(token=token if token else None, cache=self.cache, use_cache=True)
        self._refresh_rate_limit_async()
        messagebox.showinfo("Token Applied", "GitHub token updated. Refreshing quota...")

    def _on_clear_cache(self) -> None:
        count = self.cache.clear()
        messagebox.showinfo("Cache Cleared", f"Cleared {count} cached responses.")

    def _refresh_rate_limit_async(self) -> None:
        def worker():
            try:
                status = self.client.get_rate_limit()
                self.after(0, lambda: self._update_rate_limit_ui(status))
            except Exception as exc:
                self.after(0, lambda: self.rate_limit_label.configure(text=f"Rate Limit error: {exc}"))

        threading.Thread(target=worker, daemon=True).start()

    def _update_rate_limit_ui(self, status: Any) -> None:
        used_pct = (status.used / status.limit) if status.limit > 0 else 0
        text = f"Remaining: {status.remaining:,} / {status.limit:,} requests (Used: {status.used:,}) | Resets: {status.reset_time.strftime('%H:%M:%S UTC')}"
        self.rate_limit_label.configure(text=text)
        self.rate_progress.set(min(max(used_pct, 0.0), 1.0))

    def _on_analyze_user(self) -> None:
        username = self.user_entry.get().strip()
        if not username:
            messagebox.showwarning("Input Required", "Please enter a GitHub username.")
            return

        include_forks = self.include_forks_var.get()
        self.user_btn.configure(state="disabled")
        self.user_status_label.configure(text=f"Analyzing @{username}...", text_color="cyan")
        self.user_export_btn.configure(state="disabled")

        for widget in self.user_content_frame.winfo_children():
            widget.destroy()

        def worker():
            try:
                analysis = analyze_user(self.client, username, include_forks=include_forks)
                self.after(0, lambda: self._display_user_analysis(analysis))
            except ResourceNotFoundError:
                self.after(0, lambda: self._handle_user_error(f"User '{username}' not found."))
            except RateLimitExceededError as exc:
                self.after(0, lambda: self._handle_user_error(f"Rate limit exceeded: {exc}"))
            except Exception as exc:
                self.after(0, lambda: self._handle_user_error(str(exc)))

        threading.Thread(target=worker, daemon=True).start()

    def _handle_user_error(self, message: str) -> None:
        self.user_btn.configure(state="normal")
        self.user_status_label.configure(text=message, text_color="red")

    def _display_user_analysis(self, analysis: UserAnalysis) -> None:
        self.last_user_analysis = analysis
        self.user_btn.configure(state="normal")
        self.user_export_btn.configure(state="normal")
        self.user_status_label.configure(text=f"Analysis complete for @{analysis.user.login}", text_color="green")

        u = analysis.user

        header_card = customtkinter.CTkFrame(self.user_content_frame)
        header_card.grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        header_card.grid_columnconfigure(0, weight=1)

        name_text = f"{u.name or u.login} (@{u.login})"
        name_lbl = customtkinter.CTkLabel(header_card, text=name_text, font=customtkinter.CTkFont(size=18, weight="bold"))
        name_lbl.grid(row=0, column=0, padx=15, pady=(10, 2), sticky="w")

        bio_text = u.bio or "No bio provided."
        bio_lbl = customtkinter.CTkLabel(header_card, text=bio_text, text_color="gray")
        bio_lbl.grid(row=1, column=0, padx=15, pady=2, sticky="w")

        meta = []
        if u.company:
            meta.append(f"Company: {u.company}")
        if u.location:
            meta.append(f"Location: {u.location}")
        meta.append(f"Joined: {u.created_at.strftime('%Y-%m-%d')}")
        meta_lbl = customtkinter.CTkLabel(header_card, text="  |  ".join(meta), text_color="#64B5F6")
        meta_lbl.grid(row=2, column=0, padx=15, pady=(2, 10), sticky="w")

        stats_frame = customtkinter.CTkFrame(self.user_content_frame)
        stats_frame.grid(row=1, column=0, padx=5, pady=5, sticky="ew")
        for i in range(6):
            stats_frame.grid_columnconfigure(i, weight=1)

        metrics = [
            ("Public Repos", str(u.public_repos)),
            ("Source Repos", str(analysis.source_repositories_count)),
            ("Forked Repos", str(analysis.forked_repositories_count)),
            ("Followers", f"{u.followers:,}"),
            ("Total Stars", f"{analysis.total_stars:,}"),
            ("Total Forks", f"{analysis.total_forks:,}"),
        ]

        for col, (title, val) in enumerate(metrics):
            box = customtkinter.CTkFrame(stats_frame, fg_color="#2B2B2B")
            box.grid(row=0, column=col, padx=5, pady=5, sticky="ew")
            box_title = customtkinter.CTkLabel(box, text=title, font=customtkinter.CTkFont(size=11), text_color="gray")
            box_title.pack(pady=(5, 0))
            box_val = customtkinter.CTkLabel(box, text=val, font=customtkinter.CTkFont(size=14, weight="bold"))
            box_val.pack(pady=(0, 5))

        if analysis.languages.languages:
            langs_card = customtkinter.CTkFrame(self.user_content_frame)
            langs_card.grid(row=2, column=0, padx=5, pady=5, sticky="ew")
            langs_card.grid_columnconfigure(1, weight=1)

            card_lbl = customtkinter.CTkLabel(
                langs_card,
                text="Top Languages Across Repositories",
                font=customtkinter.CTkFont(size=14, weight="bold"),
            )
            card_lbl.grid(row=0, column=0, columnspan=3, padx=10, pady=5, sticky="w")

            for row_idx, lang in enumerate(analysis.languages.languages[:6], start=1):
                name_lbl = customtkinter.CTkLabel(langs_card, text=lang.name, width=120, anchor="w")
                name_lbl.grid(row=row_idx, column=0, padx=10, pady=3, sticky="w")

                bar = customtkinter.CTkProgressBar(langs_card)
                bar.grid(row=row_idx, column=1, padx=10, pady=3, sticky="ew")
                bar.set(lang.percentage / 100.0)

                pct_lbl = customtkinter.CTkLabel(langs_card, text=f"{lang.percentage:.1f}%", width=60, anchor="e")
                pct_lbl.grid(row=row_idx, column=2, padx=10, pady=3, sticky="e")

        if analysis.top_starred_repos:
            repos_card = customtkinter.CTkFrame(self.user_content_frame)
            repos_card.grid(row=3, column=0, padx=5, pady=5, sticky="ew")
            repos_card.grid_columnconfigure(0, weight=1)

            card_lbl = customtkinter.CTkLabel(
                repos_card,
                text="Top Starred Repositories",
                font=customtkinter.CTkFont(size=14, weight="bold"),
            )
            card_lbl.grid(row=0, column=0, columnspan=2, padx=10, pady=5, sticky="w")

            for idx, r in enumerate(analysis.top_starred_repos, start=1):
                r_box = customtkinter.CTkFrame(repos_card, fg_color="#242424")
                r_box.grid(row=idx, column=0, padx=10, pady=4, sticky="ew")
                r_box.grid_columnconfigure(0, weight=1)

                r_title = customtkinter.CTkLabel(
                    r_box,
                    text=f"{r.name}  —  {r.language or 'No Language'}",
                    font=customtkinter.CTkFont(weight="bold"),
                    text_color="#81D4FA",
                )
                r_title.grid(row=0, column=0, padx=10, pady=(4, 0), sticky="w")

                r_desc_text = r.description or "No description provided."
                r_desc = customtkinter.CTkLabel(r_box, text=r_desc_text, text_color="gray", anchor="w")
                r_desc.grid(row=1, column=0, padx=10, pady=(0, 4), sticky="w")

                r_stats = customtkinter.CTkLabel(r_box, text=f"Stars: {r.stars:,}  |  Forks: {r.forks:,}", text_color="yellow")
                r_stats.grid(row=0, column=1, rowspan=2, padx=15, pady=4, sticky="e")

    def _on_export_user(self) -> None:
        if not self.last_user_analysis:
            return
        target_path = filedialog.asksaveasfilename(
            defaultextension=".md",
            filetypes=[("Markdown Files", "*.md"), ("JSON Files", "*.json")],
            initialfile=f"{self.last_user_analysis.user.login}_analysis.md",
        )
        if not target_path:
            return

        path = Path(target_path)
        content = (
            export_user_to_json(self.last_user_analysis)
            if path.suffix.lower() == ".json"
            else export_user_to_markdown(self.last_user_analysis)
        )
        save_export_file(content, path)
        messagebox.showinfo("Export Successful", f"Saved analysis to:\n{path}")

    def _on_analyze_repo(self) -> None:
        target = self.repo_entry.get().strip()
        if not target or "/" not in target:
            messagebox.showwarning("Input Required", "Please enter a repository in 'owner/repo' format.")
            return

        owner, repo_name = target.split("/", 1)
        self.repo_btn.configure(state="disabled")
        self.repo_status_label.configure(text=f"Analyzing repository {target}...", text_color="cyan")
        self.repo_export_btn.configure(state="disabled")

        for widget in self.repo_content_frame.winfo_children():
            widget.destroy()

        def worker():
            try:
                analysis = analyze_repo(self.client, owner, repo_name)
                self.after(0, lambda: self._display_repo_analysis(analysis))
            except ResourceNotFoundError:
                self.after(0, lambda: self._handle_repo_error(f"Repository '{target}' not found."))
            except RateLimitExceededError as exc:
                self.after(0, lambda: self._handle_repo_error(f"Rate limit exceeded: {exc}"))
            except Exception as exc:
                self.after(0, lambda: self._handle_repo_error(str(exc)))

        threading.Thread(target=worker, daemon=True).start()

    def _handle_repo_error(self, message: str) -> None:
        self.repo_btn.configure(state="normal")
        self.repo_status_label.configure(text=message, text_color="red")

    def _display_repo_analysis(self, analysis: RepoAnalysis) -> None:
        self.last_repo_analysis = analysis
        self.repo_btn.configure(state="normal")
        self.repo_export_btn.configure(state="normal")
        self.repo_status_label.configure(text=f"Analysis complete for {analysis.repository.full_name}", text_color="green")

        r = analysis.repository

        header_card = customtkinter.CTkFrame(self.repo_content_frame)
        header_card.grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        header_card.grid_columnconfigure(0, weight=1)

        name_lbl = customtkinter.CTkLabel(
            header_card,
            text=r.full_name,
            font=customtkinter.CTkFont(size=18, weight="bold"),
            text_color="#81C784",
        )
        name_lbl.grid(row=0, column=0, padx=15, pady=(10, 2), sticky="w")

        desc_lbl = customtkinter.CTkLabel(header_card, text=r.description or "No description provided.", text_color="gray")
        desc_lbl.grid(row=1, column=0, padx=15, pady=2, sticky="w")

        meta = [
            f"Branch: {r.default_branch}",
            f"License: {r.license_name or 'None'}",
            f"Size: {r.size_kb:,} KB",
            f"Created: {r.created_at.strftime('%Y-%m-%d')}",
        ]
        meta_lbl = customtkinter.CTkLabel(header_card, text="  |  ".join(meta), text_color="#90CAF9")
        meta_lbl.grid(row=2, column=0, padx=15, pady=(2, 10), sticky="w")

        stats_frame = customtkinter.CTkFrame(self.repo_content_frame)
        stats_frame.grid(row=1, column=0, padx=5, pady=5, sticky="ew")
        for i in range(5):
            stats_frame.grid_columnconfigure(i, weight=1)

        metrics = [
            ("Stars", f"{r.stars:,}"),
            ("Forks", f"{r.forks:,}"),
            ("Watchers", f"{r.watchers:,}"),
            ("Open Issues", f"{r.open_issues:,}"),
            ("Health Score", f"{analysis.health.health_score}/100"),
        ]

        for col, (title, val) in enumerate(metrics):
            box = customtkinter.CTkFrame(stats_frame, fg_color="#2B2B2B")
            box.grid(row=0, column=col, padx=5, pady=5, sticky="ew")
            box_title = customtkinter.CTkLabel(box, text=title, font=customtkinter.CTkFont(size=11), text_color="gray")
            box_title.pack(pady=(5, 0))
            box_val = customtkinter.CTkLabel(box, text=val, font=customtkinter.CTkFont(size=14, weight="bold"))
            box_val.pack(pady=(0, 5))

        if analysis.languages.languages:
            langs_card = customtkinter.CTkFrame(self.repo_content_frame)
            langs_card.grid(row=2, column=0, padx=5, pady=5, sticky="ew")
            langs_card.grid_columnconfigure(1, weight=1)

            card_lbl = customtkinter.CTkLabel(
                langs_card,
                text="Language Composition",
                font=customtkinter.CTkFont(size=14, weight="bold"),
            )
            card_lbl.grid(row=0, column=0, columnspan=3, padx=10, pady=5, sticky="w")

            for row_idx, lang in enumerate(analysis.languages.languages, start=1):
                name_lbl = customtkinter.CTkLabel(langs_card, text=lang.name, width=120, anchor="w")
                name_lbl.grid(row=row_idx, column=0, padx=10, pady=3, sticky="w")

                bar = customtkinter.CTkProgressBar(langs_card)
                bar.grid(row=row_idx, column=1, padx=10, pady=3, sticky="ew")
                bar.set(lang.percentage / 100.0)

                pct_lbl = customtkinter.CTkLabel(
                    langs_card,
                    text=f"{lang.percentage:.1f}% ({lang.bytes_count:,} bytes)",
                    anchor="e",
                )
                pct_lbl.grid(row=row_idx, column=2, padx=10, pady=3, sticky="e")

        if analysis.contributors:
            contrib_card = customtkinter.CTkFrame(self.repo_content_frame)
            contrib_card.grid(row=3, column=0, padx=5, pady=5, sticky="ew")
            contrib_card.grid_columnconfigure(0, weight=1)

            card_lbl = customtkinter.CTkLabel(
                contrib_card,
                text="Top Contributors",
                font=customtkinter.CTkFont(size=14, weight="bold"),
            )
            card_lbl.grid(row=0, column=0, columnspan=2, padx=10, pady=5, sticky="w")

            for idx, c in enumerate(analysis.contributors[:8], start=1):
                c_lbl = customtkinter.CTkLabel(contrib_card, text=f"• {c.login}", anchor="w")
                c_lbl.grid(row=idx, column=0, padx=15, pady=2, sticky="w")

                count_lbl = customtkinter.CTkLabel(contrib_card, text=f"{c.contributions:,} commits", text_color="#81C784")
                count_lbl.grid(row=idx, column=1, padx=15, pady=2, sticky="e")

    def _on_export_repo(self) -> None:
        if not self.last_repo_analysis:
            return
        safe_name = self.last_repo_analysis.repository.full_name.replace("/", "_")
        target_path = filedialog.asksaveasfilename(
            defaultextension=".md",
            filetypes=[("Markdown Files", "*.md"), ("JSON Files", "*.json")],
            initialfile=f"{safe_name}_audit.md",
        )
        if not target_path:
            return

        path = Path(target_path)
        content = (
            export_repo_to_json(self.last_repo_analysis)
            if path.suffix.lower() == ".json"
            else export_repo_to_markdown(self.last_repo_analysis)
        )
        save_export_file(content, path)
        messagebox.showinfo("Export Successful", f"Saved repository analysis to:\n{path}")

    def _on_compare(self) -> None:
        t1 = self.target1_entry.get().strip()
        t2 = self.target2_entry.get().strip()
        if not t1 or not t2:
            messagebox.showwarning("Input Required", "Please enter two targets to compare.")
            return

        mode = self.compare_type_var.get()
        is_repo = mode == "repo" or (mode == "auto" and ("/" in t1 or "/" in t2))

        self.compare_btn.configure(state="disabled")
        self.compare_status_label.configure(text="Comparing targets...", text_color="cyan")

        for widget in self.compare_content_frame.winfo_children():
            widget.destroy()

        def worker():
            try:
                if is_repo:
                    if "/" not in t1 or "/" not in t2:
                        raise ValueError("Repository comparison requires 'owner/repo' format for both targets.")
                    o1, r1 = t1.split("/", 1)
                    o2, r2 = t2.split("/", 1)
                    a1 = analyze_repo(self.client, o1, r1)
                    a2 = analyze_repo(self.client, o2, r2)
                    comp = compare_repositories(a1, a2)
                else:
                    a1 = analyze_user(self.client, t1)
                    a2 = analyze_user(self.client, t2)
                    comp = compare_users(a1, a2)
                self.after(0, lambda: self._display_comparison(comp))
            except Exception as exc:
                self.after(0, lambda: self._handle_compare_error(str(exc)))

        threading.Thread(target=worker, daemon=True).start()

    def _handle_compare_error(self, message: str) -> None:
        self.compare_btn.configure(state="normal")
        self.compare_status_label.configure(text=message, text_color="red")

    def _display_comparison(self, comparison: ComparisonResult) -> None:
        self.compare_btn.configure(state="normal")
        self.compare_status_label.configure(text=f"Comparison: {comparison.item1_name} vs {comparison.item2_name}", text_color="green")

        card = customtkinter.CTkFrame(self.compare_content_frame)
        card.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        card.grid_columnconfigure(0, weight=2)
        card.grid_columnconfigure(1, weight=3)
        card.grid_columnconfigure(2, weight=3)

        title_lbl = customtkinter.CTkLabel(
            card,
            text=comparison.title,
            font=customtkinter.CTkFont(size=16, weight="bold"),
        )
        title_lbl.grid(row=0, column=0, columnspan=3, padx=15, pady=10, sticky="w")

        h_metric = customtkinter.CTkLabel(card, text="Metric", font=customtkinter.CTkFont(weight="bold"), text_color="gray")
        h_metric.grid(row=1, column=0, padx=10, pady=5, sticky="w")

        h_item1 = customtkinter.CTkLabel(
            card,
            text=comparison.item1_name,
            font=customtkinter.CTkFont(weight="bold"),
            text_color="#81D4FA",
        )
        h_item1.grid(row=1, column=1, padx=10, pady=5)

        h_item2 = customtkinter.CTkLabel(
            card,
            text=comparison.item2_name,
            font=customtkinter.CTkFont(weight="bold"),
            text_color="#CE93D8",
        )
        h_item2.grid(row=1, column=2, padx=10, pady=5)

        for row_idx, m in enumerate(comparison.metrics, start=2):
            bg_color = "#242424" if row_idx % 2 == 0 else "#2A2A2A"
            row_frame = customtkinter.CTkFrame(card, fg_color=bg_color)
            row_frame.grid(row=row_idx, column=0, columnspan=3, padx=5, pady=2, sticky="ew")
            row_frame.grid_columnconfigure(0, weight=2)
            row_frame.grid_columnconfigure(1, weight=3)
            row_frame.grid_columnconfigure(2, weight=3)

            m_lbl = customtkinter.CTkLabel(row_frame, text=m.name, anchor="w")
            m_lbl.grid(row=0, column=0, padx=10, pady=6, sticky="w")

            t1_color = "#81C784" if m.winner == 1 else "white"
            t1_text = f"{m.value1}  [WINNER]" if m.winner == 1 else m.value1
            val1_lbl = customtkinter.CTkLabel(row_frame, text=t1_text, text_color=t1_color)
            val1_lbl.grid(row=0, column=1, padx=10, pady=6)

            t2_color = "#81C784" if m.winner == 2 else "white"
            t2_text = f"{m.value2}  [WINNER]" if m.winner == 2 else m.value2
            val2_lbl = customtkinter.CTkLabel(row_frame, text=t2_text, text_color=t2_color)
            val2_lbl.grid(row=0, column=2, padx=10, pady=6)


def run_gui() -> None:
    app = GitHubAnalyzerApp()
    app.mainloop()


if __name__ == "__main__":
    run_gui()
