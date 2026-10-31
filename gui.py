"""
A window for the plane projection: choose the files, run, and watch the frames.

Usage:
    python gui.py
It runs exactly the same code as Ex0.py (projection.pipeline).
"""
import os
import queue
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from PIL import ImageTk                                             # noqa: E402

from projection import pipeline                                     # noqa: E402
from projection.errors import ProjectionError                       # noqa: E402
from projection.preview import PREVIEW_BOX, default_output, to_preview   # noqa: E402

POLL_MS = 30            # how often the window reads messages from the worker thread
PLAY_MS = 100           # 10 frames per second, like the video


class ProjectionApp:
    """The main window. The projection runs in a worker thread; it never touches the window,
    it only puts messages in a queue that the window reads (tkinter is not thread safe)."""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.messages = queue.Queue()
        self.previews = []              # one small image per frame, for the slider
        self.photo = None               # keeps the shown image alive (tkinter would drop it)
        self.playing = False
        self.auto_output = True         # the output name follows the volume until the user picks one

        root.title("Plane Projection")
        root.minsize(820, 560)
        self._build()

    # ---------- layout ----------

    def _build(self):
        files = ttk.Frame(self.root, padding=10)
        files.pack(fill="x")
        self.nrrd = tk.StringVar()
        self.csv = tk.StringVar()
        self.mp4 = tk.StringVar()
        rows = [("Volume (NRRD):", self.nrrd, self._browse_nrrd),
                ("Planes (CSV):", self.csv, self._browse_csv),
                ("Output (MP4):", self.mp4, self._browse_mp4)]
        for r, (label, var, command) in enumerate(rows):
            ttk.Label(files, text=label).grid(row=r, column=0, sticky="w", pady=2)
            ttk.Entry(files, textvariable=var).grid(row=r, column=1, sticky="ew", padx=6)
            ttk.Button(files, text="Browse...", command=command).grid(row=r, column=2)
        files.columnconfigure(1, weight=1)

        buttons = ttk.Frame(self.root, padding=(10, 0))
        buttons.pack(fill="x")
        self.run_button = ttk.Button(buttons, text="Run", command=self._run)
        self.run_button.pack(side="left")
        self.open_button = ttk.Button(buttons, text="Open video", command=self._open_video, state="disabled")
        self.open_button.pack(side="left", padx=6)
        self.progress = ttk.Progressbar(buttons, mode="determinate")
        self.progress.pack(side="left", fill="x", expand=True, padx=6)
        self.status = ttk.Label(buttons, text="Choose the files and press Run", width=28)
        self.status.pack(side="left")

        body = ttk.Frame(self.root, padding=10)
        body.pack(fill="both", expand=True)

        viewer = ttk.Frame(body)
        viewer.pack(side="left", fill="y")
        height, width = PREVIEW_BOX
        canvas = tk.Frame(viewer, width=width, height=height, background="black")
        canvas.pack()
        canvas.pack_propagate(False)                        # keep the box size fixed
        self.image_label = tk.Label(canvas, background="black")
        self.image_label.pack(expand=True)
        controls = ttk.Frame(viewer)
        controls.pack(fill="x", pady=4)
        self.play_button = ttk.Button(controls, text="Play", width=6, command=self._toggle_play, state="disabled")
        self.play_button.pack(side="left")
        self.slider = ttk.Scale(controls, from_=0, to=0, command=self._on_slider, state="disabled")
        self.slider.pack(side="left", fill="x", expand=True, padx=6)
        self.frame_label = ttk.Label(controls, text="", width=9)
        self.frame_label.pack(side="left")

        self.log = ScrolledText(body, height=10, wrap="word", state="disabled", font=("Consolas", 9))
        self.log.pack(side="left", fill="both", expand=True, padx=(10, 0))
        self.log.tag_config("warning", foreground="#b36b00")
        self.log.tag_config("error", foreground="#c62828")

    # ---------- choosing files ----------

    def _browse_nrrd(self):
        path = filedialog.askopenfilename(title="Volume", initialdir=ROOT / "data",
                                          filetypes=[("NRRD volume", "*.nrrd"), ("All files", "*.*")])
        if path:
            self.nrrd.set(str(Path(path)))                          # Windows style \ on Windows
            if self.auto_output or not self.mp4.get():
                self.mp4.set(default_output(path))

    def _browse_csv(self):
        path = filedialog.askopenfilename(title="Planes", initialdir=ROOT / "experiments" / "planes",
                                          filetypes=[("CSV planes", "*.csv"), ("All files", "*.*")])
        if path:
            self.csv.set(str(Path(path)))

    def _browse_mp4(self):
        path = filedialog.asksaveasfilename(title="Output video", defaultextension=".mp4",
                                            filetypes=[("MP4 video", "*.mp4")])
        if path:
            self.mp4.set(str(Path(path)))
            self.auto_output = False                                # the user chose it: keep it

    # ---------- running ----------

    def _run(self):
        paths = [self.nrrd.get().strip(), self.csv.get().strip(), self.mp4.get().strip()]
        if not all(paths):
            messagebox.showwarning("Plane Projection", "Please choose a volume, a CSV file and an output file.")
            return
        self._stop_play()
        self.previews.clear()
        self._clear_log()
        self.progress["value"] = 0
        self.run_button.config(state="disabled")
        self.open_button.config(state="disabled")
        self.play_button.config(state="disabled")
        self.slider.config(state="disabled")
        self.status.config(text="Running...")
        threading.Thread(target=self._work, args=paths, daemon=True).start()
        self.root.after(POLL_MS, self._poll)

    def _work(self, nrrd, csv, mp4):
        """Runs in the worker thread: only puts messages in the queue."""
        def on_frame(index, total, frame):
            self.messages.put(("frame", index, total, to_preview(frame)))
        try:
            summary = pipeline.run(nrrd, csv, mp4, log=lambda m: self.messages.put(("log", m)), on_frame=on_frame)
            self.messages.put(("done", summary))
        except ProjectionError as e:
            self.messages.put(("error", str(e)))
        except Exception as e:                                       # NFR-2: a message, not a crash
            self.messages.put(("error", f"unexpected problem ({type(e).__name__}: {e})"))

    def _poll(self):
        """Runs in the window thread: shows everything the worker reported since the last poll."""
        last_frame = None
        try:
            while True:
                message = self.messages.get_nowait()
                kind = message[0]
                if kind == "log":
                    self._write_log(message[1])
                elif kind == "frame":
                    _, index, total, image = message
                    self.previews.append(image)
                    self.progress.config(maximum=total, value=index + 1)
                    self.status.config(text=f"{index + 1} / {total} planes")
                    last_frame = index
                elif kind == "done":
                    self._finished(message[1])
                    return
                elif kind == "error":
                    self._failed(message[1])
                    return
        except queue.Empty:
            pass
        if last_frame is not None:
            self._show(last_frame)                      # only the newest frame, so the window keeps up
        self.root.after(POLL_MS, self._poll)

    def _finished(self, summary):
        self.status.config(text=f"Done: {summary.frames} frames")
        self.run_button.config(state="normal")
        self.open_button.config(state="normal")
        if self.previews:
            self.slider.config(to=len(self.previews) - 1, state="normal")
            self.play_button.config(state="normal")
            self._show(0)

    def _failed(self, error):
        self._write_log(f"Error: {error}")
        self.status.config(text="Failed")
        self.run_button.config(state="normal")
        messagebox.showerror("Plane Projection", error)

    # ---------- preview ----------

    def _show(self, index):
        self.photo = ImageTk.PhotoImage(self.previews[index])
        self.image_label.config(image=self.photo)
        self.frame_label.config(text=f"{index + 1} / {len(self.previews)}")
        if str(self.slider.cget("state")) == "normal":
            self.slider.set(index)

    def _on_slider(self, value):
        if self.previews and str(self.slider.cget("state")) == "normal":
            index = round(float(value))
            if self.frame_label.cget("text") != f"{index + 1} / {len(self.previews)}":
                self._show(index)

    def _toggle_play(self):
        if self.playing:
            self._stop_play()
        else:
            self.playing = True
            self.play_button.config(text="Pause")
            self._play_step(round(float(self.slider.get())))

    def _play_step(self, index):
        if not self.playing:
            return
        if index >= len(self.previews):
            index = 0                                               # start again from the first frame
        self._show(index)
        self.root.after(PLAY_MS, self._play_step, index + 1)

    def _stop_play(self):
        self.playing = False
        self.play_button.config(text="Play")

    # ---------- log and video ----------

    def _write_log(self, text):
        tag = "warning" if text.startswith("Warning") else "error" if text.startswith("Error") else ""
        self.log.config(state="normal")
        self.log.insert("end", text + "\n", tag)
        self.log.see("end")
        self.log.config(state="disabled")

    def _clear_log(self):
        self.log.config(state="normal")
        self.log.delete("1.0", "end")
        self.log.config(state="disabled")

    def _open_video(self):
        path = self.mp4.get()
        if sys.platform.startswith("win"):
            os.startfile(path)                                      # the default video player
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])


def main():
    root = tk.Tk()
    ProjectionApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
