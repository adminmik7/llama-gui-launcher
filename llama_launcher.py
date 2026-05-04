"""
Llama.cpp Model Launcher — GUI приложение для запуска llama-server
Создано на основе рекомендаций по оптимизации запуска MoE моделей
"""

import os
import sys
import subprocess
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from datetime import datetime
import json
import re


class LlamaLauncherApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Llama.cpp Model Launcher")
        self.root.geometry("1100x850")
        self.root.minsize(900, 700)

        self.server_process = None
        self.log_lines = []
        self.is_running = False

        self._setup_styles()
        self._create_ui()

    def _setup_styles(self):
        style = ttk.Style()
        try:
            style.theme_use('vista')
        except tk.TclError:
            style.theme_use('clam')

        self.root.configure(bg='#f0f0f0')

        style.configure('Title.TLabel',
                        foreground='#1a73e8',
                        font=('Segoe UI', 18, 'bold'))

        style.configure('Section.TLabel',
                        font=('Segoe UI', 11, 'bold'))

        style.configure('Card.TFrame', background='#f0f0f0')
        style.configure('Card.TLabel', background='#f0f0f0')

        style.configure('Primary.TButton', font=('Segoe UI', 10, 'bold'))
        style.configure('Danger.TButton', font=('Segoe UI', 10, 'bold'))
        style.configure('Success.TButton', font=('Segoe UI', 10, 'bold'))
        style.configure('Info.TButton', font=('Segoe UI', 10))

        style.configure('TEntry', font=('Segoe UI', 10))
        style.configure('TCombobox', font=('Segoe UI', 10))
        style.configure('TLabel', font=('Segoe UI', 10))
        style.configure('TCheckbutton', font=('Segoe UI', 10))
        style.configure('TRadiobutton', font=('Segoe UI', 10))

        style.configure('Treeview', font=('Segoe UI', 9))
        style.configure('Treeview.Heading', font=('Segoe UI', 9, 'bold'))

    def _create_ui(self):
        # === Header ===
        header = ttk.Frame(self.root, style='Card.TFrame')
        header.pack(fill='x', padx=20, pady=(15, 10))

        ttk.Label(header, text="🦙 Llama.cpp Model Launcher",
                  style='Title.TLabel').pack(side='left')

        # === Main Content ===
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill='both', expand=True, padx=20, pady=5)

        # Configuration panel
        config_frame = ttk.Frame(main_frame, style='Card.TFrame')
        config_frame.pack(side='left', fill='both', expand=True, padx=(0, 8))

        self._create_model_section(config_frame)
        self._create_server_gen_section(config_frame)
        self._create_advanced_section(config_frame)
        self._create_buttons_frame(config_frame)
        self._create_log_panel(config_frame)

    def _create_model_section(self, parent):
        frame = ttk.LabelFrame(parent, text="📦 Модель", padding=12, style='Card.TFrame')
        frame.pack(fill='x', pady=(0, 8))

        # Model path
        ttk.Label(frame, text="Файл модели (.gguf):").grid(row=0, column=0, sticky='w', pady=4)

        model_frame = ttk.Frame(frame)
        model_frame.grid(row=0, column=1, sticky='ew', padx=(10, 0))

        self.model_var = tk.StringVar()
        self.model_entry = ttk.Entry(model_frame, textvariable=self.model_var, state='readonly')
        self.model_entry.pack(side='left', fill='x', expand=True, ipady=4)

        ttk.Button(model_frame, text="📂 Выбрать", command=self._select_model,
                   style='Info.TButton').pack(side='right', padx=(5, 0))

        ttk.Label(frame, text="Путь к llama-server.exe:").grid(row=1, column=0, sticky='w', pady=4)

        server_frame = ttk.Frame(frame)
        server_frame.grid(row=1, column=1, sticky='ew', padx=(10, 0))

        self.server_path_var = tk.StringVar(value=os.path.join(os.path.dirname(os.path.abspath(__file__)), "llama-server.exe"))
        self.server_path_entry = ttk.Entry(server_frame, textvariable=self.server_path_var)
        self.server_path_entry.pack(side='left', fill='x', expand=True, ipady=4)

        ttk.Button(server_frame, text="📂", command=self._select_server,
                   style='Info.TButton').pack(side='right', padx=(5, 0))

        frame.columnconfigure(1, weight=1)

    def _create_server_gen_section(self, parent):
        frame = ttk.Frame(parent)
        frame.pack(fill='both', expand=True, pady=(0, 8))

        # Left column — Server
        left_col = ttk.LabelFrame(frame, text="⚙️ Сервер", padding=10, style='Card.TFrame')
        left_col.pack(side='left', fill='both', expand=True, padx=(0, 2))

        params = [
            ("Хост", "host", "192.168.3.151", 0),
            ("Порт", "port", "1515", 1),
            ("Контекст", "context_size", "65536", 2),
            ("GPU слои", "gpu_layers", "999", 3),
            ("Потоки CPU", "threads", "16", 4),
            ("Batch size", "batch_size", "256", 5),
        ]

        self.server_vars = {}
        for label, key, default, row in params:
            ttk.Label(left_col, text=label + ":").grid(row=row, column=0, sticky='w', pady=2)
            var = tk.StringVar(value=default)
            self.server_vars[key] = var
            entry = ttk.Entry(left_col, textvariable=var, width=14)
            entry.grid(row=row, column=1, sticky='w', padx=(6, 0))

        preset_frame = ttk.Frame(left_col)
        preset_frame.grid(row=6, column=0, columnspan=2, pady=(6, 0))

        ttk.Label(preset_frame, text="Пресеты:").pack(side='left', padx=(0, 4))

        self.preset_var = tk.StringVar(value="8GB")

        self.preset_combo = ttk.Combobox(
            preset_frame,
            textvariable=self.preset_var,
            values=["8GB", "16GB", "24GB", "48GB"],
            state='readonly',
            width=10,
        )
        self.preset_combo.pack(side='left')
        self.preset_combo.bind("<<ComboboxSelected>>", self._on_preset_select)

        # Right column — Generation
        right_col = ttk.LabelFrame(frame, text="🎯 Генерация", padding=10, style='Card.TFrame')
        right_col.pack(side='left', fill='both', expand=True, padx=(2, 0))

        gen_params = [
            ("Temperature", "temp", "0.6", 0),
            ("Top-k", "top_k", "20", 1),
            ("Top-p", "top_p", "0.95", 2),
            ("Parallel", "parallel", "2", 3),
        ]

        self.gen_vars = {}
        for label, key, default, row in gen_params:
            ttk.Label(right_col, text=label + ":").grid(row=row, column=0, sticky='w', pady=2)
            var = tk.StringVar(value=default)
            self.gen_vars[key] = var
            entry = ttk.Entry(right_col, textvariable=var, width=14)
            entry.grid(row=row, column=1, sticky='w', padx=(6, 0))

        ttk.Label(right_col, text="KV-cache:").grid(row=4, column=0, sticky='w', pady=2)
        self.cache_var = tk.StringVar(value="q8_0")
        cache_combo = ttk.Combobox(right_col, textvariable=self.cache_var,
                                   values=["f16", "q8_0", "q4_0", "q4_1", "q5_0", "q5_1", "turbo3"],
                                   state='readonly', width=12)
        cache_combo.grid(row=4, column=1, sticky='w', padx=(6, 0))

        ttk.Label(right_col, text="MoE экспертов:").grid(row=5, column=0, sticky='w', pady=2)
        self.moe_var = tk.StringVar(value="")
        ttk.Entry(right_col, textvariable=self.moe_var, width=14).grid(row=5, column=1, sticky='w', padx=(6, 0))

        ttk.Label(right_col, text="Reasoning:").grid(row=6, column=0, sticky='w', pady=2)
        self.reasoning_var = tk.StringVar(value="2048")
        ttk.Entry(right_col, textvariable=self.reasoning_var, width=14).grid(row=6, column=1, sticky='w', padx=(6, 0))

    def _create_advanced_section(self, parent):
        frame = ttk.LabelFrame(parent, text="🔧 Дополнительно", padding=12, style='Card.TFrame')
        frame.pack(fill='x', pady=(0, 8))

        self.flash_attn_var = tk.BooleanVar(value=True)
        self.cont_batching_var = tk.BooleanVar(value=True)
        self.jinja_var = tk.BooleanVar(value=True)
        self.no_mmap_var = tk.BooleanVar(value=True)
        self.kv_unified_var = tk.BooleanVar(value=True)
        self.preserve_thinking_var = tk.BooleanVar(value=True)

        self.adv_vars = {
            "flash_attn": self.flash_attn_var,
            "cont_batching": self.cont_batching_var,
            "jinja": self.jinja_var,
            "no_mmap": self.no_mmap_var,
            "kv_unified": self.kv_unified_var,
            "preserve_thinking": self.preserve_thinking_var,
        }

        labels = {
            "flash_attn": "Flash Attention",
            "cont_batching": "Continual Batching",
            "jinja": "Jinja шаблон",
            "no_mmap": "No MMAP (Windows)",
            "kv_unified": "KV Unified",
            "preserve_thinking": "Preserve Thinking",
        }

        for idx, (key, var) in enumerate(self.adv_vars.items()):
            r = idx // 2
            c = idx % 2
            ttk.Checkbutton(frame, text=labels[key], variable=var).grid(row=r, column=c, sticky='w', padx=(0, 10), pady=2)
        row = 3

        # Custom extra args
        ttk.Label(frame, text="Доп. аргументы:").grid(row=row, column=0, sticky='w', pady=(8, 5))
        self.extra_args_var = tk.StringVar(value="")
        ttk.Entry(frame, textvariable=self.extra_args_var, width=40, state='normal').grid(row=row, column=1, sticky='ew', pady=(8, 5), padx=(10, 0))
        frame.columnconfigure(1, weight=1)

    def _create_buttons_frame(self, parent):
        frame = ttk.Frame(parent)
        frame.pack(fill='x', pady=(5, 0))

        self.start_btn = ttk.Button(frame, text="▶ Запустить", style='Success.TButton',
                                     command=self._start_server)
        self.start_btn.pack(side='left', padx=5, expand=True, fill='x')

        ttk.Button(frame, text="⏹ Остановить", style='Danger.TButton',
                    command=self._stop_server).pack(side='left', padx=5, expand=True, fill='x')

        ttk.Button(frame, text="📋 Копировать команду", style='Info.TButton',
                    command=self._copy_command).pack(side='left', padx=5, expand=True, fill='x')

        ttk.Button(frame, text="💾 Сохранить конфиг", style='Info.TButton',
                    command=self._save_config).pack(side='left', padx=5, expand=True, fill='x')

        ttk.Button(frame, text="📂 Загрузить конфиг", style='Info.TButton',
                    command=self._load_config).pack(side='left', padx=5, expand=True, fill='x')

    def _create_log_panel(self, parent):
        frame = ttk.LabelFrame(parent, text="📝 Лог сервера", padding=10, style='Card.TFrame')
        frame.pack(fill='both', expand=True)

        log_frame = ttk.Frame(frame)
        log_frame.pack(fill='both', expand=True)

        self.log_text = tk.Text(log_frame, font=('Consolas', 9), state='disabled',
                                   borderwidth=0, wrap='word',
                                   bg='#000000', fg='#ffffff')
        scrollbar = ttk.Scrollbar(log_frame, orient='vertical', command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)

        self.log_text.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')

        self.log_text.bind('<Control-c>', self._copy_selected)
        self.log_text.bind('<Control-C>', self._copy_selected)
        self.log_text.bind('<Button-3>', self._log_context_menu)

        ttk.Button(frame, text="🗑 Очистить лог", command=self._clear_log,
                    style='Info.TButton').pack(anchor='e', pady=(5, 0))

    # === Actions ===

    def _select_model(self):
        path = filedialog.askopenfilename(
            title="Выберите GGUF модель",
            filetypes=[("GGUF модели", "*.gguf"), ("Все файлы", "*.*")]
        )
        if path:
            self.model_var.set(path)

    def _select_server(self):
        path = filedialog.askopenfilename(
            title="Выберите llama-server.exe",
            filetypes=[("Executable", "*.exe"), ("Все файлы", "*.*")]
        )
        if path:
            self.server_path_var.set(path)

    _PRESETS = {
        "8GB": {"gpu_layers": "30", "context_size": "8192", "batch_size": "512"},
        "16GB": {"gpu_layers": "80", "context_size": "32768", "batch_size": "512"},
        "24GB": {"gpu_layers": "999", "context_size": "65536", "batch_size": "256"},
        "48GB": {"gpu_layers": "999", "context_size": "128000", "batch_size": "256"},
    }

    def _on_preset_select(self, event=None):
        name = self.preset_var.get()
        values = self._PRESETS.get(name, {})
        self._apply_preset(values)

    def _apply_preset(self, values):
        for key, value in values.items():
            if key in self.server_vars:
                self.server_vars[key].set(value)

    def _build_command(self):
        server_path = self.server_path_var.get()
        model_path = self.model_var.get()

        if not server_path or not os.path.exists(server_path):
            messagebox.showerror("Ошибка", "Укажите путь к llama-server.exe")
            return None

        if not model_path or not os.path.exists(model_path):
            messagebox.showerror("Ошибка", "Укажите путь к GGUF модели")
            return None

        cmd = [
            server_path,
            "-m", model_path,
            "--host", self.server_vars["host"].get(),
            "--port", self.server_vars["port"].get(),
            "--gpu-layers", self.server_vars["gpu_layers"].get(),
            "-c", self.server_vars["context_size"].get(),
            "--temp", self.gen_vars["temp"].get(),
            "--top-k", self.gen_vars["top_k"].get(),
            "--top-p", self.gen_vars["top_p"].get(),
            "-t", self.server_vars["threads"].get(),
            "-b", self.server_vars["batch_size"].get(),
            "--parallel", self.gen_vars["parallel"].get(),
        ]

        # Cache types
        cache = self.cache_var.get()
        cmd.extend(["--cache-type-k", cache, "--cache-type-v", cache])

        # Advanced flags
        if self.flash_attn_var.get():
            cmd.extend(["--flash-attn", "on"])
        if self.cont_batching_var.get():
            cmd.append("--cont-batching")
        if self.jinja_var.get():
            cmd.append("--jinja")
        if self.no_mmap_var.get():
            cmd.append("--no-mmap")
        if self.kv_unified_var.get():
            cmd.append("--kv-unified")

        # MoE
        if self.moe_var.get().strip():
            cmd.extend(["--n-cpu-moe", self.moe_var.get().strip()])

        # Reasoning
        reasoning = self.reasoning_var.get().strip()
        if reasoning:
            cmd.extend(["--reasoning-budget", reasoning])

        # Chat template kwargs
        if self.preserve_thinking_var.get():
            cmd.extend(["--chat-template-kwargs", '{"preserve_thinking":true}'])

        # Extra args
        if self.extra_args_var.get().strip():
            cmd.extend(self.extra_args_var.get().strip().split())

        return cmd

    def _start_server(self):
        if self.is_running:
            messagebox.showwarning("Внимание", "Сервер уже запущен!")
            return

        cmd = self._build_command()
        if cmd is None:
            return

        self.is_running = True
        self.start_btn.configure(text="⏳ Запуск...", state='disabled')
        self._log("Команда: " + " ".join(cmd))
        self._log("Запуск сервера...")

        try:
            self.server_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                encoding='utf-8',
                errors='replace',
                creationflags=subprocess.CREATE_NO_WINDOW
            )

            # Monitor thread
            monitor_thread = threading.Thread(target=self._monitor_process, daemon=True)
            monitor_thread.start()

        except Exception as e:
            self._log(f"Ошибка запуска: {e}")
            self.is_running = False
            self.start_btn.configure(text="▶ Запустить", state='normal')

    def _monitor_process(self):
        if self.server_process is None:
            return

        try:
            while True:
                line = self.server_process.stdout.readline()
                if not line:
                    break
                self.root.after(0, self._log, line.rstrip())
        except Exception:
            pass
        self.root.after(0, self._log, f"[Завершено] Код выхода: {self.server_process.returncode}")
        self.root.after(0, self._on_server_stopped)

    def _on_server_stopped(self):
        self.is_running = False
        self.start_btn.configure(text="▶ Запустить", state='normal')

    def _stop_server(self):
        if self.server_process and self.server_process.poll() is None:
            self._log("Остановка сервера...")
            self.server_process.terminate()
            try:
                self.server_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.server_process.kill()
            self._log("Сервер остановлен.")
            self._on_server_stopped()
        else:
            self._log("Сервер не запущен.")
            self._on_server_stopped()

    def _copy_command(self):
        cmd = self._build_command()
        if cmd:
            self.root.clipboard_clear()
            self.root.clipboard_append(" ".join(cmd))
            messagebox.showinfo("Инфо", "Команда скопирована в буфер обмена!")

    def _copy_selected(self, event=None):
        try:
            selected = self.log_text.get("sel.first", "sel.last")
            if selected.strip():
                self.root.clipboard_clear()
                self.root.clipboard_append(selected)
        except tk.TclError:
            pass
        if event is not None:
            return "break"

    def _log_context_menu(self, event):
        try:
            self.log_text.edit_modified(False)
        except tk.TclError:
            pass
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label="Копировать", command=self._copy_selected)
        try:
            selection = self.log_text.get("sel.first", "sel.last")
            if selection.strip():
                menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def _clear_log(self):
        self.log_text.configure(state='normal')
        self.log_text.delete("1.0", tk.END)
        self.log_text.configure(state='disabled')

    def _log(self, message):
        self.log_text.configure(state='normal')
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
        self.log_text.configure(state='disabled')

    def _save_config(self):
        path = filedialog.asksaveasfilename(
            title="Сохранить конфиг",
            defaultextension=".json",
            filetypes=[("JSON", "*.json")]
        )
        if not path:
            return

        config = {
            "model": self.model_var.get(),
            "server_path": self.server_path_var.get(),
            "server": {k: v.get() for k, v in self.server_vars.items()},
            "generation": {k: v.get() for k, v in self.gen_vars.items()},
            "cache": self.cache_var.get(),
            "moe": self.moe_var.get(),
            "reasoning": self.reasoning_var.get(),
            "advanced": {k: v.get() for k, v in self.adv_vars.items()},
            "extra_args": self.extra_args_var.get(),
        }

        with open(path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        messagebox.showinfo("Инфо", f"Конфиг сохранён: {path}")

    def _load_config(self):
        path = filedialog.askopenfilename(
            title="Загрузить конфиг",
            filetypes=[("JSON", "*.json"), ("Все файлы", "*.*")]
        )
        if not path:
            return

        try:
            with open(path, 'r', encoding='utf-8') as f:
                config = json.load(f)

            if config.get("model"):
                self.model_var.set(config["model"])
            if config.get("server_path"):
                self.server_path_var.set(config["server_path"])

            for k, v in config.get("server", {}).items():
                if k in self.server_vars:
                    self.server_vars[k].set(v)
            for k, v in config.get("generation", {}).items():
                if k in self.gen_vars:
                    self.gen_vars[k].set(v)

            if config.get("cache"):
                self.cache_var.set(config["cache"])
            if config.get("moe"):
                self.moe_var.set(config["moe"])
            if config.get("reasoning"):
                self.reasoning_var.set(config["reasoning"])
            if "extra_args" in config:
                self.extra_args_var.set(config["extra_args"])

            for k, v in config.get("advanced", {}).items():
                if k in self.adv_vars:
                    self.adv_vars[k].set(v)

            messagebox.showinfo("Инфо", f"Конфиг загружен: {path}")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка загрузки конфига: {e}")


def main():
    import ctypes
    if ctypes.windll.kernel32.GetConsoleWindow():
        ctypes.windll.kernel32.FreeConsole()
        pythonw = sys.executable
        args = [pythonw] + sys.argv
        os.execv(pythonw, args)
    root = tk.Tk()
    app = LlamaLauncherApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
