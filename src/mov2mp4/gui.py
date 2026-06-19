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
    WINDOW_AREA_RATIO = 0.04
    MIN_FONT_SIZE = 9
    MAX_FONT_SIZE = 32

    def __init__(self, settings, logger):
        super().__init__()

        self.settings = settings
        self.logger = logger
        self.queue = queue.Queue()
        self.cancel_event = threading.Event()
        self.out_dir = None
        self.crf_value = str(settings.default_crf)
        self.preset_value = settings.default_preset
        self.font_size_var = tk.StringVar(value=str(self._initial_font_size()))

        self.title("MOV → MP4 Converter")
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        self._configure_window()
        self._configure_fonts()
        self._build_layout()
        self._apply_font_size()

        self.bind("<Configure>", self._on_resize)

    def _screen_size(self):
        self.update_idletasks()
        return self.winfo_screenwidth(), self.winfo_screenheight()

    def _initial_font_size(self):
        base = getattr(self.settings, "default_font_size", 15)
        try:
            base = int(base)
        except (TypeError, ValueError):
            base = 15

        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        screen_scale = min(screen_w / 1920, screen_h / 1080)
        screen_scale = max(1.0, min(1.35, screen_scale))
        value = round(base * screen_scale)
        return max(self.MIN_FONT_SIZE, min(self.MAX_FONT_SIZE, value))

    def _geometry_centered(self, width, height):
        screen_w, screen_h = self._screen_size()
        x = max(0, (screen_w - width) // 2)
        y = max(0, (screen_h - height) // 2)
        return f"{width}x{height}+{x}+{y}"

    def _configure_window(self):
        screen_w, screen_h = self._screen_size()
        side_ratio = self.WINDOW_AREA_RATIO ** 0.5

        width = int(screen_w * side_ratio)
        height = int(screen_h * side_ratio)

        width = max(560, min(width, int(screen_w * 0.95)))
        height = max(340, min(height, int(screen_h * 0.90)))

        min_width = min(width, max(460, int(screen_w * 0.25)))
        min_height = min(height, max(300, int(screen_h * 0.22)))

        self.geometry(self._geometry_centered(width, height))
        self.minsize(min_width, min_height)
        self.resizable(True, True)

        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

    def _configure_fonts(self):
        default = tkfont.nametofont("TkDefaultFont")
        family = default.actual("family")

        self.font_title = tkfont.Font(family=family, size=19, weight="bold")
        self.font_text = tkfont.Font(family=family, size=15)
        self.font_button = tkfont.Font(family=family, size=15)
        self.font_small = tkfont.Font(family=family, size=13)

    def _build_layout(self):
        self.main = tk.Frame(self)
        self.main.grid(row=0, column=0, sticky="nsew")

        self.main.columnconfigure(0, weight=1)
        self.main.rowconfigure(5, weight=1)

        self.status_var = tk.StringVar(value="Listo.")
        self.help_var = tk.StringVar(
            value=(
                "CRF: 0–51; menor valor implica mayor calidad y archivos más grandes. "
                "Preset: velocidad de codificación vs compresión."
            )
        )

        self.title_label = tk.Label(
            self.main,
            text="MOV → MP4 Converter",
            font=self.font_title,
            anchor="center",
        )
        self.title_label.grid(row=0, column=0, sticky="ew")

        self.btn_quality = tk.Button(
            self.main,
            text="Ajustes de calidad",
            font=self.font_button,
            command=self.show_quality_settings,
        )
        self.btn_quality.grid(row=1, column=0, sticky="ew")

        self.btn_convert = tk.Button(
            self.main,
            text="Seleccionar y convertir",
            font=self.font_button,
            command=self.start,
        )
        self.btn_convert.grid(row=2, column=0, sticky="ew")

        self.btn_cancel = tk.Button(
            self.main,
            text="Cancelar",
            font=self.font_button,
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

        self.status_label = tk.Label(
            self.main,
            textvariable=self.status_var,
            font=self.font_text,
            anchor="center",
            justify="center",
        )
        self.status_label.grid(row=5, column=0, sticky="nsew")

        self.bottom = tk.Frame(self.main)
        self.bottom.grid(row=6, column=0, sticky="ew")
        self.bottom.columnconfigure(0, weight=1)
        self.bottom.columnconfigure(1, weight=0)

        self.help_bar = tk.Label(
            self.bottom,
            textvariable=self.help_var,
            font=self.font_small,
            anchor="w",
            justify="left",
            relief="groove",
        )
        self.help_bar.grid(row=0, column=0, sticky="ew")

        self.font_frame = tk.Frame(self.bottom)
        self.font_frame.grid(row=0, column=1, sticky="e")

        self.font_label = tk.Label(
            self.font_frame,
            text="Texto",
            font=self.font_small,
        )
        self.font_label.grid(row=0, column=0, sticky="w")

        self.font_spin = tk.Spinbox(
            self.font_frame,
            from_=self.MIN_FONT_SIZE,
            to=self.MAX_FONT_SIZE,
            textvariable=self.font_size_var,
            width=5,
            font=self.font_small,
            command=self.apply_font_size_from_control,
        )
        self.font_spin.grid(row=0, column=1)

        self.btn_font_minus = tk.Button(
            self.font_frame,
            text="−",
            width=3,
            font=self.font_small,
            command=lambda: self.change_font_size(-1),
        )
        self.btn_font_minus.grid(row=0, column=2)

        self.btn_font_plus = tk.Button(
            self.font_frame,
            text="+",
            width=3,
            font=self.font_small,
            command=lambda: self.change_font_size(1),
        )
        self.btn_font_plus.grid(row=0, column=3)

        self.font_spin.bind("<Return>", lambda _: self.apply_font_size_from_control())
        self.font_spin.bind("<FocusOut>", lambda _: self.apply_font_size_from_control())

    def _font_size(self):
        try:
            value = int(self.font_size_var.get())
        except (TypeError, ValueError):
            value = getattr(self.settings, "default_font_size", 15)

        return max(self.MIN_FONT_SIZE, min(self.MAX_FONT_SIZE, int(value)))

    def _set_font_size(self, value):
        value = max(self.MIN_FONT_SIZE, min(self.MAX_FONT_SIZE, int(value)))
        self.font_size_var.set(str(value))
        self._apply_font_size()

    def change_font_size(self, delta):
        self._set_font_size(self._font_size() + delta)

    def apply_font_size_from_control(self):
        self._set_font_size(self._font_size())

    def _apply_font_size(self):
        size = self._font_size()

        self.font_title.configure(size=size + 4)
        self.font_text.configure(size=size)
        self.font_button.configure(size=size)
        self.font_small.configure(size=max(self.MIN_FONT_SIZE, size - 2))

        pad = max(12, int(size * 1.2))
        gap = max(6, int(size * 0.6))
        big_gap = max(12, int(size * 1.1))

        self.main.configure(padx=pad, pady=pad)

        self.title_label.grid_configure(pady=(0, big_gap))
        self.btn_quality.grid_configure(pady=(0, gap), ipady=gap)
        self.btn_convert.grid_configure(pady=(0, gap), ipady=gap)
        self.btn_cancel.grid_configure(pady=(0, big_gap), ipady=gap)
        self.progress.grid_configure(pady=(0, gap))
        self.bottom.grid_configure(pady=(big_gap, 0))

        self.help_bar.grid_configure(ipadx=gap, ipady=max(3, gap // 2), padx=(0, gap))
        self.font_label.grid_configure(padx=(0, gap))
        self.font_spin.grid_configure(padx=(0, gap))
        self.btn_font_minus.grid_configure(padx=(0, gap))

        self._update_wraplength()
        self.update_idletasks()

    def _update_wraplength(self):
        width = max(240, self.winfo_width() - 80)
        self.status_label.configure(wraplength=width)

        help_width = max(240, self.winfo_width() - 260)
        self.help_bar.configure(wraplength=help_width)

    def _on_resize(self, event):
        if event.widget is self:
            self._update_wraplength()

    def show_quality_settings(self):
        top = tk.Toplevel(self)
        top.title("Ajustes de calidad")
        top.transient(self)

        screen_w, screen_h = self._screen_size()
        width = max(420, int(screen_w * 0.28))
        height = max(140, int(screen_h * 0.14))

        width = min(width, int(screen_w * 0.80))
        height = min(height, int(screen_h * 0.45))

        top.geometry(self._geometry_centered(width, height))
        top.minsize(380, 130)
        top.resizable(True, False)

        top.columnconfigure(0, weight=1)
        top.rowconfigure(0, weight=1)

        frame = tk.Frame(top)
        frame.grid(row=0, column=0, sticky="nsew")

        frame.columnconfigure(1, weight=1)
        frame.columnconfigure(3, weight=1)

        size = self._font_size()
        pad = max(12, int(size * 1.2))
        gap = max(6, int(size * 0.6))

        frame.configure(padx=pad, pady=pad)

        tk.Label(frame, text="CRF", font=self.font_text).grid(
            row=0,
            column=0,
            sticky="w",
        )

        crf_entry = tk.Entry(frame, width=6, font=self.font_text)
        crf_entry.insert(0, self.crf_value)
        crf_entry.grid(row=0, column=1, sticky="ew", padx=(gap, gap * 2))

        tk.Label(frame, text="Preset", font=self.font_text).grid(
            row=0,
            column=2,
            sticky="w",
        )

        preset_combo = ttk.Combobox(
            frame,
            values=PRESETS,
            width=12,
            font=self.font_text,
        )
        preset_combo.set(self.preset_value)
        preset_combo.grid(row=0, column=3, sticky="ew", padx=(gap, 0))

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

        tk.Button(
            frame,
            text="Aplicar",
            font=self.font_button,
            command=apply,
        ).grid(
            row=1,
            column=0,
            columnspan=4,
            sticky="ew",
            pady=(gap * 2, 0),
            ipady=gap,
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
                self.queue.put(
                    ("done", ("askopen", "Conversión completada. ¿Abrir carpeta de salida?"))
                )
            else:
                failed = sum(not result.success for result in results)
                self.queue.put(
                    (
                        "done",
                        (
                            "warning",
                            f"Conversión terminada con {failed} error(es). Revisá el log.",
                        ),
                    )
                )
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
        messagebox.showerror(
            "Error",
            f"No se encontró '{settings.ffmpeg_bin}' en PATH.",
        )
        return 1

    app = ConverterGUI(settings, logger)
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
