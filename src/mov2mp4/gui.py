import queue
import shutil
import sys
import threading
import tkinter as tk
from tkinter import filedialog, font as tkfont, messagebox, ttk

from .config import PRESETS, load_settings
from .converter import convert_batch
from .logging_config import configure_logging
from .opener import open_folder


class ConverterGUI(tk.Tk):
    NORMAL_AREA_RATIO = 0.20

    def __init__(self, settings, logger):
        super().__init__()

        self.settings = settings
        self.logger = logger
        self.queue = queue.Queue()
        self.cancel_event = threading.Event()
        self.out_dir = None
        self.crf_value = str(settings.default_crf)
        self.preset_value = settings.default_preset
        self.ui_scale = 1.0

        self.title("MOV → MP4 Converter")
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        self._configure_fonts()
        self._configure_window()
        self._configure_styles()
        self._build_layout()

        self.bind("<Configure>", self._on_resize)

    def _screen_size(self):
        self.update_idletasks()
        return self.winfo_screenwidth(), self.winfo_screenheight()

    def _geometry_centered(self, width, height):
        screen_w, screen_h = self._screen_size()
        x = max(0, (screen_w - width) // 2)
        y = max(0, (screen_h - height) // 2)
        return f"{width}x{height}+{x}+{y}"

    def _configure_window(self):
        screen_w, screen_h = self._screen_size()

        side_ratio = self.NORMAL_AREA_RATIO ** 0.5
        width = int(screen_w * side_ratio)
        height = int(screen_h * side_ratio)

        width = max(460, min(width, int(screen_w * 0.95)))
        height = max(260, min(height, int(screen_h * 0.9)))

        min_width = min(width, max(420, int(screen_w * 0.25)))
        min_height = min(height, max(220, int(screen_h * 0.22)))

        self.geometry(self._geometry_centered(width, height))
        self.minsize(min_width, min_height)
        self.resizable(True, True)

        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

    def _configure_fonts(self):
        default = tkfont.nametofont("TkDefaultFont")
        family = default.actual("family")

        self.font_title = tkfont.Font(family=family, size=12, weight="bold")
        self.font_normal = tkfont.Font(family=family, size=10)
        self.font_button = tkfont.Font(family=family, size=10)
        self.font_status = tkfont.Font(family=family, size=10)

    def _configure_styles(self):
        self.style = ttk.Style(self)
        self.style.configure("TFrame")
        self.style.configure("TLabel", font=self.font_normal)
        self.style.configure("TButton", font=self.font_button)
        self.style.configure("TEntry", font=self.font_normal)
        self.style.configure("TCombobox", font=self.font_normal)
        self.style.configure("Title.TLabel", font=self.font_title)
        self.style.configure("Status.TLabel", font=self.font_status)

    def _build_layout(self):
        self.main = ttk.Frame(self)
        self.main.grid(row=0, column=0, sticky="nsew")

        self.main.columnconfigure(0, weight=1)
        self.main.rowconfigure(5, weight=1)

        self.status_var = tk.StringVar(value="Listo.")

        self.title_label = ttk.Label(
            self.main,
            text="MOV → MP4 Converter",
            style="Title.TLabel",
            anchor="center",
        )
        self.title_label.grid(row=0, column=0, sticky="ew")

        self.btn_quality = ttk.Button(
            self.main,
            text="Ajustes de calidad",
            command=self.show_quality_settings,
        )
        self.btn_quality.grid(row=1, column=0, sticky="ew")

        self.btn_convert = ttk.Button(
            self.main,
            text="Seleccionar y convertir",
            command=self.start,
        )
        self.btn_convert.grid(row=2, column=0, sticky="ew")

        self.btn_cancel = ttk.Button(
            self.main,
            text="Cancelar",
            state="disabled",
            command=self.cancel,
        )
        self.btn_cancel.grid(row=3, column=0, sticky="ew")

        self.progress = ttk.Progressbar(
            self.main,
            orient="horizontal",
            mode="determinate",
        )
        self.progress.grid(row=4, column=0, sticky="ew")

        self.status_label = ttk.Label(
            self.main,
            textvariable=self.status_var,
            style="Status.TLabel",
            anchor="center",
            justify="center",
        )
        self.status_label.grid(row=5, column=0, sticky="nsew")

        self._apply_scale()

    def _px(self, value):
        return max(1, int(round(value * self.ui_scale)))

    def _compute_scale(self):
        screen_w, screen_h = self._screen_size()
        width = max(1, self.winfo_width())
        height = max(1, self.winfo_height())

        screen_scale = min(screen_w / 1920, screen_h / 1080)
        window_ratio = min(width / screen_w, height / screen_h)
        normal_ratio = self.NORMAL_AREA_RATIO ** 0.5

        scale = screen_scale * max(0.9, min(1.35, window_ratio / normal_ratio))
        return max(0.9, min(1.5, scale))

    def _apply_scale(self):
        self.ui_scale = self._compute_scale()

        self.font_title.configure(size=self._px(13))
        self.font_normal.configure(size=self._px(10))
        self.font_button.configure(size=self._px(10))
        self.font_status.configure(size=self._px(10))

        pad = self._px(16)
        gap = self._px(8)
        big_gap = self._px(16)

        self.main.configure(padding=pad)

        self.title_label.grid_configure(pady=(0, big_gap))
        self.btn_quality.grid_configure(pady=(0, gap))
        self.btn_convert.grid_configure(pady=(0, gap))
        self.btn_cancel.grid_configure(pady=(0, big_gap))
        self.progress.grid_configure(pady=(0, gap))

        wrap = max(220, self.winfo_width() - 2 * pad)
        self.status_label.configure(wraplength=wrap)

    def _on_resize(self, event):
        if event.widget is self:
            self._apply_scale()

    def show_quality_settings(self):
        top = tk.Toplevel(self)
        top.title("Ajustes de calidad")
        top.transient(self)

        screen_w, screen_h = self._screen_size()
        width = max(360, int(screen_w * 0.28))
        height = max(170, int(screen_h * 0.16))

        width = min(width, int(screen_w * 0.8))
        height = min(height, int(screen_h * 0.5))

        top.geometry(self._geometry_centered(width, height))
        top.minsize(340, 160)
        top.resizable(True, False)

        top.columnconfigure(0, weight=1)
        top.rowconfigure(0, weight=1)

        frame = ttk.Frame(top, padding=self._px(12))
        frame.grid(row=0, column=0, sticky="nsew")

        frame.columnconfigure(1, weight=1)
        frame.columnconfigure(3, weight=1)
        frame.rowconfigure(1, weight=1)

        ttk.Label(frame, text="CRF").grid(row=0, column=0, sticky="w")

        crf_entry = ttk.Entry(frame, width=6)
        crf_entry.insert(0, self.crf_value)
        crf_entry.grid(row=0, column=1, sticky="ew", padx=(self._px(6), self._px(12)))

        ttk.Label(frame, text="Preset").grid(row=0, column=2, sticky="w")

        preset_combo = ttk.Combobox(frame, values=PRESETS, width=12)
        preset_combo.set(self.preset_value)
        preset_combo.grid(row=0, column=3, sticky="ew", padx=(self._px(6), 0))

        help_var = tk.StringVar(
            value="CRF: menor valor implica mayor calidad y archivos más grandes."
        )

        help_label = ttk.Label(
            frame,
            textvariable=help_var,
            style="Status.TLabel",
            anchor="center",
            justify="center",
        )
        help_label.grid(row=1, column=0, columnspan=4, sticky="nsew", pady=self._px(12))

        def update_help_wrap(event):
            if event.widget is top:
                help_label.configure(wraplength=max(240, event.width - self._px(48)))

        top.bind("<Configure>", update_help_wrap)

        crf_entry.bind(
            "<Enter>",
            lambda _: help_var.set("CRF: calidad del video entre 0 y 51. Menor es mejor."),
        )
        crf_entry.bind(
            "<Leave>",
            lambda _: help_var.set("CRF: menor valor implica mayor calidad y archivos más grandes."),
        )
        preset_combo.bind(
            "<Enter>",
            lambda _: help_var.set("Preset: velocidad de codificación contra compresión."),
        )
        preset_combo.bind(
            "<Leave>",
            lambda _: help_var.set("CRF: menor valor implica mayor calidad y archivos más grandes."),
        )

        def apply():
            try:
                crf = int(crf_entry.get())
                if not 0 <= crf <= 51:
                    raise ValueError
            except ValueError:
                messagebox.showerror("Error", "CRF debe ser un número entre 0 y 51.")
                return

            if preset_combo.get() not in PRESETS:
                messagebox.showerror("Error", "Preset inválido.")
                return

            self.crf_value = str(crf)
            self.preset_value = preset_combo.get()
            top.destroy()

        ttk.Button(frame, text="Aplicar", command=apply).grid(
            row=2,
            column=0,
            columnspan=4,
            sticky="ew",
        )

    def start(self):
        files = filedialog.askopenfilenames(
            filetypes=[("MOV", "*.mov")],
            title="Seleccionar archivos .mov",
        )

        if not files:
            return

        out_dir = filedialog.askdirectory(title="Seleccionar carpeta de salida")
        if not out_dir:
            return

        self.out_dir = out_dir
        self.cancel_event.clear()
        self.progress["value"] = 0
        self.status_var.set("Iniciando...")
        self.btn_convert.config(state="disabled")
        self.btn_cancel.config(state="normal")

        thread = threading.Thread(
            target=self._run_conversion,
            args=(files, out_dir),
            daemon=True,
        )
        thread.start()
        self.after(100, self._poll_queue)

    def _run_conversion(self, files, out_dir):
        try:
            def progress(done, total, result):
                self.queue.put(("progress", done / total * 100))
                self.queue.put(("status", f"{done}/{total}"))

            results = convert_batch(
                files,
                out_dir,
                self.settings,
                crf=int(self.crf_value),
                preset=self.preset_value,
                cancel_event=self.cancel_event,
                progress_callback=progress,
                logger=self.logger,
            )

            if self.cancel_event.is_set():
                self.queue.put(("done", ("info", "Conversión cancelada.")))
            elif all(result.success for result in results):
                self.queue.put(("done", ("askopen", "Conversión completada. ¿Abrir carpeta de salida?")))
            else:
                failed = sum(not result.success for result in results)
                self.queue.put(("done", ("warning", f"Conversión terminada con {failed} error(es). Revisá el log.")))
        except Exception as exc:
            self.logger.exception("Unexpected conversion error")
            self.queue.put(("done", ("error", str(exc))))

    def _poll_queue(self):
        try:
            while True:
                kind, value = self.queue.get_nowait()

                if kind == "progress":
                    self.progress["value"] = value
                elif kind == "status":
                    self.status_var.set(value)
                elif kind == "done":
                    self._finish(*value)
                    return
        except queue.Empty:
            self.after(100, self._poll_queue)

    def _finish(self, level, message):
        self.btn_cancel.config(state="disabled")
        self.btn_convert.config(state="normal")

        if level == "askopen":
            if messagebox.askyesno("Listo", message):
                open_folder(self.out_dir)
        elif level == "info":
            messagebox.showinfo("Info", message)
        elif level == "warning":
            messagebox.showwarning("Aviso", message)
        else:
            messagebox.showerror("Error", message)

        self.status_var.set("Listo.")

    def cancel(self):
        self.cancel_event.set()
        self.status_var.set("Cancelando...")

    def on_close(self):
        if self.btn_cancel["state"] == "normal" and not self.cancel_event.is_set():
            if not messagebox.askokcancel("Confirmar", "¿Cancelar conversión y salir?"):
                return

        self.destroy()
        sys.exit(0)


def main():
    settings = load_settings()
    logger = configure_logging(settings.log_file)

    if not shutil.which(settings.ffmpeg_bin):
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("Error", f"No se encontró '{settings.ffmpeg_bin}' en PATH.")
        return 1

    app = ConverterGUI(settings, logger)
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())