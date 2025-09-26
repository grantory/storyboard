from __future__ import annotations

import os
import threading
import queue

import customtkinter as ctk

from src.config import load_config
from src.gui.pipeline import Pipeline
from src.gui.state import AppState
from src.gui.utils_images import data_url_to_ctkimage
from src.services.video import sample_middle_frame_as_data_url
from src.services import connectivity_probe, openrouter_models_probe, openrouter_chat_probe


class MaestroApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Project Maestro v2 - AI Storyboard Generator")
        self.geometry("1400x900")
        self.minsize(1000, 700)

        self.app_state = AppState(cfg=load_config())
        self.pipeline = Pipeline(self.app_state.cfg, on_log=self._on_log)
        self.events: "queue.Queue[tuple]" = queue.Queue()

        self._build_ui()
        self._setup_keyboard_shortcuts()
        self.after(50, self._drain_events)
        self.after(150, self._post_init_checks)
        # Ensure action buttons reflect prerequisites at startup
        try:
            self._refresh_action_buttons_state()
        except Exception:
            pass

    # ---------- UI ----------
    def _build_ui(self) -> None:
        """Build the main UI layout."""
        self._setup_grid_layout()
        self._build_sidebar()
        self._build_main_content()
        self._build_right_sidebar()
        self._build_status_bar()

    def _setup_grid_layout(self) -> None:
        """Set up the main grid layout."""
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=0)
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(2, weight=0)

    def _build_sidebar(self) -> None:
        """Build the left sidebar with controls."""
        self.sidebar = ctk.CTkScrollableFrame(self, width=280, fg_color="transparent")
        self.sidebar.grid(row=0, column=0, sticky="nsw", padx=1, pady=1)

        self._build_sidebar_header()
        self._build_file_section()
        self._build_action_section()
        self._build_preview_section()

    def _build_sidebar_header(self) -> None:
        """Build the sidebar header."""
        sidebar_header = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        sidebar_header.pack(fill="x", padx=16, pady=(16, 8))

        sidebar_title = ctk.CTkLabel(
            sidebar_header,
            text="🎬 Project Maestro",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        sidebar_title.pack(anchor="w")

    def _build_file_section(self) -> None:
        """Build the file selection section."""
        file_section = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        file_section.pack(fill="x", padx=16, pady=(16, 8))

        file_label = ctk.CTkLabel(
            file_section,
            text="📁 Files",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=("gray60", "gray40")
        )
        file_label.pack(anchor="w", pady=(0, 8))

        self.btn_open_video = ctk.CTkButton(
            file_section,
            text="📹 Open Video",
            command=self._open_video,
            height=36,
            font=ctk.CTkFont(size=13)
        )
        # tooltips disabled

        self.btn_open_style = ctk.CTkButton(
            file_section,
            text="🎨 Open Style Image",
            command=self._open_style,
            height=36,
            font=ctk.CTkFont(size=13)
        )
        # tooltips disabled
        self.btn_open_video.pack(pady=(0, 4), fill="x")
        self.btn_open_style.pack(pady=(0, 8), fill="x")

    def _build_action_section(self) -> None:
        """Build the action buttons section."""
        action_section = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        action_section.pack(fill="x", padx=16, pady=(0, 8))

        action_label = ctk.CTkLabel(
            action_section,
            text="⚡ Actions",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=("gray60", "gray40")
        )
        action_label.pack(anchor="w", pady=(0, 8))

        self.btn_analyze = ctk.CTkButton(
            action_section,
            text="🔍 Analyze Video (Context)",
            command=self._analyze,
            height=36,
            font=ctk.CTkFont(size=13),
            fg_color="#166534",
            hover_color="#14532d"
        )
        # tooltips disabled
        # Start disabled until prerequisites are satisfied
        try:
            self.btn_analyze.configure(state="disabled")
        except Exception:
            pass

        self.btn_gen_all = ctk.CTkButton(
            action_section,
            text="🎭 Generate Shots",
            command=self._generate_shots_from_context,
            height=36,
            font=ctk.CTkFont(size=13),
            fg_color="#1d4ed8",
            hover_color="#1e40af"
        )
        # tooltips disabled
        # Start disabled until analysis finishes
        try:
            self.btn_gen_all.configure(state="disabled")
        except Exception:
            pass
        # Shot count selector (3-10)
        shot_row = ctk.CTkFrame(action_section, fg_color="transparent")
        shot_row.pack(fill="x", pady=(8, 4))

        lbl_shots = ctk.CTkLabel(
            shot_row,
            text="Shots:",
            font=ctk.CTkFont(size=12),
            text_color=("gray60", "gray40")
        )
        lbl_shots.pack(side="left")

        # Keep an internal variable for the dropdown
        self.var_shot_count = ctk.StringVar(value=str(self.app_state.shot_count))
        def _on_shot_count_change(choice: str) -> None:
            try:
                self.app_state.shot_count = max(3, min(10, int(choice)))
                self._on_log(f"🎯 Shot count set to {self.app_state.shot_count}")
            except Exception:
                pass

        self.dd_shot_count = ctk.CTkOptionMenu(
            shot_row,
            values=[str(n) for n in range(3, 11)],
            variable=self.var_shot_count,
            command=_on_shot_count_change,
            width=80,
        )
        self.dd_shot_count.pack(side="right")

        self.btn_analyze.pack(pady=(0, 4), fill="x")
        self.btn_gen_all.pack(pady=(0, 8), fill="x")

        # Accessibility: Text size scaling
        size_row = ctk.CTkFrame(action_section, fg_color="transparent")
        size_row.pack(fill="x", pady=(0, 6))

        lbl_text = ctk.CTkLabel(
            size_row,
            text="Text Size:",
            font=ctk.CTkFont(size=12),
            text_color=("gray60", "gray40"),
        )
        lbl_text.pack(side="left")

        self.var_text_scale = ctk.StringVar(value="100%")
        def _on_text_scale_change(choice: str) -> None:
            try:
                pct = int(choice.strip("%"))
                pct = max(75, min(175, pct))
                ctk.set_widget_scaling(pct / 100.0)
                self._on_log(f"🔤 UI scale set to {pct}%")
            except Exception:
                pass

        self.dd_text_scale = ctk.CTkOptionMenu(
            size_row,
            values=["90%", "100%", "110%", "125%", "150%"],
            variable=self.var_text_scale,
            command=_on_text_scale_change,
            width=100,
        )
        self.dd_text_scale.pack(side="right")

        # Theme toggle (Light/Dark)
        theme_row = ctk.CTkFrame(action_section, fg_color="transparent")
        theme_row.pack(fill="x", pady=(0, 8))

        lbl_theme = ctk.CTkLabel(
            theme_row,
            text="Theme:",
            font=ctk.CTkFont(size=12),
            text_color=("gray60", "gray40"),
        )
        lbl_theme.pack(side="left")

        self._theme_mode = "dark"
        self.btn_theme_toggle = ctk.CTkButton(
            theme_row,
            text="Switch to Light",
            command=self._toggle_theme,
            height=28,
            font=ctk.CTkFont(size=11),
        )
        self.btn_theme_toggle.pack(side="right")

    def _build_preview_section(self) -> None:
        """Build the preview section in the sidebar."""
        preview_section = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        preview_section.pack(fill="x", padx=16, pady=(0, 16))

        preview_label = ctk.CTkLabel(
            preview_section,
            text="📋 Previews",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=("gray60", "gray40")
        )
        preview_label.pack(anchor="w", pady=(0, 12))

        # Video preview with improved styling
        video_preview_frame = ctk.CTkFrame(preview_section, fg_color=("gray85", "gray25"))
        video_preview_frame.pack(fill="x", pady=(0, 8))

        self.lbl_video_preview = ctk.CTkLabel(
            video_preview_frame,
            text="📹 Video Preview",
            font=ctk.CTkFont(size=11),
            text_color=("gray50", "gray60"),
            height=80
        )
        self.lbl_video_preview._image_ref = None  # type: ignore[attr-defined]
        self.lbl_video_preview.pack(padx=8, pady=8, fill="both", expand=True)

        # Style preview with improved styling
        style_preview_frame = ctk.CTkFrame(preview_section, fg_color=("gray85", "gray25"))
        style_preview_frame.pack(fill="x")

        self.lbl_style_preview = ctk.CTkLabel(
            style_preview_frame,
            text="🎨 Style Preview",
            font=ctk.CTkFont(size=11),
            text_color=("gray50", "gray60"),
            height=80
        )
        self.lbl_style_preview._image_ref = None  # type: ignore[attr-defined]
        self.lbl_style_preview.pack(padx=8, pady=8, fill="both", expand=True)

    def _build_main_content(self) -> None:
        """Build the main content area."""
        self.main = ctk.CTkFrame(self, fg_color=("gray95", "gray10"))
        self.main.grid(row=0, column=1, sticky="nsew", padx=1, pady=1)
        self.main.grid_rowconfigure(1, weight=1)
        self.main.grid_columnconfigure(0, weight=1)

        self._build_context_section()
        self._build_shots_section()

    def _build_context_section(self) -> None:
        """Build the context input section."""
        context_section = ctk.CTkFrame(self.main, fg_color="transparent")
        context_section.pack(fill="x", padx=20, pady=(20, 0))

        context_header = ctk.CTkFrame(context_section, fg_color="transparent")
        context_header.pack(fill="x")

        self.lbl_context = ctk.CTkLabel(
            context_header,
            text="📝 Context & Analysis",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        self.lbl_context.pack(anchor="w", side="left")

        self.lbl_wc = ctk.CTkLabel(
            context_header,
            text="0 words",
            font=ctk.CTkFont(size=12),
            text_color=("gray60", "gray40")
        )
        self.lbl_wc.pack(anchor="e", side="right")

        # Context text area with improved styling
        self.txt_context = ctk.CTkTextbox(
            context_section,
            height=120,
            font=ctk.CTkFont(size=12),
            fg_color=("gray90", "gray20")
        )
        self.txt_context.pack(padx=0, pady=(12, 0), fill="x")
        self.txt_context.bind("<KeyRelease>", lambda _e: self._update_word_count())

    def _build_shots_section(self) -> None:
        """Build the shots display section."""
        shots_section = ctk.CTkFrame(self.main, fg_color="transparent")
        shots_section.pack(fill="both", expand=True, padx=20, pady=20)

        self.shots_frame = ctk.CTkScrollableFrame(
            shots_section,
            label_text="🎬 Generated Shots",
            label_font=ctk.CTkFont(size=14, weight="bold"),
            label_fg_color="transparent"
        )
        self.shots_frame.pack(fill="both", expand=True)

    def _build_right_sidebar(self) -> None:
        """Build the right sidebar with logs."""
        self.right = ctk.CTkFrame(self, width=340, fg_color=("gray95", "gray10"))
        self.right.grid(row=0, column=2, sticky="nse", padx=1, pady=1)
        self.right.grid_propagate(False)

        self._build_progress_section()
        self._build_logs_section()

    def _build_progress_section(self) -> None:
        """Build the progress indicator section."""
        progress_section = ctk.CTkFrame(self.right, fg_color="transparent")
        progress_section.pack(fill="x", padx=20, pady=(20, 0))

        self.progress = ctk.CTkProgressBar(
            progress_section,
            mode="indeterminate",
            height=6,
            progress_color="#4CAF50"
        )
        self.progress.pack(fill="x")

    def _build_logs_section(self) -> None:
        """Build the logs display section."""
        logs_section = ctk.CTkFrame(self.right, fg_color="transparent")
        logs_section.pack(fill="both", expand=True, padx=20, pady=20)

        logs_header = ctk.CTkFrame(logs_section, fg_color="transparent")
        logs_header.pack(fill="x")

        logs_label = ctk.CTkLabel(
            logs_header,
            text="📊 Activity Log",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        logs_label.pack(anchor="w", side="left")

        clear_logs_btn = ctk.CTkButton(
            logs_header,
            text="🗑️ Clear",
            command=self._clear_logs,
            width=60,
            height=28,
            font=ctk.CTkFont(size=10),
            fg_color="transparent",
            text_color=("gray60", "gray40")
        )
        # tooltips disabled
        clear_logs_btn.pack(anchor="e", side="right")

        # Logs text area with improved styling
        self.txt_logs = ctk.CTkTextbox(
            logs_section,
            activate_scrollbars=True,
            font=ctk.CTkFont(size=11),
            fg_color=("gray90", "gray20")
        )
        self.txt_logs.pack(fill="both", expand=True, pady=(12, 0))

    def _build_status_bar(self) -> None:
        """Build the status bar."""
        self.status_bar = ctk.CTkFrame(self, height=32, fg_color=("gray90", "gray15"))
        self.status_bar.grid(row=1, column=0, columnspan=3, sticky="we")
        self.status_bar.grid_propagate(False)

        status_content = ctk.CTkFrame(self.status_bar, fg_color="transparent")
        status_content.pack(fill="both", expand=True, padx=16, pady=4)

        self.lbl_status = ctk.CTkLabel(
            status_content,
            text="✨ Ready to create storyboards (Press F1 for help)",
            anchor="w",
            font=ctk.CTkFont(size=12),
            text_color=("gray50", "gray70")
        )
        self.lbl_status.pack(side="left")
        # tooltips disabled

        # Add connection status indicator
        self.lbl_connection_status = ctk.CTkLabel(
            status_content,
            text="🔌 Checking connection...",
            anchor="e",
            font=ctk.CTkFont(size=11),
            text_color=("gray60", "gray50")
        )
        self.lbl_connection_status.pack(side="right")

    # ---------- Events ----------
    def _on_log(self, msg: str) -> None:
        self.app_state.logs.append(msg)
        try:
            self.txt_logs.insert("end", msg + os.linesep)
            self.txt_logs.see("end")
        except Exception:
            pass
        self._set_status(msg)

    def _set_status(self, text: str) -> None:
        try:
            self.lbl_status.configure(text=text)
        except Exception:
            pass

    def _update_word_count(self) -> None:
        try:
            txt = self.txt_context.get("1.0", "end").strip()
            words = len([w for w in txt.split() if w])
            self.lbl_wc.configure(text=f"{words} words")
        except Exception:
            pass

    def _clear_logs(self) -> None:
        """Clear the activity log."""
        try:
            log_count = len(self.app_state.logs)
            self._on_log(f"🗑️ Clearing activity log ({log_count} entries)...")
            self.txt_logs.delete("1.0", "end")
            self.app_state.logs.clear()
            self._on_log("✅ Activity log cleared successfully")
        except Exception:
            pass

    def show_tooltip(self, widget, text: str) -> None:
        return

    def hide_tooltip(self) -> None:
        """Hide the current tooltip."""
        if hasattr(self, '_current_tooltip') and self._current_tooltip:
            try:
                self._current_tooltip.destroy()
                self._current_tooltip = None
            except Exception:
                pass

    def _setup_keyboard_shortcuts(self) -> None:
        """Set up keyboard shortcuts for the application."""
        self.bind("<Control-o>", lambda e: self._open_video())
        self.bind("<Control-s>", lambda e: self._open_style())
        self.bind("<Control-a>", lambda e: self._analyze())
        self.bind("<Control-g>", lambda e: self._generate_shots_from_context())
        # Escape previously cancelled operations; no-op now
        self.bind("<Control-l>", lambda e: self._clear_logs())
        self.bind("<F1>", lambda e: self.show_toast("💡 Keyboard shortcuts:\nCtrl+O: Open Video\nCtrl+S: Open Style\nCtrl+A: Analyze\nCtrl+G: Generate All\nCtrl+L: Clear Log", duration_ms=5000))

    def _toggle_theme(self) -> None:
        try:
            self._theme_mode = "light" if self._theme_mode == "dark" else "dark"
            ctk.set_appearance_mode(self._theme_mode)
            btn_text = "Switch to Dark" if self._theme_mode == "light" else "Switch to Light"
            try:
                self.btn_theme_toggle.configure(text=btn_text)
            except Exception:
                pass
            self._on_log(f"🌓 Theme set to {self._theme_mode.title()}")
        except Exception:
            pass

    def _refresh_action_buttons_state(self) -> None:
        """Enable/disable Analyze and Generate based on prerequisites."""
        try:
            has_video = bool(self.app_state.video_bytes)
            has_style = bool(self.app_state.style_data_url)
            can_analyze = has_video and has_style
            self.btn_analyze.configure(state="normal" if can_analyze else "disabled")

            analyzed = bool(self.app_state.context_text and self.app_state.middle_frame_data_url)
            self.btn_gen_all.configure(state="normal" if analyzed else "disabled")
        except Exception:
            pass

    def _open_video(self) -> None:
        self._on_log("📹 Opening video file dialog...")
        from tkinter.filedialog import askopenfilename
        path = askopenfilename(filetypes=[("Video", "*.mp4")])
        if not path:
            self._on_log("❌ Video selection cancelled")
            return

        self._on_log(f"📁 Selected video file: {os.path.basename(path)}")
        self.app_state.video_path = path
        try:
            self._on_log("📖 Reading video file...")
            with open(path, "rb") as f:
                self.app_state.video_bytes = f.read()
            file_size = len(self.app_state.video_bytes)
            self._on_log(f"✅ Video loaded successfully: {os.path.basename(path)} ({file_size:,} bytes)")

            # Build and show middle-frame preview
            self._on_log("🖼️  Generating video preview...")
            try:
                data_url = sample_middle_frame_as_data_url(self.app_state.video_bytes)
                cimg = data_url_to_ctkimage(data_url, max_width=150)
                self.lbl_video_preview.configure(image=cimg, text="")
                self.lbl_video_preview._image_ref = cimg  # type: ignore[attr-defined]
                self._on_log("✅ Video preview generated successfully")
            except Exception as e:  # noqa: BLE001
                self._on_log(f"⚠️  Video preview failed: {e}")
        except Exception as e:
            self._on_log(f"❌ Failed to load video: {e}")
        # Update action buttons availability
        try:
            self._refresh_action_buttons_state()
        except Exception:
            pass

    def _open_style(self) -> None:
        self._on_log("🎨 Opening style image file dialog...")
        from tkinter.filedialog import askopenfilename
        path = askopenfilename(filetypes=[("Images", "*.png;*.jpg;*.jpeg")])
        if not path:
            self._on_log("❌ Style image selection cancelled")
            return

        self._on_log(f"📁 Selected style image: {os.path.basename(path)}")
        self.app_state.style_path = path
        try:
            self._on_log("📖 Reading style image file...")
            with open(path, "rb") as f:
                b = f.read()
            file_size = len(b)
            self._on_log(f"📊 Style image loaded: {file_size:,} bytes")

            self._on_log("🖼️  Building style preview...")
            self.app_state.style_data_url = self.pipeline.build_style_preview(b)

            self._on_log(f"✅ Style image processed successfully: {os.path.basename(path)}")

            # Show style preview
            self._on_log("🖼️  Generating style preview display...")
            try:
                cimg = data_url_to_ctkimage(self.app_state.style_data_url, max_width=150)
                self.lbl_style_preview.configure(image=cimg, text="")
                self.lbl_style_preview._image_ref = cimg  # type: ignore[attr-defined]
                self._on_log("✅ Style preview displayed successfully")
            except Exception as e:  # noqa: BLE001
                self._on_log(f"⚠️  Style preview display failed: {e}")
        except Exception as e:
            self._on_log(f"❌ Failed to load style image: {e}")
        # Update action buttons availability
        try:
            self._refresh_action_buttons_state()
        except Exception:
            pass

    def _analyze(self) -> None:
        self._on_log("🎬 Analyzing video for context...")
        if not self.app_state.video_bytes:
            self._on_log("❌ No video loaded - analysis cancelled")
            self.show_toast("📹 Please select a video first", duration_ms=3000)
            return

        self._on_log(f"📊 Video size: {len(self.app_state.video_bytes)} bytes")

        # Update UI state
        self.btn_analyze.configure(state="disabled", text="🔄 Analyzing...")
        self.btn_gen_all.configure(state="disabled")

        # Enhanced progress feedback
        try:
            self.progress.start()
            self.progress.configure(progress_color="#6366f1")
        except Exception:
            pass

        self.app_state.cancel_event.clear()
        self._set_status("🔍 Getting context from video...")
        self.show_toast("🧠 Analyzing context", duration_ms=2000)
        self._on_log("🔄 UI updated, starting analysis thread...")

        def worker() -> None:
            self._on_log("🧵 Context analysis worker started")
            try:
                ctx, middle = self.pipeline.analyze_context(self.app_state.video_bytes or b"", cancel=self.app_state.cancel_event)
                self._on_log("✅ Context analysis completed successfully")
                self.events.put(("context_done", ctx, middle))
            except Exception as e:  # noqa: BLE001
                self._on_log(f"❌ Context analysis failed with exception: {e}")
                self.events.put(("error", str(e)))

        threading.Thread(target=worker, daemon=True).start()

    # Cancel functionality removed

    def _drain_events(self) -> None:
        try:
            while True:
                evt = self.events.get_nowait()
                kind = evt[0]
                if kind == "context_done":
                    _k, ctx, middle = evt
                    self._on_log(f"📝 Context received: {len(ctx)} chars. Middle frame ready.")
                    self.app_state.context_text = ctx
                    self.app_state.middle_frame_data_url = middle
                    self.txt_context.delete("1.0", "end")
                    self.txt_context.insert("1.0", ctx)
                    self._update_word_count()

                    # Reset UI state; enable Generate Shots
                    self.btn_analyze.configure(state="normal", text="🔍 Analyze Video (Context)")
                    # Cancel button removed
                    self._refresh_action_buttons_state()

                    try:
                        self.progress.stop()
                        self.progress.configure(progress_color="#4CAF50")
                    except Exception:
                        pass

                    self._set_status("✅ Context ready. You can edit it, then Generate Shots.")
                    self.show_toast("🧠 Context ready. Edit if needed, then press Generate Shots.", duration_ms=3000)
                elif kind == "error":
                    _k, msg = evt
                    self._on_log(f"🚨 Critical error occurred: {msg}")
                    self._on_log("🔄 Resetting UI state after error...")

                    # Reset UI state
                    self.btn_analyze.configure(state="normal", text="🔍 Analyze Video")
                    # Cancel button removed
                    self._refresh_action_buttons_state()

                    try:
                        self.progress.stop()
                        self._on_log("✅ Progress indicator stopped")
                    except Exception as progress_error:  # noqa: BLE001
                        self._on_log(f"⚠️ Failed to stop progress indicator: {progress_error}")

                    self._on_log("✅ UI state reset complete after error")
                    try:
                        self.progress.configure(progress_color="#ef4444")
                    except Exception:
                        pass

                    self._set_status("❌ Analysis failed")
                    self.show_toast("Something went wrong. Check the log for details.", duration_ms=4000)
                elif kind == "conn_check":
                    _k, ok, msg = evt
                    status_icon = "✅" if ok else "❌"
                    status_color = ("green", "lightgreen") if ok else ("red", "darkred")
                    try:
                        self.lbl_connection_status.configure(
                            text=f"{status_icon} {msg}",
                            text_color=status_color
                        )
                    except Exception:
                        pass
                elif kind == "gen_done":
                    _k, shot_id, url = evt
                    # Persist result
                    self.app_state.results[shot_id] = url
                    # Update UI widgets for this shot
                    widgets = self.shot_widgets.get(shot_id)
                    if widgets:
                        prev = widgets.get("preview")
                        if prev is not None and hasattr(prev, "set_preview"):
                            try:
                                prev.set_preview(url)  # type: ignore[attr-defined]
                            except Exception:
                                pass
                        btn_save = widgets.get("btn_save")
                        status_indicator = widgets.get("status_indicator")
                        if btn_save:
                            btn_save.configure(state="disabled")
                        if status_indicator:
                            status_indicator.configure(text="⏳ Processing...", text_color="#f59e0b")
                    # Auto-upscale asynchronously
                    def _auto_upscale_worker(sid: int, data_url: str) -> None:
                        try:
                            from src.services.storage import data_url_to_bytes_and_mime, bytes_to_data_url, save_data_url_png_to_dir
                            from src.services.upscaler import get_upscaler
                            raw, _ = data_url_to_bytes_and_mime(data_url)
                            up_bytes = get_upscaler().upscale_from_bytes(raw, outscale=2.0, output_format="PNG")
                            up_url = bytes_to_data_url(up_bytes, mime="image/png")
                            # Autosave to output/
                            root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
                            out_dir = os.path.join(root_dir, "output")
                            saved_path = save_data_url_png_to_dir(up_url, out_dir, prefix=f"storyboard_shot_{sid:03d}")
                            self.events.put(("auto_upscaled", sid, up_url, up_bytes, saved_path))
                        except Exception as e:  # noqa: BLE001
                            self.events.put(("upscale_error", sid, str(e)))
                    threading.Thread(target=_auto_upscale_worker, args=(shot_id, url), daemon=True).start()
                    btn_gen = widgets.get("btn_gen")
                    if btn_gen:
                        btn_gen.configure(state="normal", text="🎨 Generate Image")
                    self._on_log(f"Shot {shot_id} generated")
                    self.show_toast(f"🎬 Shot {shot_id} complete!", duration_ms=2000)
                elif kind == "gen_error":
                    _k, shot_id, msg = evt
                    self._on_log(f"Shot {shot_id} failed: {msg}")
                    self.app_state.errors[shot_id] = msg
                    widgets = self.shot_widgets.get(shot_id)
                    if widgets:
                        status_indicator = widgets.get("status_indicator")
                        btn_gen = widgets.get("btn_gen")
                        if status_indicator:
                            status_indicator.configure(text="❌ Failed", text_color="#ef4444")
                        if btn_gen:
                            btn_gen.configure(state="normal", text="🔄 Retry")
                    self.show_toast(f"❌ Shot {shot_id} failed. Check log for details.", duration_ms=3000)
                elif kind == "shots_done":
                    _k, shots = evt
                    self.app_state.shots = shots
                    self._render_shots()
                    try:
                        self.progress.stop()
                        self.progress.configure(progress_color="#4CAF50")
                    except Exception:
                        pass
                    self.btn_gen_all.configure(state="normal", text="🎭 Generate Shots")
                    self.btn_analyze.configure(state="normal")
                    self._set_status("✅ Shots ready. Generate images per shot or all.")
                    self.show_toast(f"🎬 {len(shots)} shots generated.", duration_ms=3000)
                elif kind == "auto_upscaled":
                    _k, shot_id, up_url, up_bytes, saved_path = evt
                    self.app_state.upscaled[shot_id] = up_bytes
                    self.app_state.saved_paths[shot_id] = saved_path
                    widgets = self.shot_widgets.get(shot_id)
                    if widgets:
                        prev = widgets.get("preview")
                        status_indicator = widgets.get("status_indicator")
                        btn_save = widgets.get("btn_save")
                        if prev is not None and hasattr(prev, "set_preview"):
                            try:
                                prev.set_preview(up_url, indicator=status_indicator, on_click_path=saved_path)  # type: ignore[attr-defined]
                            except Exception:
                                pass
                        if btn_save:
                            btn_save.configure(state="normal")
                    self._on_log(f"💾 Autosaved upscaled shot {shot_id} → {os.path.basename(saved_path)}")
                    self.show_toast(f"💾 Saved shot {shot_id}")
        except queue.Empty:
            pass
        self.after(50, self._drain_events)

    # ---------- Rendering ----------
    def _render_shots(self) -> None:
        """Render all shots in the shots frame."""
        for child in self.shots_frame.winfo_children():
            child.destroy()
        self.shot_widgets: dict[int, dict[str, ctk.CTkBaseClass]] = {}

        for shot in self.app_state.shots:
            shot_widgets = self._create_shot_widget(shot)
            self.shot_widgets[shot.id] = shot_widgets

    def _create_shot_widget(self, shot) -> dict[str, ctk.CTkBaseClass]:
        """Create a single shot widget and return its components."""
        # Create shot container with improved styling
        shot_container = ctk.CTkFrame(self.shots_frame, fg_color=("gray90", "gray25"))
        shot_container.pack(fill="x", padx=12, pady=8)

        # Shot header with number and status
        header_frame = ctk.CTkFrame(shot_container, fg_color="transparent")
        header_frame.pack(fill="x", padx=16, pady=(16, 8))

        shot_title = ctk.CTkLabel(
            header_frame,
            text=f"🎬 Shot {shot.id}",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        shot_title.pack(anchor="w", side="left")

        # Status indicator
        status_indicator = ctk.CTkLabel(
            header_frame,
            text="⏳ Ready",
            font=ctk.CTkFont(size=12),
            text_color=("gray60", "gray40")
        )
        status_indicator.pack(anchor="e", side="right")

        # Content area with text and controls
        content_frame = ctk.CTkFrame(shot_container, fg_color="transparent")
        content_frame.pack(fill="x", padx=16, pady=(0, 16))

        # Left side: text and generate button
        left_section = ctk.CTkFrame(content_frame, fg_color="transparent")
        left_section.pack(side="left", fill="y")

        txt = ctk.CTkTextbox(
            left_section,
            height=160,
            width=360,
            font=ctk.CTkFont(size=12)
        )
        txt.insert("1.0", shot.text)

        btn_gen = ctk.CTkButton(
            left_section,
            text="🎨 Generate Image",
            command=lambda s=shot, t_ref=txt: self._generate_one(s.id, t_ref),
            height=36,
            font=ctk.CTkFont(size=13),
            fg_color="#1d4ed8",
            hover_color="#1e40af"
        )
        # tooltips disabled

        txt.pack(pady=(0, 8), fill="x")
        btn_gen.pack(fill="x")

        # Right side: preview and action buttons
        right_section = ctk.CTkFrame(content_frame, fg_color="transparent")
        right_section.pack(side="right", fill="y", padx=(16, 0))

        # Preview area
        preview = self._create_preview_widget(right_section)

        # Action buttons (Save only)
        action_buttons = self._create_action_buttons(right_section, shot.id, status_indicator)

        return {
            "container": shot_container,
            "txt": txt,
            "btn_gen": btn_gen,
            "preview": preview,
            "btn_save": action_buttons["btn_save"],
            "status_indicator": status_indicator,
        }

    def _create_preview_widget(self, parent) -> ctk.CTkLabel:
        """Create preview widget for shot images."""
        preview_frame = ctk.CTkFrame(parent, fg_color=("gray85", "gray30"), width=220, height=140)
        preview_frame.pack(pady=(0, 12))

        preview_frame.grid_columnconfigure(0, weight=1)
        preview_frame.grid_rowconfigure(0, weight=1)

        preview = ctk.CTkLabel(
            preview_frame,
            text="📷 No preview",
            font=ctk.CTkFont(size=12),
            text_color=("gray50", "gray60")
        )
        preview.grid(row=0, column=0, sticky="nsew")

        # Setup preview callback
        preview._image_ref = None  # type: ignore[attr-defined]
        def set_preview(data_url: str, widget=preview, indicator=None, on_click_path: str | None = None) -> None:
            try:
                cimg = data_url_to_ctkimage(data_url, max_width=150)
                widget.configure(image=cimg, text="")
                widget._image_ref = cimg  # type: ignore[attr-defined]
                if indicator:
                    indicator.configure(text="✅ Generated", text_color="#10b981")
                # Click to open if path provided later
                def _on_click(_e=None, path=on_click_path):
                    if path:
                        try:
                            import subprocess, os, sys
                            if sys.platform.startswith("win"):
                                os.startfile(path)  # type: ignore[attr-defined]
                            elif sys.platform == "darwin":
                                subprocess.run(["open", path], check=False)
                            else:
                                subprocess.run(["xdg-open", path], check=False)
                        except Exception:
                            pass
                widget.bind("<Button-1>", _on_click)
            except Exception:
                widget.configure(text="❌ Preview error", text_color=("red", "darkred"))
                if indicator:
                    indicator.configure(text="❌ Error", text_color=("red", "darkred"))

        preview.set_preview = set_preview  # type: ignore[attr-defined]

        return preview

    def _create_action_buttons(self, parent, shot_id: int, status_indicator) -> dict[str, ctk.CTkButton]:
        """Create action buttons for a shot."""
        actions_frame = ctk.CTkFrame(parent, fg_color="transparent")
        actions_frame.pack(fill="x")

        btn_save = ctk.CTkButton(
            actions_frame,
            text="💾 Save",
            state="disabled",
            command=lambda sid=shot_id: self._save_original(sid),
            height=32,
            font=ctk.CTkFont(size=11),
            fg_color="#166534",
            hover_color="#14532d"
        )
        # tooltips disabled

        btn_save.pack(side="left", padx=(0, 0), expand=True, fill="x")

        return {
            "btn_save": btn_save,
        }

    def _generate_one(self, shot_id: int, txt_widget: ctk.CTkTextbox) -> None:
        self._on_log(f"🎨 Starting generation for shot {shot_id}")
        if not self.app_state.style_data_url:
            self._on_log(f"❌ No style image loaded - generation cancelled for shot {shot_id}")
            self.show_toast("🎨 Please select a style image first", duration_ms=3000)
            return

        # Update button and status
        widgets = self.shot_widgets.get(shot_id)
        if widgets:
            btn_gen = widgets.get("btn_gen")
            status_indicator = widgets.get("status_indicator")
            if btn_gen:
                btn_gen.configure(state="disabled", text="⏳ Generating...")
            if status_indicator:
                status_indicator.configure(text="🎨 Creating...", text_color="#f59e0b")

        self.app_state.in_progress[shot_id] = True
        self._on_log(f"🔄 UI updated for shot {shot_id}, starting generation thread...")

        def worker() -> None:
            self._on_log(f"🧵 Generation worker thread started for shot {shot_id}")
            try:
                text_val = txt_widget.get("1.0", "end").strip()
                text_preview = text_val[:30] + "..." if len(text_val) > 30 else text_val
                self._on_log(f"📝 Shot {shot_id} text: '{text_preview}'")
                url = self.pipeline.generate_one(self.app_state.style_data_url, text_val)
                self._on_log(f"✅ Generation completed successfully for shot {shot_id}")
                self.events.put(("gen_done", shot_id, url))
            except Exception as e:  # noqa: BLE001
                self._on_log(f"❌ Generation failed for shot {shot_id}: {e}")
                self.events.put(("gen_error", shot_id, str(e)))

        threading.Thread(target=worker, daemon=True).start()

        # register event handling
        def on_event() -> None:
            try:
                updated = False
                while True:
                    evt = self.events.get_nowait()
                    kind = evt[0]
                    if kind == "gen_done" and evt[1] == shot_id:
                        _k, _sid, url = evt
                        self.app_state.results[shot_id] = url
                        widgets = self.shot_widgets.get(shot_id)
                        if widgets:
                            prev = widgets.get("preview")
                            if prev is not None and hasattr(prev, "set_preview"):
                                prev.set_preview(url)  # type: ignore[attr-defined]
                            btn_save = widgets.get("btn_save")
                            status_indicator = widgets.get("status_indicator")
                            if btn_save: btn_save.configure(state="disabled")
                            if status_indicator:
                                status_indicator.configure(text="⏳ Processing...", text_color="#f59e0b")

                        # Reset generate button
                        btn_gen = widgets.get("btn_gen")
                        if btn_gen:
                            btn_gen.configure(state="normal", text="🎨 Generate Image")

                        self._on_log(f"Shot {shot_id} generated")
                        self.show_toast(f"🎬 Shot {shot_id} complete!", duration_ms=2000)
                        self.app_state.in_progress[shot_id] = False
                        updated = True
                    elif kind == "gen_error" and evt[1] == shot_id:
                        _k, _sid, msg = evt
                        self._on_log(f"Shot {shot_id} failed: {msg}")
                        self.app_state.errors[shot_id] = msg
                        widgets = self.shot_widgets.get(shot_id)
                        if widgets:
                            status_indicator = widgets.get("status_indicator")
                            btn_gen = widgets.get("btn_gen")
                            if status_indicator:
                                status_indicator.configure(text="❌ Failed", text_color="#ef4444")
                            if btn_gen:
                                btn_gen.configure(state="normal", text="🔄 Retry")
                        self.app_state.in_progress[shot_id] = False
                        self.show_toast(f"❌ Shot {shot_id} failed. Check log for details.", duration_ms=3000)
                        updated = True
                if updated:
                    self.update_idletasks()
            except queue.Empty:
                pass

        self.after(50, on_event)

    def _generate_shots_from_context(self) -> None:
        self._on_log("🎭 Generating shots from context")
        if not self.app_state.middle_frame_data_url:
            self._on_log("❌ No middle frame available - run Analyze first")
            self.show_toast("Run Analyze first to get context.", duration_ms=3000)
            return
        # Read latest edited context
        ctx = self.txt_context.get("1.0", "end").strip()
        if not ctx:
            self._on_log("❌ Context is empty - cannot generate shots")
            self.show_toast("Context is empty.", duration_ms=3000)
            return

        self._set_status("🎬 Calling Director to generate shots from context...")
        self.btn_gen_all.configure(state="disabled", text="⏳ Generating...")
        self.btn_analyze.configure(state="disabled")

        self.show_toast("🎬 Generating shots...", duration_ms=2000)

        def worker() -> None:
            self._on_log("🧵 Director worker thread started")
            try:
                shots = self.pipeline.generate_shots_from_context(
                    self.app_state.middle_frame_data_url or "",
                    ctx,
                    cancel=self.app_state.cancel_event,
                    shot_count=self.app_state.shot_count,
                )
                self.events.put(("shots_done", shots))
            except Exception as e:  # noqa: BLE001
                self.events.put(("error", f"Generate shots failed: {e}"))

        threading.Thread(target=worker, daemon=True).start()

        # Let the main event loop handle the shots_done event

    # ---------- Startup checks ----------
    def _post_init_checks(self) -> None:
        # Disable actions if API key missing
        if not (self.app_state.cfg and self.app_state.cfg.openrouter_api_key):
            try:
                self.btn_analyze.configure(state="disabled")
                self.btn_gen_all.configure(state="disabled")
            except Exception:
                pass
            self._on_log("OPENROUTER_API_KEY missing; analysis and image generation may fail.")
            self._set_status("API key missing")

        def worker() -> None:
            try:
                ok, msg = connectivity_probe()
                self.events.put(("conn_check", ok, msg))
            except Exception as e:  # noqa: BLE001
                self.events.put(("conn_check", False, str(e)))

        threading.Thread(target=worker, daemon=True).start()

    # ---------- Save & Upscale ----------
    def _save_original(self, shot_id: int) -> None:
        self._on_log(f"💾 Starting save operation for shot {shot_id}")
        from tkinter.filedialog import asksaveasfilename
        up = self.app_state.upscaled.get(shot_id)
        if not up:
            self._on_log(f"❌ No upscaled data found for shot {shot_id}")
            return
        data_size = len(up)
        ext = ".png"

        self._on_log(f"📁 Opening save dialog for shot {shot_id}...")
        path = asksaveasfilename(defaultextension=ext, initialfile=f"storyboard_shot_{shot_id:03d}{ext}")
        if not path:
            self._on_log(f"❌ Save operation cancelled for shot {shot_id}")
            return

        try:
            self._on_log(f"💾 Writing {data_size:,} bytes to {os.path.basename(path)}...")
            with open(path, "wb") as f:
                f.write(up)
            self._on_log(f"✅ Saved upscaled for shot {shot_id}: {os.path.basename(path)} ({data_size:,} bytes)")
        except Exception as e:  # noqa: BLE001
            self._on_log(f"❌ Save failed for shot {shot_id}: {e}")

    def _upscale(self, shot_id: int) -> None:
        # Deprecated: kept as no-op for safety if any bindings remain
        self._on_log(f"ℹ️ Upscale is automatic now for shot {shot_id}")

    def _save_upscaled(self, shot_id: int) -> None:
        # Deprecated: Save button now saves upscaled via _save_original
        self._save_original(shot_id)

    # ---------- Settings ----------
    def _open_settings(self) -> None:
        self._on_log("⚙️ Opening settings dialog...")
        cfg = self.app_state.cfg or load_config()
        self._on_log(f"📋 Current configuration: context_model={cfg.context_model}, director_model={cfg.director_model}, image_model={cfg.image_model}")
        win = ctk.CTkToplevel(self)
        win.title("Settings")
        win.geometry("420x300")

        lbl_api = ctk.CTkLabel(win, text="OPENROUTER_API_KEY")
        ent_api = ctk.CTkEntry(win, width=360)
        ent_api.insert(0, os.getenv("OPENROUTER_API_KEY", cfg.openrouter_api_key or ""))

        lbl_ctx = ctk.CTkLabel(win, text="Context Model")
        ent_ctx = ctk.CTkEntry(win, width=360)
        ent_ctx.insert(0, cfg.context_model)

        lbl_dir = ctk.CTkLabel(win, text="Director Model")
        ent_dir = ctk.CTkEntry(win, width=360)
        ent_dir.insert(0, cfg.director_model)

        lbl_img = ctk.CTkLabel(win, text="Image Model")
        ent_img = ctk.CTkEntry(win, width=360)
        ent_img.insert(0, cfg.image_model)

        def save_settings() -> None:
            self._on_log("💾 Applying runtime settings...")
            from dataclasses import replace
            new_cfg = replace(cfg,
                              openrouter_api_key=ent_api.get().strip() or None,
                              context_model=ent_ctx.get().strip() or cfg.context_model,
                              director_model=ent_dir.get().strip() or cfg.director_model,
                              image_model=ent_img.get().strip() or cfg.image_model)

            # Log configuration changes
            changes = []
            if new_cfg.context_model != cfg.context_model:
                changes.append(f"context_model: {cfg.context_model} → {new_cfg.context_model}")
            if new_cfg.director_model != cfg.director_model:
                changes.append(f"director_model: {cfg.director_model} → {new_cfg.director_model}")
            if new_cfg.image_model != cfg.image_model:
                changes.append(f"image_model: {cfg.image_model} → {new_cfg.image_model}")
            if new_cfg.openrouter_api_key != cfg.openrouter_api_key:
                old_masked = "***" if cfg.openrouter_api_key else "None"
                new_masked = "***" if new_cfg.openrouter_api_key else "None"
                changes.append(f"api_key: {old_masked} → {new_masked}")

            if changes:
                self._on_log(f"🔄 Configuration changes: {', '.join(changes)}")
            else:
                self._on_log("ℹ️ No configuration changes detected")

            self.app_state.cfg = new_cfg
            self.pipeline.reload_config(new_cfg)
            self._on_log("✅ Settings applied (runtime). Restart to persist.")
            win.destroy()

        def write_env_and_save() -> None:
            self._on_log("💾 Writing settings to .env file...")
            env_map = {
                "OPENROUTER_API_KEY": ent_api.get().strip(),
                "V2_OPENROUTER_CONTEXT_MODEL": ent_ctx.get().strip(),
                "V2_OPENROUTER_DIRECTOR_MODEL": ent_dir.get().strip(),
                "V2_OPENROUTER_IMAGE_MODEL": ent_img.get().strip(),
            }

            # Log what we're writing (mask sensitive data)
            log_map = env_map.copy()
            if log_map["OPENROUTER_API_KEY"]:
                log_map["OPENROUTER_API_KEY"] = "***masked***"
            self._on_log(f"📝 Writing environment variables: {log_map}")

            try:
                self._write_env(env_map)
                self._on_log("✅ .env file updated successfully")
            except Exception as e:  # noqa: BLE001
                self._on_log(f"❌ Failed to write .env: {e}")
            save_settings()

        def test_connectivity() -> None:
            api_key = ent_api.get().strip()
            ok_base, msg_base = connectivity_probe()
            msg = f"Base: {'OK' if ok_base else 'FAIL'} ({msg_base})"
            if api_key:
                ok_models, msg_models = openrouter_models_probe(api_key)
                ok_chat, msg_chat = openrouter_chat_probe(api_key, ent_ctx.get().strip() or cfg.context_model)
                msg += f" | Models: {'OK' if ok_models else 'FAIL'} ({msg_models}) | Chat: {'OK' if ok_chat else 'FAIL'} ({msg_chat})"
            self._on_log(f"Connectivity: {msg}")
            try:
                lbl_test.configure(text=msg)
            except Exception:
                pass

        btn_save = ctk.CTkButton(win, text="Save", command=save_settings)
        btn_save_env = ctk.CTkButton(win, text="Save + Write .env", command=write_env_and_save)
        btn_test = ctk.CTkButton(win, text="Test Connectivity", command=test_connectivity)
        lbl_test = ctk.CTkLabel(win, text="", anchor="w")

        lbl_api.pack(padx=12, pady=(12, 4), anchor="w")
        ent_api.pack(padx=12, pady=(0, 8))
        lbl_ctx.pack(padx=12, pady=(8, 4), anchor="w")
        ent_ctx.pack(padx=12, pady=(0, 8))
        lbl_dir.pack(padx=12, pady=(8, 4), anchor="w")
        ent_dir.pack(padx=12, pady=(0, 8))
        lbl_img.pack(padx=12, pady=(8, 4), anchor="w")
        ent_img.pack(padx=12, pady=(0, 8))
        btn_test.pack(padx=12, pady=(8, 4))
        lbl_test.pack(padx=12, pady=(0, 4), fill="x")
        btn_save.pack(padx=12, pady=(8, 4))
        btn_save_env.pack(padx=12, pady=(0, 12))

    # ---------- .env ----------
    def _write_env(self, kv: dict[str, str]) -> None:
        root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        env_path = os.path.join(root_dir, ".env")
        # Load existing
        existing: dict[str, str] = {}
        if os.path.exists(env_path):
            try:
                with open(env_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith("#") or "=" not in line:
                            continue
                        k, v = line.split("=", 1)
                        existing[k.strip()] = v.strip()
            except Exception:
                pass
        # Update and write
        existing.update({k: v for k, v in kv.items() if v is not None})
        lines = [f"{k}={v}\n" for k, v in existing.items()]
        with open(env_path, "w", encoding="utf-8") as f:
            f.writelines(lines)

    # ---------- Toasts ----------
    def show_toast(self, message: str, *, duration_ms: int = 2500) -> None:
        try:
            toast = ctk.CTkToplevel(self)
            toast.overrideredirect(True)
            toast.attributes("-topmost", True)
            lbl = ctk.CTkLabel(toast, text=message)
            lbl.pack(padx=12, pady=8)
            self.update_idletasks()
            x = self.winfo_x() + self.winfo_width() - toast.winfo_reqwidth() - 24
            y = self.winfo_y() + self.winfo_height() - toast.winfo_reqheight() - 48
            toast.geometry(f"+{x}+{y}")
            toast.after(duration_ms, toast.destroy)
        except Exception:
            pass


