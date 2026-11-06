import json
import os
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

from app.lesson_engine import render_lesson

ROOT = Path(__file__).resolve().parent.parent


class MentivioApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Mentivio")
        self.geometry("920x680")
        self.minsize(820, 620)
        self.configure(bg="#f3f7fb")

        self.country_var = tk.StringVar(value="India")
        self.board_var = tk.StringVar(value="CBSE")
        self.class_var = tk.StringVar(value="10")
        self.subject_var = tk.StringVar(value="Mathematics")
        self.chapter_var = tk.StringVar(value="Triangles")
        self.topic_var = tk.StringVar(value="Similar Triangles and Basic Proportionality Theorem (BPT)")
        self.language_var = tk.StringVar(value="English")
        self.subtitle_var = tk.StringVar(value="English")
        self.fps_var = tk.StringVar(value="24")
        self.result = None

        self._build_ui()

    def _build_ui(self):
        header = tk.Label(
            self,
            text="Mentivio",
            font=("Segoe UI", 24, "bold"),
            bg="#f3f7fb",
            fg="#162033",
            pady=12,
        )
        header.pack(fill="x")

        subtitle = tk.Label(
            self,
            text="Understand visually. Learn in any language.",
            font=("Segoe UI", 12),
            bg="#f3f7fb",
            fg="#4a5d7a",
            pady=12,
        )
        subtitle.pack(fill="x")

        form = ttk.Frame(self, padding=16)
        form.pack(fill="both", expand=True)

        fields = [
            ("Country", self.country_var, ["India"]),
            ("Education Board", self.board_var, ["CBSE"]),
            ("Class / Grade", self.class_var, ["10"]),
            ("Subject", self.subject_var, ["Mathematics"]),
            ("Chapter", self.chapter_var, ["Triangles"]),
            ("Topic", self.topic_var, ["Similar Triangles and Basic Proportionality Theorem (BPT)"]),
            ("Teaching Language", self.language_var, ["English", "Telugu"]),
            ("Subtitle Language", self.subtitle_var, ["English", "Telugu"]),
            ("Frame Rate", self.fps_var, ["24", "25", "30"]),
        ]

        for index, (label_text, var, options) in enumerate(fields):
            row = ttk.Frame(form)
            row.pack(fill="x", pady=6)
            label = ttk.Label(row, text=label_text, width=22, anchor="w")
            label.pack(side="left")
            combo = ttk.Combobox(row, textvariable=var, values=options, state="readonly", width=40)
            combo.pack(side="left", padx=(10, 0), fill="x", expand=True)

        action_bar = ttk.Frame(form)
        action_bar.pack(fill="x", pady=(16, 8))
        render_btn = ttk.Button(action_bar, text="Create an Animated Lesson", command=self.start_render)
        render_btn.pack(side="left")

        self.status_var = tk.StringVar(value="Ready")
        status = ttk.Label(action_bar, textvariable=self.status_var, foreground="#234a71")
        status.pack(side="left", padx=(12, 0))

        output_frame = ttk.LabelFrame(self, text="Generated Output", padding=12)
        output_frame.pack(fill="both", expand=True, padx=16, pady=(0, 16))

        self.output_text = tk.Text(output_frame, height=12, wrap="word", state="disabled", font=("Segoe UI", 10))
        self.output_text.pack(fill="both", expand=True)

        button_row = ttk.Frame(output_frame)
        button_row.pack(fill="x", pady=(12, 0))

        self.open_video_btn = ttk.Button(button_row, text="Open MP4", command=self.open_mp4)
        self.open_video_btn.pack(side="left", padx=(0, 8))

        self.open_dir_btn = ttk.Button(button_row, text="Open Output Folder", command=self.open_output_folder)
        self.open_dir_btn.pack(side="left")

    def start_render(self):
        self.status_var.set("Generating lesson scenes, narration, and MP4 locally...")
        self.output_text.config(state="normal")
        self.output_text.delete("1.0", tk.END)
        self.output_text.insert(tk.END, "Render started...\n")
        self.output_text.config(state="disabled")

        worker = threading.Thread(target=self._render_worker, daemon=True)
        worker.start()

    def _render_worker(self):
        try:
            kwargs = {
                "language": self.language_var.get(),
                "subtitle_language": self.subtitle_var.get(),
                "fps": int(self.fps_var.get()),
            }
            result = render_lesson(**kwargs)
            self.result = result
            self.after(0, self._update_result, result)
        except Exception as exc:  # pragma: no cover - UI error surface
            self.after(0, self._handle_error, exc)

    def _update_result(self, result):
        self.status_var.set("Lesson rendered successfully.")
        summary = [
            f"Video: {result['video_path']}",
            f"Subtitles: {result['subtitle_path']}",
            f"Script: {result['script_path']}",
            f"Scene Breakdown: {result['scene_breakdown_path']}",
            f"Validation Report: {result['validation_report_path']}",
            f"Narration status: {result['narration_status']}",
            f"Duration: {result['duration_seconds']:.3f} s",
            f"FPS: {result['fps']:.3f}",
        ]
        self.output_text.config(state="normal")
        self.output_text.delete("1.0", tk.END)
        for line in summary:
            self.output_text.insert(tk.END, line + "\n")
        self.output_text.config(state="disabled")

    def _handle_error(self, exc):
        self.status_var.set("Render failed")
        self.output_text.config(state="normal")
        self.output_text.delete("1.0", tk.END)
        self.output_text.insert(tk.END, f"Error: {exc}\n")
        self.output_text.config(state="disabled")
        messagebox.showerror("Mentivio", f"Render failed: {exc}")

    def open_mp4(self):
        if not self.result:
            messagebox.showinfo("Mentivio", "No rendered video available yet.")
            return
        video_path = Path(self.result["video_path"])
        if not video_path.exists():
            messagebox.showwarning("Mentivio", f"Video not found: {video_path}")
            return
        self._open_file(video_path)

    def open_output_folder(self):
        output_dir = ROOT / "output" / "lesson_bpt"
        self._open_file(output_dir)

    @staticmethod
    def _open_file(path):
        if os.name == "nt":
            os.startfile(path)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(path)])
        else:
            subprocess.Popen(["xdg-open", str(path)])


def main():
    app = MentivioApp()
    app.mainloop()


if __name__ == "__main__":
    main()
