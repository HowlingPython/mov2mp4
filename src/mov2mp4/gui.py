import queue
import shutil
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from .config import PRESETS, load_settings
from .converter import convert_batch
from .logging_config import configure_logging
from .opener import open_folder


class ConverterGUI(tk.Tk):
    def __init__(self, settings, logger):
        super().__init__()

        self.settings = settings
        self.logger = logger
        self.queue = queue.Queue()
        self.cancel_event = threading.Event()
        self.out_dir = None
        self.crf_value = str(settings.default_crf)
        self.preset_value = settings.default_preset

        self.title("MOV → MP4 Converter")
        self.minsize(420, 220)
        self.geometry("520x260")
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        main = ttk.Frame(self, padding=16)
        main.grid(row=0, column=0, sticky="nsew")

        main.columnconfigure(0, weight=1)
        main.rowconfigure(4, weight=1)

        self.status_var = tk.StringVar(value="Listo.")

        self.btn_quality = ttk.Button(
            main,
            text="Ajustes de calidad",
            command=self.show_quality_settings,
        )
        self.btn_quality.grid(row=0, column=0, sticky="ew", pady=(0, 8))

        self.btn_convert = ttk.Button(
            main,
            text="Seleccionar y convertir",
            command=self.start,
        )
        self.btn_convert.grid(row=1, column=0, sticky="ew", pady=(0, 8))

        self.btn_cancel = ttk.Button(
            main,
            text="Cancelar",
            state="disabled",
            command=self.cancel,
        )
        self.btn_cancel.grid(row=2, column=0, sticky="ew", pady=(0, 16))

        self.progress = ttk.Progressbar(
            main,
            orient="horizontal",
            mode="determinate",
        )
        self.progress.grid(row=3, column=0, sticky="ew", pady=(0, 8))

        self.status_label = ttk.Label(
            main,
            textvariable=self.status_var,
            anchor="center",
            justify="center",
            wraplength=480,
        )
        self.status_label.grid(row=4, column=0, sticky="nsew")

        self.bind(
            "<Configure>",
            lambda event: self.status_label.config(
                wraplength=max(200, event.width - 40)
            ),
        )

    def show_quality_settings(self):
        top = tk.Toplevel(self)
        top.title("Ajustes de calidad")
        top.minsize(320, 120)
        top.resizable(True, False)
        
        top.columnconfigure(0, weight=1)
        
        frame = ttk.Frame(top, padding=12)
        frame.grid(row=0, column=0, sticky="ew")

        frame = tk.Frame(top)
        frame.pack(pady=10)

        tk.Label(frame, text="CRF").grid(row=0, column=0)
        crf_entry = tk.Entry(frame, width=5)
        crf_entry.insert(0, self.crf_value)
        crf_entry.grid(row=0, column=1, padx=(0, 10))
        crf_entry.bind(
            "<Enter>",
            lambda _: self.status_var.set(
                "CRF: calidad del video (0-51, menor es mejor)"
            ),
        )
        crf_entry.bind("<Leave>", lambda _: self.status_var.set("Listo."))

        tk.Label(frame, text="Preset").grid(row=0, column=2)
        preset_combo = ttk.Combobox(frame, values=PRESETS, width=10)
        preset_combo.set(self.preset_value)
        preset_combo.grid(row=0, column=3)
        preset_combo.bind(
            "<Enter>", lambda _: self.status_var.set("Preset: velocidad vs compresión")
        )
        preset_combo.bind("<Leave>", lambda _: self.status_var.set("Listo."))

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

        ttk.Button(top, text="Aplicar", command=apply).grid(row=1, column=0, pady=(0, 12))

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
            target=self._run_conversion, args=(files, out_dir), daemon=True
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
                    (
                        "done",
                        ("askopen", "Conversión completada. ¿Abrir carpeta de salida?"),
                    )
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
            "Error", f"No se encontró '{settings.ffmpeg_bin}' en PATH."
        )
        return 1

    app = ConverterGUI(settings, logger)
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
