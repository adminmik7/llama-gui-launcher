import os
import sys
import socket
import subprocess
import shlex
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from datetime import datetime
import json
import time
_LAST_CONFIG_META = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".config")
def _get_last_config_path():
    try:
        with open(_LAST_CONFIG_META, 'r', encoding='utf-8') as f:
            path = f.read().strip()
        if path and os.path.exists(path):
            return path
    except Exception:
        pass
    return None
def _save_last_config_path(path):
    try:
        with open(_LAST_CONFIG_META, 'w', encoding='utf-8') as f:
            f.write(path)
    except Exception:
        pass
class LlamaLauncherApp:
    def __init__(self, root):
        self.root = root
        self.root.title("llama GUI")
        self.root.geometry("820x800")
        self.root.minsize(700, 660)
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
        self.server_process = None
        self.is_running = False
        self._dirty = False
        self._animation_thread = None
        self._animation_running = False
        self._poll_timeout_callback_id = None
        self._log_line_count = 0
        self._log_file = None
        self._setup_styles()
        self._create_ui()
        self._auto_load_config()
        self._register_dirty_traces()
        self._center_window()
    def _setup_styles(self):
        style = ttk.Style()
        try:
            style.theme_use('vista')
        except tk.TclError:
            style.theme_use('clam')
        self.root.configure(bg='#f0f0f0')
        style.configure('Card.TFrame', background='#f0f0f0')
        style.configure('Danger.TButton', font=('Segoe UI', 10, 'bold'))
        style.configure('Success.TButton', font=('Segoe UI', 10, 'bold'))
        style.configure('Info.TButton', font=('Segoe UI', 10))
        style.configure('TEntry', font=('Segoe UI', 10))
        style.configure('TCombobox', font=('Segoe UI', 10))
        style.configure('TLabel', font=('Segoe UI', 10))
        style.configure('TCheckbutton', font=('Segoe UI', 10))
        style.configure('TRadiobutton', font=('Segoe UI', 10))
    def _center_window(self):
        self.root.update_idletasks()
        w = self.root.winfo_width()
        h = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() - w) // 2
        y = (self.root.winfo_screenheight() - h) // 2
        self.root.geometry(f'+{x}+{y}')
    def _create_ui(self):
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill='both', expand=True, padx=10, pady=5)
        config_frame = ttk.Frame(main_frame, style='Card.TFrame')
        config_frame.pack(side='left', fill='both', expand=True, padx=(0, 8))
        self._create_model_section(config_frame)
        self._create_server_gen_section(config_frame)
        self._create_buttons_frame(config_frame)
        self._create_log_panel(config_frame)
    def _create_model_section(self, parent):
        frame = ttk.Frame(parent, padding=12, style='Card.TFrame')
        frame.pack(fill='x', pady=(0, 8))
        ttk.Label(frame, text="Путь к llama-server.exe:").grid(row=0, column=0, sticky='w', pady=4)
        server_frame = ttk.Frame(frame)
        server_frame.grid(row=0, column=1, sticky='ew', padx=(10, 0))
        self.server_path_var = tk.StringVar()
        self.server_path_entry = ttk.Entry(server_frame, textvariable=self.server_path_var)
        self.server_path_entry.pack(side='left', fill='x', expand=True, ipady=4)
        ttk.Button(server_frame, text="📂 Выбрать", command=self._select_server,
                   style='Info.TButton').pack(side='right', padx=(5, 0))
        ttk.Label(frame, text="Файл модели (.gguf):").grid(row=1, column=0, sticky='w', pady=4)
        model_frame = ttk.Frame(frame)
        model_frame.grid(row=1, column=1, sticky='ew', padx=(10, 0))
        self.model_var = tk.StringVar()
        self.model_entry = ttk.Entry(model_frame, textvariable=self.model_var)
        self.model_entry.pack(side='left', fill='x', expand=True, ipady=4)
        ttk.Button(model_frame, text="📂 Выбрать", command=self._select_model,
                   style='Info.TButton').pack(side='right', padx=(5, 0))
        ttk.Label(frame, text="Файл mmproj (визуализация):").grid(row=2, column=0, sticky='w', pady=4)
        mmproj_frame = ttk.Frame(frame)
        mmproj_frame.grid(row=2, column=1, sticky='ew', padx=(10, 0))
        self.mmproj_path_var = tk.StringVar()
        self.mmproj_path_entry = ttk.Entry(mmproj_frame, textvariable=self.mmproj_path_var)
        self.mmproj_path_entry.pack(side='left', fill='x', expand=True, ipady=4)
        ttk.Button(mmproj_frame, text="📂 Выбрать", command=self._select_mmproj,
                   style='Info.TButton').pack(side='right', padx=(5, 0))
        ttk.Label(frame, text="Файл chat template:").grid(row=3, column=0, sticky='w', pady=4)
        chat_template_frame = ttk.Frame(frame)
        chat_template_frame.grid(row=3, column=1, sticky='ew', padx=(10, 0))
        self.chat_template_path_var = tk.StringVar()
        self.chat_template_path_entry = ttk.Entry(chat_template_frame, textvariable=self.chat_template_path_var)
        self.chat_template_path_entry.pack(side='left', fill='x', expand=True, ipady=4)
        ttk.Button(chat_template_frame, text="📂 Выбрать", command=self._select_chat_template,
                   style='Info.TButton').pack(side='right', padx=(5, 0))
        frame.columnconfigure(1, weight=1)
    def _create_server_gen_section(self, parent):
        frame = ttk.Frame(parent)
        frame.pack(fill='both', expand=True, pady=(0, 8))
        left_col = ttk.LabelFrame(frame, text="⚙️ Сервер", padding=10, style='Card.TFrame')
        left_col.pack(side='left', fill='both', expand=True, padx=(0, 1))
        try:
            local_ip = [ip for ip in socket.gethostbyname_ex(socket.gethostname())[2] if not ip.startswith('127.')][0]
        except (IndexError, socket.gaierror):
            local_ip = "0.0.0.0"
        params = [
            ("Хост", "host", local_ip, 0),
            ("Порт", "port", "1414", 1),
            ("Контекст", "context_size", "120000", 2),
            ("GPU слои", "gpu_layers", "999", 3),
            ("Потоки CPU", "threads", str(os.cpu_count() or 4), 4),
            ("Batch size", "batch_size", "512", 5),
            ("UBatch size", "ubatch_size", "512", 6),
        ]
        self.server_vars = {}
        self.server_enabled = {}
        for idx, (label, key, default, row) in enumerate(params):
            ttk.Label(left_col, text=label + ":").grid(row=row, column=0, sticky='w', pady=2)
            var = tk.StringVar(value=default)
            self.server_vars[key] = var
            width = 14
            entry = ttk.Entry(left_col, textvariable=var, width=width)
            entry.grid(row=row, column=1, sticky='w', padx=(6, 0))
            if key not in ("host", "port"):
                enabled = tk.BooleanVar(value=True)
                self.server_enabled[key] = enabled
                ttk.Checkbutton(left_col, variable=enabled).grid(row=row, column=2, sticky='e', padx=(4, 0))
        mid_col = ttk.LabelFrame(frame, text="🎯 Генерация", padding=10, style='Card.TFrame')
        mid_col.pack(side='left', fill='both', expand=True, padx=(1, 1))
        gen_params = [
            ("Temperature", "temp", "0.6", 0),
            ("Top-k", "top_k", "20", 1),
            ("Top-p", "top_p", "0.95", 2),
            ("Parallel", "parallel", "2", 3),
        ]
        self.gen_vars = {}
        self.gen_enabled = {}
        for label, key, default, row in gen_params:
            ttk.Label(mid_col, text=label + ":").grid(row=row, column=0, sticky='w', pady=2)
            var = tk.StringVar(value=default)
            self.gen_vars[key] = var
            enabled = tk.BooleanVar(value=True)
            self.gen_enabled[key] = enabled
            entry = ttk.Entry(mid_col, textvariable=var, width=9)
            entry.grid(row=row, column=1, sticky='w', padx=(6, 0))
            ttk.Checkbutton(mid_col, variable=enabled).grid(row=row, column=2, sticky='e', padx=(4, 0))
        ttk.Label(mid_col, text="KV-cache K:").grid(row=4, column=0, sticky='w', pady=2)
        self.cache_k_var = tk.StringVar(value="q4_0")
        cache_k_combo = ttk.Combobox(mid_col, textvariable=self.cache_k_var,
                                      values=["f16", "bf16", "f32", "q8_0", "q4_0", "q4_1", "iq4_nl", "q5_0", "q5_1"],
                                      state='readonly', width=6)
        cache_k_combo.grid(row=4, column=1, sticky='w', padx=(6, 0))
        self.cache_k_enabled = tk.BooleanVar(value=True)
        ttk.Checkbutton(mid_col, variable=self.cache_k_enabled).grid(row=4, column=2, sticky='e', padx=(4, 0))
        ttk.Label(mid_col, text="KV-cache V:").grid(row=5, column=0, sticky='w', pady=2)
        self.cache_v_var = tk.StringVar(value="q4_0")
        cache_v_combo = ttk.Combobox(mid_col, textvariable=self.cache_v_var,
                                      values=["f16", "bf16", "f32", "q8_0", "q4_0", "q4_1", "iq4_nl", "q5_0", "q5_1"],
                                      state='readonly', width=6)
        cache_v_combo.grid(row=5, column=1, sticky='w', padx=(6, 0))
        self.cache_v_enabled = tk.BooleanVar(value=True)
        ttk.Checkbutton(mid_col, variable=self.cache_v_enabled).grid(row=5, column=2, sticky='e', padx=(4, 0))
        ttk.Label(mid_col, text="CPU MoE:").grid(row=7, column=0, sticky='w', pady=2)
        self.moe_var = tk.StringVar(value="0")
        ttk.Entry(mid_col, textvariable=self.moe_var, width=9).grid(row=7, column=1, sticky='w', padx=(6, 0))
        self.moe_enabled = tk.BooleanVar(value=True)
        ttk.Checkbutton(mid_col, variable=self.moe_enabled).grid(row=7, column=2, sticky='e', padx=(4, 0))
        ttk.Label(mid_col, text="Reasoning:").grid(row=8, column=0, sticky='w', pady=2)
        self.reasoning_var = tk.StringVar(value="0")
        ttk.Entry(mid_col, textvariable=self.reasoning_var, width=9).grid(row=8, column=1, sticky='w', padx=(6, 0))
        self.reasoning_enabled = tk.BooleanVar(value=True)
        ttk.Checkbutton(mid_col, variable=self.reasoning_enabled).grid(row=8, column=2, sticky='e', padx=(4, 0))
        right_col = ttk.LabelFrame(frame, text="🔧 Дополнительно", padding=10, style='Card.TFrame')
        right_col.pack(side='left', fill='both', expand=True, padx=(1, 0))
        self.flash_attn_var = tk.BooleanVar(value=True)
        self.cont_batching_var = tk.BooleanVar(value=True)
        self.jinja_var = tk.BooleanVar(value=True)
        self.no_mmap_var = tk.BooleanVar(value=True)
        self.kv_unified_var = tk.BooleanVar(value=True)
        self.preserve_thinking_var = tk.BooleanVar(value=True)
        self.repeat_penalty_var = tk.BooleanVar(value=False)
        self.cache_prompt_var = tk.BooleanVar(value=False)
        self.ctx_checkpoints_var = tk.BooleanVar(value=False)
        self.swa_full_var = tk.BooleanVar(value=False)
        self.adv_vars = {
            "flash_attn": self.flash_attn_var,
            "cont_batching": self.cont_batching_var,
            "jinja": self.jinja_var,
            "no_mmap": self.no_mmap_var,
            "kv_unified": self.kv_unified_var,
            "preserve_thinking": self.preserve_thinking_var,
            "repeat_penalty": self.repeat_penalty_var,
            "cache_prompt": self.cache_prompt_var,
            "ctx_checkpoints": self.ctx_checkpoints_var,
            "swa_full": self.swa_full_var,
        }
        labels = {
            "flash_attn": "Flash Attention",
            "cont_batching": "Continual Batching",
            "jinja": "Jinja шаблон",
            "no_mmap": "No MMAP (Windows)",
            "kv_unified": "KV Unified",
            "preserve_thinking": "Preserve Thinking",
            "repeat_penalty": "Repeat Penalty",
            "cache_prompt": "Cache Prompt",
            "ctx_checkpoints": "Ctx Checkpoints",
            "swa_full": "SWA Full",
        }
        for idx, (key, var) in enumerate(self.adv_vars.items()):
            r = idx // 2
            c = idx % 2
            ttk.Checkbutton(right_col, text=labels[key], variable=var).grid(row=r, column=c, sticky='w', padx=(0, 10), pady=2)
        row = 5
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
        self.stop_btn = ttk.Button(frame, text="⏹ Остановить", style='Danger.TButton',
                    command=self._stop_server, state='disabled')
        self.stop_btn.pack(side='left', padx=5, expand=True, fill='x')
        ttk.Button(frame, text="💾 Сохранить конфиг", style='Info.TButton',
                    command=self._save_config).pack(side='left', padx=5, expand=True, fill='x')
        ttk.Button(frame, text="📂 Загрузить конфиг", style='Info.TButton',
                    command=self._load_config).pack(side='left', padx=5, expand=True, fill='x')
    def _create_log_panel(self, parent):
        frame = ttk.LabelFrame(parent, text="📝 Лог сервера", padding=10, style='Card.TFrame')
        frame.pack(fill='both', expand=True)
        log_frame = ttk.Frame(frame)
        log_frame.pack(fill='both', expand=True)
        self.log_text = tk.Text(log_frame, font=('Consolas', 10), state='disabled',
                                   borderwidth=0, wrap='word',
                                   bg='#000000', fg='#ffffff')
        scrollbar = ttk.Scrollbar(log_frame, orient='vertical', command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        self.log_text.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        self.log_text.bind('<Control-c>', self._copy_selected)
        self.log_text.bind('<Button-3>', self._log_context_menu)
    def _mark_dirty(self, *_args):
        if not self._dirty:
            self._dirty = True
    def _register_dirty_traces(self):
        for var in [self.server_path_var, self.model_var, self.mmproj_path_var, self.chat_template_path_var,
                     self.cache_k_var, self.cache_v_var, self.moe_var, self.reasoning_var,
                     self.extra_args_var]:
            var.trace_add('write', self._mark_dirty)
        for var in list(self.server_vars.values()) + list(self.gen_vars.values()):
            var.trace_add('write', self._mark_dirty)
        for var in (list(self.server_enabled.values()) + list(self.gen_enabled.values()) +
                     [self.cache_k_enabled, self.cache_v_enabled, self.moe_enabled,
                      self.reasoning_enabled] +
                     [self.flash_attn_var, self.cont_batching_var, self.jinja_var,
                      self.no_mmap_var, self.kv_unified_var, self.preserve_thinking_var,
                      self.repeat_penalty_var, self.cache_prompt_var, self.ctx_checkpoints_var,
                      self.swa_full_var]):
            var.trace_add('write', self._mark_dirty)
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
        host = self.server_vars.get("host", tk.StringVar()).get().strip()
        if not host:
            errors.append("Укажите адрес хоста")

        server_fields = {
            "port": ("Порт", 1, 65535),
            "context_size": ("Контекст", 1, 1000000),
            "gpu_layers": ("GPU слои", -1, 999),
            "threads": ("Потоки CPU", 1, 1024),
            "batch_size": ("Batch size", 1, 4096),
            "ubatch_size": ("UBatch size", 1, 4096),
        }
        for key, (label, min_v, max_v) in server_fields.items():
            if key == "gpu_layers" and not self.server_enabled.get("gpu_layers", True):
                continue
            val = self.server_vars.get(key, tk.StringVar()).get().strip()
            if not val:
                continue
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
            ok, err = self._validate_numeric("Reasoning", reasoning_val, -1, 10000)
            if not ok:
                errors.append(err)
        moe_val = self.moe_var.get().strip()
        if moe_val:
            ok, err = self._validate_numeric("MoE экспертов", moe_val, 0, 1000)
            if not ok:
                errors.append(err)
        return errors
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
            filetypes=[("MMProj файлы", "*.gguf"), ("Все файлы", "*.*")]
        )
        if path:
            self.mmproj_path_var.set(path)
    def _select_chat_template(self):
        path = filedialog.askopenfilename(
            title="Выберите файл chat template",
            filetypes=[("Chat Template (*.jinja, *.json)", "*.jinja *.json"), ("Все файлы", "*.*")]
        )
        if path:
            self.chat_template_path_var.set(path)
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
        ]
        cmd.extend(["--host", self.server_vars["host"].get()])
        cmd.extend(["--port", self.server_vars["port"].get()])
        server_enabled_map = self.server_enabled
        param_mapping = {
            "context_size": ["-c"],
            "threads": ["-t"],
            "batch_size": ["-b"],
            "ubatch_size": ["-ub"],
        }
        for key, flags in param_mapping.items():
            if key not in server_enabled_map:
                continue
            enabled_bool = server_enabled_map[key]
            if enabled_bool.get():
                cmd.extend(flags + [self.server_vars[key].get()])
        gen_enabled_map = self.gen_enabled
        gen_param_mapping = {
            "temp": ["--temp"],
            "top_k": ["--top-k"],
            "top_p": ["--top-p"],
            "parallel": ["--parallel"],
        }
        for key, flags in gen_param_mapping.items():
            if key not in gen_enabled_map:
                continue
            enabled_bool = gen_enabled_map[key]
            if enabled_bool.get():
                cmd.extend(flags + [self.gen_vars[key].get()])
        mmproj_path = self.mmproj_path_var.get().strip()
        if mmproj_path and os.path.exists(mmproj_path):
            cmd.extend(["--mmproj", mmproj_path])
        else:
            cmd.append("--no-mmproj")
        chat_template_path = self.chat_template_path_var.get().strip()
        if chat_template_path and os.path.exists(chat_template_path):
            cmd.extend(["--chat-template-file", chat_template_path])
        if self.cache_k_enabled.get():
            cmd.extend(["--cache-type-k", self.cache_k_var.get()])
        if self.cache_v_enabled.get():
            cmd.extend(["--cache-type-v", self.cache_v_var.get()])
        if self.flash_attn_var.get():
            cmd.extend(["-fa", "on"])
        if self.cont_batching_var.get():
            cmd.append("--cont-batching")
        if self.jinja_var.get():
            cmd.append("--jinja")
        if self.no_mmap_var.get():
            cmd.append("--no-mmap")
        if self.kv_unified_var.get():
            cmd.append("--kv-unified")
        if self.moe_enabled.get() and self.moe_var.get().strip():
            cmd.extend(["--n-cpu-moe", self.moe_var.get().strip()])
        reasoning = self.reasoning_var.get().strip()
        if self.reasoning_enabled.get() and reasoning:
            cmd.extend(["--reasoning-budget", reasoning])
        if self.preserve_thinking_var.get():
            cmd.extend(["--chat-template-kwargs", '{"preserve_thinking":true}'])
        else:
            cmd.extend(["--chat-template-kwargs", '{"preserve_thinking":false}'])
        if self.repeat_penalty_var.get():
            cmd.extend(["--repeat-penalty", "1.1"])
        if self.cache_prompt_var.get():
            cmd.append("--cache-prompt")
        if self.ctx_checkpoints_var.get():
            cmd.extend(["--ctx-checkpoints", "64"])
        if self.swa_full_var.get():
            cmd.append("--swa-full")
        extra = self.extra_args_var.get().strip()
        if extra:
            try:
                cmd.extend(shlex.split(extra))
            except ValueError as e:
                messagebox.showerror("Ошибка", f"Некорректный формат доп. аргументов:\n{e}")
                return None
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
        # Очистка лога перед новым запуском
        self.log_text.configure(state='normal')
        self.log_text.delete(1.0, tk.END)
        self.log_text.configure(state='disabled')

        self.is_running = True
        self.start_btn.configure(text="⏳ Запуск...", state='disabled')
        self.stop_btn.configure(state='normal')
        if self._log_file and not self._log_file.closed:
            self._log_file.close()
            self._log_file = None
        self._log("Команда: " + " ".join(cmd))
        self._log("Запуск сервера...")
        try:
            if sys.platform == "win32":
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
            else:
                self.server_process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    encoding='utf-8',
                    errors='replace',
                    start_new_session=True
                )
            monitor_thread = threading.Thread(target=self._monitor_process, daemon=True)
            monitor_thread.start()
            self._start_title_animation()
        except Exception as e:
            self._log(f"Ошибка запуска: {e}")
            self.is_running = False
            self.start_btn.configure(text="▶ Запустить", state='normal')
            self.stop_btn.configure(state='disabled')
    def _monitor_process(self):
        if self.server_process is None:
            return
        try:
            while True:
                line = self.server_process.stdout.readline()
                if not line:
                    break
                log_line = line.rstrip()
                self.root.after(0, self._log, log_line)
                if 'listening' in log_line.lower():
                    self.root.after(0, self._on_server_listening)
        except Exception:
            pass
        try:
            self.server_process.wait()
        except Exception as e:
            self.root.after(0, self._log, f"Ошибка получения кода завершения: {e}")
            return
        if not self.is_running:
            return
        self.root.after(0, self._on_server_stopped)
    def _on_server_stopped(self, logged=True):
        # Double-check to prevent duplicate logs from race conditions
        if not self.is_running:
            return
        self._cancel_poll_callback()
        still_running = self.is_running  # capture state before clearing
        self.is_running = False
        if still_running and logged:
            self._log("Сервер остановлен.")
        self.start_btn.configure(text="▶ Запустить", state='normal')
        self.stop_btn.configure(state='disabled')
        self._stop_title_animation()

    def _on_server_listening(self):
        if self.is_running:
            self.start_btn.configure(text="✅ Запущен")

    def _start_title_animation(self):
        self._animation_running = True
        self._animation_thread = threading.Thread(target=self._title_animation_loop, daemon=True)
        self._animation_thread.start()

    def _stop_title_animation(self):
        self._animation_running = False
        if self._animation_thread is not None:
            self._animation_thread.join(timeout=1.0)
            self._animation_thread = None
        self.root.title("llama GUI")

    def _title_animation_loop(self):
        count = 0
        while self._animation_running:
            try:
                self.root.after(0, self._set_title_frame, count)
            except Exception:
                break
            count = (count + 1) % 4
            time.sleep(0.3)

    def _set_title_frame(self, count):
        if self._animation_running:
            self.root.title("llama GUI" + (" * " * count).rstrip())
    def _stop_server(self):
        if self.server_process and self.server_process.poll() is None:
            self._log("Остановка сервера...")
            self.server_process.terminate()
            self._poll_stop_with_timeout(5.0)
        else:
            self._log("Сервер не запущен.")
            self._on_server_stopped(logged=False)
    def _cancel_poll_callback(self):
        if self._poll_timeout_callback_id is not None:
            self.root.after_cancel(self._poll_timeout_callback_id)
            self._poll_timeout_callback_id = None

    def _poll_stop(self):
        if not self.server_process or self.server_process.poll() is not None:
            if self.server_process:
                try:
                    self.server_process.wait(timeout=2)
                except Exception:
                    pass
            self._log("Сервер остановлен.")
            self._on_server_stopped(logged=False)
            return
        self._poll_timeout_callback_id = self.root.after(200, self._poll_stop)

    def _force_kill(self):
        if self.server_process and self.server_process.poll() is None:
            was_running = True
            try:
                if sys.platform == "win32":
                    self.server_process.terminate()  # CTRL_BREAK_EVENT on Windows
                else:
                    import signal
                    os.killpg(os.getpgid(self.server_process.pid), signal.SIGKILL)
            except Exception as e:
                self.root.after(0, self._log, f"Ошибка принудительной остановки: {e}")
            try:
                self.server_process.wait(timeout=3)
            except Exception:
                pass
        else:
            was_running = False
        if was_running and self.is_running:
            self._log("Сервер принудительно остановлен.")
            self._on_server_stopped(logged=False)

    def _poll_stop_with_timeout(self, remaining=5.0):
        if remaining <= 0 or not self.is_running:
            self._cancel_poll_callback()
            if self.server_process and self.server_process.poll() is None:
                self._force_kill()
            elif self.is_running:
                self._on_server_stopped(logged=True)
            return
        if self.server_process and self.server_process.poll() is not None:
            self._cancel_poll_callback()
            self._log("Сервер остановлен.")
            self._on_server_stopped(logged=False)
            return
        self._poll_timeout_callback_id = self.root.after(200, lambda r=remaining - 0.2: self._poll_stop_with_timeout(r))
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
    def _log(self, message):
        try:
            if self._log_file is None or self._log_file.closed:
                log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "log.txt")
                try:
                    self._log_file = open(log_path, 'w', encoding='utf-8')
                except Exception:
                    self._log_file = None
            if self._log_file and not self._log_file.closed:
                timestamp = datetime.now().strftime("%H:%M:%S")
                self._log_file.write(f"[{timestamp}] {message}\n")
                self._log_file.flush()
        except Exception:
            pass
        self._log_line_count += 1
        if self._log_line_count > 5000:
            self.log_text.configure(state='normal')
            current_lines = int(float(self.log_text.index('end-1c').split('.')[0]))
            if current_lines > 100:
                remove_count = min(100, current_lines - 1)
                self.log_text.delete(1.0, f"{remove_count}.0")
                self._log_line_count -= remove_count
            self.log_text.configure(state='disabled')
        self.log_text.configure(state='normal')
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
        self.log_text.configure(state='disabled')
    def _save_config(self):
        path = filedialog.asksaveasfilename(
            title="Сохранить конфиг",
            initialdir=os.path.dirname(os.path.abspath(__file__)),
            defaultextension=".json",
            filetypes=[("JSON", "*.json")]
        )
        if not path:
            return
        if not self._write_config(path):
            return
        self._dirty = False
        _save_last_config_path(path)
        messagebox.showinfo("Инфо", f"Конфиг сохранён: {path}")
    def _write_config(self, path):
        config = {
            "model": self.model_var.get(),
            "server_path": self.server_path_var.get(),
            "mmproj_path": self.mmproj_path_var.get(),
            "chat_template_path": self.chat_template_path_var.get(),
            "server": {k: v.get() for k, v in self.server_vars.items()},
            "server_enabled": {k: v.get() for k, v in self.server_enabled.items()},
            "generation": {k: v.get() for k, v in self.gen_vars.items()},
            "gen_enabled": {k: v.get() for k, v in self.gen_enabled.items()},
            "cache_k": self.cache_k_var.get(),
            "cache_v": self.cache_v_var.get(),
            "cache_k_enabled": self.cache_k_enabled.get(),
            "cache_v_enabled": self.cache_v_enabled.get(),
            "moe": self.moe_var.get(),
            "moe_enabled": self.moe_enabled.get(),
            "reasoning": self.reasoning_var.get(),
            "reasoning_enabled": self.reasoning_enabled.get(),
            "advanced": {k: v.get() for k, v in self.adv_vars.items()},
            "extra_args": self.extra_args_var.get(),
        }
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось сохранить конфиг:\n{e}")
            return False
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
            self._apply_config(config)
            _save_last_config_path(path)
            self._dirty = False
            messagebox.showinfo("Инфо", f"Конфиг загружен: {path}")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка загрузки конфига: {e}")
    def _auto_load_config(self):
        path = _get_last_config_path()
        if not path:
            return
        try:
            with open(path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            self._apply_config(config)
        except Exception:
            self._log(f"Ошибка загрузки последнего конфига ({path}): неизвестная ошибка")
    def _apply_config(self, config):
        known_server_keys = set(self.server_vars.keys())
        known_gen_keys = set(self.gen_vars.keys())
        known_gen_enabled_keys = set(self.gen_enabled.keys())
        known_server_enabled_keys = set(self.server_enabled.keys())

        if config.get("model"):
            self.model_var.set(config["model"])
        if config.get("server_path"):
            self.server_path_var.set(config["server_path"])
        if config.get("mmproj_path"):
            self.mmproj_path_var.set(config["mmproj_path"])
        if config.get("chat_template_path"):
            self.chat_template_path_var.set(config["chat_template_path"])

        unknown_server = []
        for k, v in config.get("server", {}).items():
            if k in known_server_keys:
                self.server_vars[k].set(v)
            else:
                unknown_server.append(k)

        for k, v in config.get("server_enabled", {}).items():
            if k in known_server_enabled_keys:
                self.server_enabled[k].set(v)
            elif k not in unknown_server:
                unknown_server.append(k + "_enabled")

        unknown_gen = []
        for k, v in config.get("generation", {}).items():
            if k in known_gen_keys:
                self.gen_vars[k].set(v)
            else:
                unknown_gen.append(k)

        for k, v in config.get("gen_enabled", {}).items():
            if k in known_gen_enabled_keys:
                self.gen_enabled[k].set(v)
            elif k not in unknown_gen:
                unknown_gen.append(k + "_enabled")

        if config.get("cache_k"):
            self.cache_k_var.set(config["cache_k"])
        if config.get("cache_v"):
            self.cache_v_var.set(config["cache_v"])
        if config.get("cache_k_enabled"):
            self.cache_k_enabled.set(config["cache_k_enabled"])
        if config.get("cache_v_enabled"):
            self.cache_v_enabled.set(config["cache_v_enabled"])
        if config.get("moe"):
            self.moe_var.set(config["moe"])
        if config.get("moe_enabled"):
            self.moe_enabled.set(config["moe_enabled"])
        if config.get("reasoning"):
            self.reasoning_var.set(config["reasoning"])
        if config.get("reasoning_enabled"):
            self.reasoning_enabled.set(config["reasoning_enabled"])
        if "extra_args" in config and config["extra_args"]:
            self.extra_args_var.set(config["extra_args"])

        unknown_adv = []
        for k, v in config.get("advanced", {}).items():
            if k in self.adv_vars:
                self.adv_vars[k].set(v)
            else:
                unknown_adv.append(k)

        all_unknown = unknown_server + unknown_gen + unknown_adv
        if all_unknown:
            messagebox.showinfo(
                "Инфо",
                f"Конфиг загружен. Неизвестные поля пропущены:\n{', '.join(all_unknown)}\n\nОбновите лаунчер до последней версии для поддержки новых параметров."
            )
    def _on_closing(self):
        self._cancel_poll_callback()
        if self.server_process and self.server_process.poll() is None:
            if not messagebox.askyesno("Предупреждение", "Сервер запущен. Закрыть приложение и остановить сервер?"):
                return
            self._log("Остановка сервера...")
            self.server_process.terminate()
            try:
                self.server_process.wait(timeout=5)
            except Exception:
                try:
                    self.server_process.kill()
                    self.server_process.wait(timeout=3)
                except Exception:
                    pass
        if self._dirty:
            result = messagebox.askokcancel(
                "Сохранение",
                "Параметры были изменены. Сохранить конфиг перед закрытием?",
                icon="question"
            )
            if result is True:
                self._save_config()
            elif result is False:
                pass
            else:
                return
        self._stop_title_animation()
        if self._log_file and not self._log_file.closed:
            self._log_file.close()
        self.root.destroy()
def main():
    root = tk.Tk()
    app = LlamaLauncherApp(root)
    root.mainloop()
if __name__ == "__main__":
    main()

