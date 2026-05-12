"""
Llama.cpp Model Launcher — GUI приложение для запуска llama-server
Создано на основе рекомендаций по оптимизации запуска MoE моделей
"""

import os
import socket
import sys
import subprocess
import shutil
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from datetime import datetime, timedelta
import json
import re


class LlamaLauncherApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Llama.cpp Model Launcher")
        self.root.geometry("800x800")
        self.root.minsize(700, 660)

        self.server_process = None
        self.log_lines = []
        self.is_running = False
        self._setup_styles()
        self._auto_detect_server()
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
        # === Main Content ===
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill='both', expand=True, padx=10, pady=5)

        # Configuration panel
        config_frame = ttk.Frame(main_frame, style='Card.TFrame')
        config_frame.pack(side='left', fill='both', expand=True, padx=(0, 8))

        self._create_model_section(config_frame)
        self._create_server_gen_section(config_frame)
        self._create_buttons_frame(config_frame)
        self._create_log_panel(config_frame)

    def _create_model_section(self, parent):
        frame = ttk.LabelFrame(parent, text="📦 Модель", padding=12, style='Card.TFrame')
        frame.pack(fill='x', pady=(0, 8))

      # Server path
        ttk.Label(frame, text="Путь к llama-server.exe:").grid(row=0, column=0, sticky='w', pady=4)

        server_frame = ttk.Frame(frame)
        server_frame.grid(row=0, column=1, sticky='ew', padx=(10, 0))

        self.server_path_var = tk.StringVar()
        self.server_path_entry = ttk.Entry(server_frame, textvariable=self.server_path_var)
        self.server_path_entry.pack(side='left', fill='x', expand=True, ipady=4)

        ttk.Button(server_frame, text="📂 Выбрать", command=self._select_server,
                   style='Info.TButton').pack(side='right', padx=(5, 0))

        # Model path
        ttk.Label(frame, text="Файл модели (.gguf):").grid(row=1, column=0, sticky='w', pady=4)

        model_frame = ttk.Frame(frame)
        model_frame.grid(row=1, column=1, sticky='ew', padx=(10, 0))

        self.model_var = tk.StringVar()
        self.model_entry = ttk.Entry(model_frame, textvariable=self.model_var)
        self.model_entry.pack(side='left', fill='x', expand=True, ipady=4)

        ttk.Button(model_frame, text="📂 Выбрать", command=self._select_model,
                   style='Info.TButton').pack(side='right', padx=(5, 0))

        # MMProj path
        ttk.Label(frame, text="Файл mmproj (визуализация):").grid(row=2, column=0, sticky='w', pady=4)

        mmproj_frame = ttk.Frame(frame)
        mmproj_frame.grid(row=2, column=1, sticky='ew', padx=(10, 0))

        self.mmproj_path_var = tk.StringVar()
        self.mmproj_path_entry = ttk.Entry(mmproj_frame, textvariable=self.mmproj_path_var)
        self.mmproj_path_entry.pack(side='left', fill='x', expand=True, ipady=4)

        ttk.Button(mmproj_frame, text="📂 Выбрать", command=self._select_mmproj,
                   style='Info.TButton').pack(side='right', padx=(5, 0))

        frame.columnconfigure(1, weight=1)

    def _create_server_gen_section(self, parent):
        frame = ttk.Frame(parent)
        frame.pack(fill='both', expand=True, pady=(0, 8))

        # Left column — Server
        left_col = ttk.LabelFrame(frame, text="⚙️ Сервер", padding=10, style='Card.TFrame')
        left_col.pack(side='left', fill='both', expand=True, padx=(0, 1))

        try:
            local_ip = [ip for ip in socket.gethostbyname_ex(socket.gethostname())[2] if not ip.startswith('127.')][0]
        except (IndexError, socket.gaierror):
            local_ip = "0.0.0.0"
        params = [
            ("Хост", "host", local_ip, 0),
            ("Порт", "port", "", 1),
            ("Контекст", "context_size", "120000", 2),
            ("GPU слои", "gpu_layers", "999", 3),
            ("Потоки CPU", "threads", str(os.cpu_count() or 4), 4),
            ("Batch size", "batch_size", "1024", 5),
        ]

        self.server_vars = {}
        for idx, (label, key, default, row) in enumerate(params):
            ttk.Label(left_col, text=label + ":").grid(row=row, column=0, sticky='w', pady=2)
            var = tk.StringVar(value=default)
            self.server_vars[key] = var
            width = 18
            entry = ttk.Entry(left_col, textvariable=var, width=width)
            entry.grid(row=row, column=1, sticky='w', padx=(6, 0))

        # Middle column — Generation
        mid_col = ttk.LabelFrame(frame, text="🎯 Генерация", padding=10, style='Card.TFrame')
        mid_col.pack(side='left', fill='both', expand=True, padx=(1, 1))

        gen_params = [
            ("Temperature", "temp", "0.6", 0),
            ("Top-k", "top_k", "20", 1),
            ("Top-p", "top_p", "0.95", 2),
            ("Parallel", "parallel", "2", 3),
        ]

        self.gen_vars = {}
        for label, key, default, row in gen_params:
            ttk.Label(mid_col, text=label + ":").grid(row=row, column=0, sticky='w', pady=2)
            var = tk.StringVar(value=default)
            self.gen_vars[key] = var
            entry = ttk.Entry(mid_col, textvariable=var, width=18)
            entry.grid(row=row, column=1, sticky='w', padx=(6, 0))

        ttk.Label(mid_col, text="KV-cache K:").grid(row=4, column=0, sticky='w', pady=2)
        self.cache_k_var = tk.StringVar(value="turbo3")
        cache_k_combo = ttk.Combobox(mid_col, textvariable=self.cache_k_var,
                                     values=["f16", "q8_0", "q4_0", "q4_1", "q5_0", "q5_1", "turbo3", "turbo4"],
                                     state='readonly', width=15)
        cache_k_combo.grid(row=4, column=1, sticky='w', padx=(6, 0))

        ttk.Label(mid_col, text="KV-cache V:").grid(row=5, column=0, sticky='w', pady=2)
        self.cache_v_var = tk.StringVar(value="turbo3")
        cache_v_combo = ttk.Combobox(mid_col, textvariable=self.cache_v_var,
                                     values=["f16", "q8_0", "q4_0", "q4_1", "q5_0", "q5_1", "turbo3", "turbo4"],
                                     state='readonly', width=15)
        cache_v_combo.grid(row=5, column=1, sticky='w', padx=(6, 0))

        ttk.Label(mid_col, text="CPU MoE:").grid(row=7, column=0, sticky='w', pady=2)
        self.moe_var = tk.StringVar(value="0")
        ttk.Entry(mid_col, textvariable=self.moe_var, width=18).grid(row=7, column=1, sticky='w', padx=(6, 0))

        ttk.Label(mid_col, text="Reasoning:").grid(row=8, column=0, sticky='w', pady=2)
        self.reasoning_var = tk.StringVar(value="0")
        ttk.Entry(mid_col, textvariable=self.reasoning_var, width=18).grid(row=8, column=1, sticky='w', padx=(6, 0))

        # Right column — Advanced (moved from separate section)
        right_col = ttk.LabelFrame(frame, text="🔧 Дополнительно", padding=10, style='Card.TFrame')
        right_col.pack(side='left', fill='both', expand=True, padx=(1, 0))

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
            ttk.Checkbutton(right_col, text=labels[key], variable=var).grid(row=r, column=c, sticky='w', padx=(0, 10), pady=2)

        row = 3
        ttk.Label(right_col, text="Доп. аргументы:").grid(row=row, column=0, columnspan=2, sticky='w', pady=(8, 5))
        self.extra_args_var = tk.StringVar(value="")
        ttk.Entry(right_col, textvariable=self.extra_args_var, width=18).grid(row=row + 1, column=0, columnspan=2, sticky='ew', pady=(0, 5))
        right_col.columnconfigure(0, weight=1)

    def _create_buttons_frame(self, parent):
        frame = ttk.Frame(parent)
        frame.pack(fill='x', pady=(5, 0))

        self.start_btn = ttk.Button(frame, text="▶ Запустить", style='Success.TButton',
                                     command=self._start_server)
        self.start_btn.pack(side='left', padx=5, expand=True, fill='x')

        ttk.Button(frame, text="⏹ Остановить", style='Danger.TButton',
                    command=self._stop_server).pack(side='left', padx=5, expand=True, fill='x')

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

    # === Helper Methods ===

    def _auto_detect_server(self):
        paths_to_check = []
        script_dir = os.path.dirname(os.path.abspath(__file__))
        paths_to_check.append(os.path.join(script_dir, "llama-server.exe"))
        paths_to_check.append(os.path.join(script_dir, "server.exe"))
        common_paths = [
            r"C:\Program Files\llama.cpp\llama-server.exe",
            r"C:\Program Files\llama.cpp\server.exe",
            r"D:\Program Files\llama.cpp\llama-server.exe",
            r"D:\Program Files\llama.cpp\server.exe",
        ]
        paths_to_check.extend(common_paths)
        try:
            path_from_env = shutil.which("llama-server") or shutil.which("server")
            if path_from_env:
                paths_to_check.append(path_from_env)
        except Exception:
            pass
        for p in paths_to_check:
            if os.path.isfile(p):
                self.server_path_var = tk.StringVar(value=p)
                return
        self.server_path_var = tk.StringVar()

    def _validate_numeric(self, field_name, value, min_val=None, max_val=None, allow_float=False):
        try:
            if allow_float:
                num = float(value)
            else:
                num = int(value)
        except (ValueError, TypeError):
            return False, f"{field_name} должно быть числом"
        if min_val is not None and num < min_val:
            return False, f"{field_name} должно быть >= {min_val}"
        if max_val is not None and num > max_val:
            return False, f"{field_name} должно быть <= {max_val}"
        return True, ""

    def _validate_all(self):
        errors = []
        server_fields = {
            "port": ("Порт", 1, 65535),
            "context_size": ("Контекст", 1, 1000000),
            "gpu_layers": ("GPU слои", 0, 1000),
            "threads": ("Потоки CPU", 1, 1024),
            "batch_size": ("Batch size", 1, 4096),
        }
        for key, (label, min_v, max_v) in server_fields.items():
            val = self.server_vars.get(key, tk.StringVar()).get()
            ok, err = self._validate_numeric(label, val, min_v, max_v)
            if not ok:
                errors.append(err)
        gen_fields = {
            "temp": ("Temperature", 0.01, 2.0, True),
            "top_k": ("Top-k", 1, 500, False),
            "top_p": ("Top-p", 0.0, 1.0, True),
            "parallel": ("Parallel", 1, 32, False),
        }
        for key, (label, min_v, max_v, allow_float) in gen_fields.items():
            val = self.gen_vars.get(key, tk.StringVar()).get()
            ok, err = self._validate_numeric(label, val, min_v, max_v, allow_float)
            if not ok:
                errors.append(err)
        reasoning_val = self.reasoning_var.get().strip()
        if reasoning_val:
            ok, err = self._validate_numeric("Reasoning", reasoning_val, 0, 100000)
            if not ok:
                errors.append(err)
        moe_val = self.moe_var.get().strip()
        if moe_val:
            ok, err = self._validate_numeric("MoE экспертов", moe_val, 0, 1000)
            if not ok:
                errors.append(err)
        return errors

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

    def _select_mmproj(self):
        path = filedialog.askopenfilename(
            title="Выберите mmproj файл",
            filetypes=[("MMProj файлы", "*.mmproj"), ("Все файлы", "*.*")]
        )
        if path:
            self.mmproj_path_var.set(path)

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

        # MMProj
        mmproj_path = self.mmproj_path_var.get().strip()
        if mmproj_path and os.path.exists(mmproj_path):
            cmd.extend(["--mmproj", mmproj_path])

        # Cache types
        cmd.extend(["--cache-type-k", self.cache_k_var.get(), "--cache-type-v", self.cache_v_var.get()])

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

        errors = self._validate_all()
        if errors:
            messagebox.showerror("Ошибка валидации", "\n".join(errors))
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
            "mmproj_path": self.mmproj_path_var.get(),
            "server": {k: v.get() for k, v in self.server_vars.items()},
            "generation": {k: v.get() for k, v in self.gen_vars.items()},
            "cache_k": self.cache_k_var.get(),
            "cache_v": self.cache_v_var.get(),
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
            if config.get("mmproj_path"):
                self.mmproj_path_var.set(config["mmproj_path"])

            for k, v in config.get("server", {}).items():
                if k in self.server_vars:
                    self.server_vars[k].set(v)
            for k, v in config.get("generation", {}).items():
                if k in self.gen_vars:
                    self.gen_vars[k].set(v)

            if config.get("cache_k"):
                self.cache_k_var.set(config["cache_k"])
            if config.get("cache_v"):
                self.cache_v_var.set(config["cache_v"])
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
    root = tk.Tk()
    app = LlamaLauncherApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
