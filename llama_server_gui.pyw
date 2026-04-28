import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
import subprocess
import os
import threading
import shlex
import time
import sys
import atexit

class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip_window = None
        widget.bind('<Enter>', self.show_tip)
        widget.bind('<Leave>', self.hide_tip)

    def show_tip(self, event=None):
        if self.tip_window or not self.text:
            return
        x, y, _, _ = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 25
        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(tw, text=self.text, justify=tk.LEFT,
                         background="#ffffe0", relief=tk.SOLID, borderwidth=1,
                         font=("Segoe UI", 9))
        label.pack()

    def hide_tip(self, event=None):
        if self.tip_window:
            self.tip_window.destroy()
            self.tip_window = None

class CollapsibleFrame(ttk.Frame):
    """Сворачиваемый фрейм с заголовком-кнопкой"""
    def __init__(self, parent, title, collapsed=True, **kwargs):
        super().__init__(parent, **kwargs)
        self.collapsed = collapsed
        self.title = title
        
        self.toggle_btn = ttk.Button(self, text=f"▶ {title}", command=self.toggle,
                                     style="Toggle.TButton")
        self.toggle_btn.pack(fill=tk.X, pady=(0, 5))
        
        self.content_frame = ttk.Frame(self)
        if not collapsed:
            self.content_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 5))
    
    def toggle(self):
        if self.collapsed:
            self.content_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 5))
            self.toggle_btn.config(text=f"▼ {self.title}")
            self.collapsed = False
        else:
            self.content_frame.pack_forget()
            self.toggle_btn.config(text=f"▶ {self.title}")
            self.collapsed = True

class LlamaGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("llama.cpp GUI Server Launcher")
        self.root.geometry("850x720")
        self.root.minsize(750, 650)
        self.root.configure(bg="#f5f5f5")
        
        # Переменные
        self.model_path = tk.StringVar()
        self.mmproj_path = tk.StringVar()
        self.api_key = tk.StringVar()
        self.port = tk.StringVar(value="1414")
        self.host = tk.StringVar(value="192.168.0.48")
        self.process = None
        self.bat_file = None
        self.running = False
        
        # Параметры модели
        self.ngl = tk.StringVar(value="99")
        self.context = tk.StringVar(value="120000")
        self.temp = tk.StringVar(value="0.8")
        self.threads = tk.StringVar(value="4")
        self.batch = tk.StringVar(value="512")
        self.cache_type_k = tk.StringVar(value="q8_0")
        self.cache_type_v = tk.StringVar(value="q8_0")
        self.parallel_slots = tk.StringVar(value="2")
        self.flash_attn = tk.BooleanVar(value=True)
        self.reasoning_budget = tk.StringVar(value="0")
        self.no_mmproj_offload = tk.BooleanVar(value=False)
        
        # Стили
        self.setup_styles()
        
        # Регистрация очистки при завершении
        atexit.register(self.cleanup_temp_files)
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        self.create_widgets()
        self.update_start_button_text()
    
    def setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        
        style.configure('.', background="#f5f5f5", font=('Segoe UI', 9))
        style.configure('TLabel', background="#f5f5f5", foreground="#333")
        style.configure('TLabelframe', background="#f5f5f5", foreground="#333", borderwidth=1, relief=tk.GROOVE)
        style.configure('TLabelframe.Label', background="#f5f5f5", foreground="#333", font=('Segoe UI', 9, 'bold'))
        style.configure('TEntry', fieldbackground="white", borderwidth=1, padding=4)
        style.configure('TButton', background="#0078d4", foreground="white", borderwidth=0, padding=6, font=('Segoe UI', 9))
        style.map('TButton', background=[('active', '#106ebe')])
        style.configure('Toggle.TButton', background="#e0e0e0", foreground="#333", font=('Segoe UI', 9, 'bold'))
        style.map('Toggle.TButton', background=[('active', '#c0c0c0')])
    
    def create_widgets(self):
        main = ttk.Frame(self.root, padding="12")
        main.pack(fill=tk.BOTH, expand=True)
        
        # Заголовок
        header = ttk.Frame(main)
        header.pack(fill=tk.X, pady=(0, 12))
        ttk.Label(header, text="🦙 llama.cpp GUI Server Launcher", font=('Segoe UI', 14, 'bold')).pack()
        
        # === Модель ===
        model_frame = ttk.LabelFrame(main, text="Модель", padding="8")
        model_frame.pack(fill=tk.X, pady=(0, 12))
        
        model_row = ttk.Frame(model_frame)
        model_row.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(model_row, text="GGUF:").pack(side=tk.LEFT, padx=(0, 5))
        self.model_entry = ttk.Entry(model_row, textvariable=self.model_path)
        self.model_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        ttk.Button(model_row, text="Обзор", command=self.browse_model, width=8).pack(side=tk.RIGHT)
        ToolTip(self.model_entry, "Путь к GGUF файлу модели")
        
        mmproj_row = ttk.Frame(model_frame)
        mmproj_row.pack(fill=tk.X, pady=(0, 5))
        ttk.Label(mmproj_row, text="MMPROJ:").pack(side=tk.LEFT, padx=(0, 5))
        self.mmproj_entry = ttk.Entry(mmproj_row, textvariable=self.mmproj_path)
        self.mmproj_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        ttk.Button(mmproj_row, text="Обзор", command=self.browse_mmproj, width=8).pack(side=tk.RIGHT)
        ToolTip(self.mmproj_entry, "Опциональный путь к mmproj файлу (для мультимодальных моделей)")
        
        no_offload_row = ttk.Frame(model_frame)
        no_offload_row.pack(fill=tk.X)
        self.no_offload_check = ttk.Checkbutton(no_offload_row, text="Отключить выгрузку mmproj на GPU (--no-mmproj-offload)", 
                                                variable=self.no_mmproj_offload)
        self.no_offload_check.pack(anchor=tk.W, pady=(5, 0))
        ToolTip(self.no_offload_check, "Не выгружать проектор mmproj на видеокарту (оставить в CPU)")
        
        # === Параметры сервера ===
        server_frame = ttk.LabelFrame(main, text="Сервер", padding="8")
        server_frame.pack(fill=tk.X, pady=(0, 12))
        
        server_row = ttk.Frame(server_frame)
        server_row.pack(fill=tk.X)
        
        ttk.Label(server_row, text="Хост:").pack(side=tk.LEFT, padx=(0, 5))
        host_entry = ttk.Entry(server_row, textvariable=self.host, width=12)
        host_entry.pack(side=tk.LEFT, padx=(0, 15))
        ToolTip(host_entry, "IP адрес для прослушивания (127.0.0.1 = локально)")
        
        ttk.Label(server_row, text="Порт:").pack(side=tk.LEFT, padx=(0, 5))
        port_entry = ttk.Entry(server_row, textvariable=self.port, width=6)
        port_entry.pack(side=tk.LEFT, padx=(0, 15))
        ToolTip(port_entry, "Порт для HTTP API (по умолчанию 1414)")
        
        ttk.Label(server_row, text="Слоты:").pack(side=tk.LEFT, padx=(0, 5))
        slots_entry = ttk.Entry(server_row, textvariable=self.parallel_slots, width=4)
        slots_entry.pack(side=tk.LEFT)
        ToolTip(slots_entry, "Количество параллельных сессий (-np, по умолчанию 2)")
        
        api_row = ttk.Frame(server_frame)
        api_row.pack(fill=tk.X, pady=(8, 0))
        ttk.Label(api_row, text="API Key:").pack(side=tk.LEFT, padx=(0, 5))
        self.api_entry = ttk.Entry(api_row, textvariable=self.api_key, width=40, show="*")
        self.api_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.show_key = tk.BooleanVar(value=False)
        def toggle_key():
            self.api_entry.config(show="" if self.show_key.get() else "*")
        ttk.Checkbutton(api_row, text="Показать", variable=self.show_key, command=toggle_key).pack(side=tk.RIGHT)
        ToolTip(self.api_entry, "API ключ для авторизации запросов (опционально)")
        
        # === Сворачиваемый блок параметров модели ===
        self.params_collapsible = CollapsibleFrame(main, "⚙️ Параметры модели", collapsed=True)
        self.params_collapsible.pack(fill=tk.X, pady=(0, 12))
        
        params_inner = ttk.Frame(self.params_collapsible.content_frame)
        params_inner.pack(fill=tk.X)
        
        # Первый ряд
        ttk.Label(params_inner, text="ngl", font=('Consolas', 9, 'bold'), width=12, anchor=tk.W).grid(row=0, column=0, padx=(0, 15), pady=(0, 2), sticky=tk.W)
        ttk.Label(params_inner, text="c", font=('Consolas', 9, 'bold'), width=12, anchor=tk.W).grid(row=0, column=1, padx=(0, 15), pady=(0, 2), sticky=tk.W)
        ttk.Label(params_inner, text="temp", font=('Consolas', 9, 'bold'), width=12, anchor=tk.W).grid(row=0, column=2, padx=0, pady=(0, 2), sticky=tk.W)
        
        ngl_entry = ttk.Entry(params_inner, textvariable=self.ngl, width=12)
        ngl_entry.grid(row=1, column=0, padx=(0, 15), pady=(0, 2), sticky=tk.W)
        ctx_entry = ttk.Entry(params_inner, textvariable=self.context, width=12)
        ctx_entry.grid(row=1, column=1, padx=(0, 15), pady=(0, 2), sticky=tk.W)
        
        temp_frame = ttk.Frame(params_inner)
        temp_frame.grid(row=1, column=2, padx=0, pady=(0, 2), sticky=tk.W)
        temp_scale = tk.Scale(temp_frame, from_=0.0, to=2.0, resolution=0.01, orient=tk.HORIZONTAL, 
                               variable=self.temp, length=100, bg="#f5f5f5", fg="#333",
                               highlightthickness=0, troughcolor="#ddd")
        temp_scale.pack(side=tk.LEFT)
        temp_label = ttk.Label(temp_frame, textvariable=self.temp, width=4, font=('Consolas', 8))
        temp_label.pack(side=tk.LEFT, padx=(5, 0))
        
        ttk.Label(params_inner, text="GPU слои", font=('Segoe UI', 7), foreground="#888").grid(row=2, column=0, padx=(0, 15), sticky=tk.W)
        ttk.Label(params_inner, text="Размер контекста", font=('Segoe UI', 7), foreground="#888").grid(row=2, column=1, padx=(0, 15), sticky=tk.W)
        ttk.Label(params_inner, text="Температура", font=('Segoe UI', 7), foreground="#888").grid(row=2, column=2, padx=0, sticky=tk.W)
        
        ToolTip(ngl_entry, "Количество слоев на GPU (-1 = все)")
        ToolTip(ctx_entry, "Максимальная длина контекста (по умолчанию 120000)")
        ToolTip(temp_scale, "Креативность ответов (по умолчанию 0.8)")
        
        # Второй ряд
        ttk.Label(params_inner, text="t", font=('Consolas', 9, 'bold'), width=12, anchor=tk.W).grid(row=3, column=0, padx=(0, 15), pady=(8, 2), sticky=tk.W)
        ttk.Label(params_inner, text="b", font=('Consolas', 9, 'bold'), width=12, anchor=tk.W).grid(row=3, column=1, padx=(0, 15), pady=(8, 2), sticky=tk.W)
        ttk.Label(params_inner, text="cache", font=('Consolas', 9, 'bold'), width=12, anchor=tk.W).grid(row=3, column=2, padx=0, pady=(8, 2), sticky=tk.W)
        
        threads_frame = ttk.Frame(params_inner)
        threads_frame.grid(row=4, column=0, padx=(0, 15), pady=(0, 2), sticky=tk.W)
        threads_scale = tk.Scale(threads_frame, from_=1, to=32, orient=tk.HORIZONTAL, 
                                  variable=self.threads, length=100, bg="#f5f5f5", fg="#333",
                                  highlightthickness=0, troughcolor="#ddd")
        threads_scale.pack(side=tk.LEFT)
        threads_label = ttk.Label(threads_frame, textvariable=self.threads, width=4, font=('Consolas', 8))
        threads_label.pack(side=tk.LEFT, padx=(5, 0))
        
        batch_entry = ttk.Entry(params_inner, textvariable=self.batch, width=12)
        batch_entry.grid(row=4, column=1, padx=(0, 15), pady=(0, 2), sticky=tk.W)
        
        cache_frame = ttk.Frame(params_inner)
        cache_frame.grid(row=4, column=2, padx=0, pady=(0, 2), sticky=tk.W)
        ttk.Label(cache_frame, text="k:").pack(side=tk.LEFT)
        k_entry = ttk.Entry(cache_frame, textvariable=self.cache_type_k, width=5)
        k_entry.pack(side=tk.LEFT, padx=(2, 5))
        ttk.Label(cache_frame, text="v:").pack(side=tk.LEFT)
        v_entry = ttk.Entry(cache_frame, textvariable=self.cache_type_v, width=5)
        v_entry.pack(side=tk.LEFT, padx=(2, 0))
        
        ttk.Label(params_inner, text="Потоки CPU", font=('Segoe UI', 7), foreground="#888").grid(row=5, column=0, padx=(0, 15), sticky=tk.W)
        ttk.Label(params_inner, text="Размер батча", font=('Segoe UI', 7), foreground="#888").grid(row=5, column=1, padx=(0, 15), sticky=tk.W)
        ttk.Label(params_inner, text="Тип кэша K/V", font=('Segoe UI', 7), foreground="#888").grid(row=5, column=2, padx=0, sticky=tk.W)
        
        ToolTip(threads_scale, "Количество потоков CPU")
        ToolTip(batch_entry, "Размер батча для обработки")
        ToolTip(k_entry, "Тип кэша для ключей (q8_0, f16 и др.)")
        ToolTip(v_entry, "Тип кэша для значений")
        
        # Третий ряд: Flash Attention и Reasoning Budget
        ttk.Label(params_inner, text="flash-attn", font=('Consolas', 9, 'bold'), width=12, anchor=tk.W).grid(row=6, column=0, padx=(0, 15), pady=(8, 2), sticky=tk.W)
        self.flash_check = ttk.Checkbutton(params_inner, variable=self.flash_attn, text="on/off")
        self.flash_check.grid(row=6, column=1, padx=(0, 15), pady=(8, 2), sticky=tk.W)
        ttk.Label(params_inner, text="Включить Flash Attention", font=('Segoe UI', 7), foreground="#888").grid(row=6, column=2, padx=0, pady=(8, 2), sticky=tk.W)
        ToolTip(self.flash_check, "Ускоряет обработку внимания на GPU (--flash-attn on/off)")
        
        ttk.Label(params_inner, text="reasoning-budget", font=('Consolas', 9, 'bold'), width=12, anchor=tk.W).grid(row=7, column=0, padx=(0, 15), pady=(4, 2), sticky=tk.W)
        budget_entry = ttk.Entry(params_inner, textvariable=self.reasoning_budget, width=12)
        budget_entry.grid(row=7, column=1, padx=(0, 15), pady=(4, 2), sticky=tk.W)
        ttk.Label(params_inner, text="Лимит токенов для рассуждений (0 = отключено)", font=('Segoe UI', 7), foreground="#888").grid(row=7, column=2, padx=0, pady=(4, 2), sticky=tk.W)
        ToolTip(budget_entry, "Максимальное количество токенов на этапе рассуждения")
        
        # Дополнительные аргументы
        extra_frame = ttk.LabelFrame(main, text="Дополнительные аргументы", padding="6")
        extra_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.extra_params = tk.Text(extra_frame, height=2, wrap=tk.WORD, font=('Consolas', 9), 
                                     borderwidth=1, relief=tk.SOLID, bg="white")
        self.extra_params.pack(fill=tk.X)
        self.extra_params.insert("1.0", "--jinja")
        ToolTip(self.extra_params, "Дополнительные аргументы командной строки для сервера")
        
        # Кнопки управления
        btn_frame = ttk.Frame(main)
        btn_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.start_btn = ttk.Button(btn_frame, command=self.start_or_reload_model, width=14)
        self.start_btn.pack(side=tk.LEFT, padx=(0, 6))
        
        self.stop_btn = ttk.Button(btn_frame, text="⏹ Остановить", command=self.stop_model, width=14, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=(0, 6))
        
        # Вывод (высота 12 строк)
        output_frame = ttk.LabelFrame(main, text="Вывод", padding="6")
        output_frame.pack(fill=tk.BOTH, expand=True)
        
        try:
            self.output_text = tk.Text(output_frame, height=12, wrap=tk.WORD, font=('Hack', 9),
                                        borderwidth=1, relief=tk.SOLID, bg="#1e1e1e", fg="#d4d4d4")
        except:
            self.output_text = tk.Text(output_frame, height=12, wrap=tk.WORD, font=('Consolas', 9),
                                        borderwidth=1, relief=tk.SOLID, bg="#1e1e1e", fg="#d4d4d4")
        
        self.output_text.pack(fill=tk.BOTH, expand=True)
        
        scroll = ttk.Scrollbar(self.output_text, orient=tk.VERTICAL, command=self.output_text.yview)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.output_text.configure(yscrollcommand=scroll.set)
    
    def browse_model(self):
        filename = filedialog.askopenfilename(
            title="Выберите GGUF файл модели",
            filetypes=[("GGUF files", "*.gguf"), ("All files", "*.*")]
        )
        if filename:
            self.model_path.set(filename)
    
    def browse_mmproj(self):
        filename = filedialog.askopenfilename(
            title="Выберите mmproj файл",
            filetypes=[("MMPROJ files", "*.gguf"), ("All files", "*.*")]
        )
        if filename:
            self.mmproj_path.set(filename)
    
    def build_command(self):
        model = self.model_path.get().strip()
        if not model:
            return None
        
        params = []
        params.extend(["--host", self.host.get().strip()])
        params.extend(["--port", self.port.get().strip()])
        if self.parallel_slots.get().strip():
            params.extend(["-np", self.parallel_slots.get().strip()])
        
        api_key = self.api_key.get().strip()
        if api_key:
            params.extend(["--api-key", api_key])
        
        if self.ngl.get().strip():
            params.extend(["-ngl", self.ngl.get().strip()])
        if self.context.get().strip():
            params.extend(["-c", self.context.get().strip()])
        if self.temp.get().strip():
            params.extend(["--temp", self.temp.get().strip()])
        if self.threads.get().strip():
            params.extend(["-t", self.threads.get().strip()])
        if self.batch.get().strip():
            params.extend(["-b", self.batch.get().strip()])
        if self.cache_type_k.get().strip() and self.cache_type_v.get().strip():
            params.extend(["--cache-type-k", self.cache_type_k.get().strip()])
            params.extend(["--cache-type-v", self.cache_type_v.get().strip()])
        
        if self.flash_attn.get():
            params.extend(["--flash-attn", "on"])
        else:
            params.extend(["--flash-attn", "off"])
        
        budget = self.reasoning_budget.get().strip()
        if budget:
            params.extend(["--reasoning-budget", budget])
        
        mmproj = self.mmproj_path.get().strip()
        if mmproj:
            mmproj_quoted = f'"{mmproj}"' if ' ' in mmproj else mmproj
            params.extend(["--mmproj", mmproj_quoted])
        
        if self.no_mmproj_offload.get():
            params.append("--no-mmproj-offload")
        
        extra_text = self.extra_params.get("1.0", tk.END).strip()
        if extra_text:
            try:
                extra_params = shlex.split(extra_text, posix=False)
                params.extend(extra_params)
            except:
                params.extend(extra_text.split())
        
        model_quoted = f'"{model}"' if ' ' in model else model
        return model_quoted, params
    
    def append_output(self, text):
        self.output_text.insert(tk.END, text)
        self.output_text.see(tk.END)
        self.root.update_idletasks()
    
    def update_start_button_text(self):
        if self.process and self.process.poll() is None:
            self.start_btn.config(text="🔄 Перезагрузить")
        else:
            self.start_btn.config(text="▶ Запустить")
    
    def start_or_reload_model(self):
        if self.process and self.process.poll() is None:
            self.append_output("="*50 + "\n")
            self.append_output("🔄 Перезагрузка модели с новыми параметрами...\n")
            self.stop_model(silent=True)
            self.root.after(500, self.start_model)
        else:
            self.start_model()
    
    def start_model(self):
        result = self.build_command()
        if not result:
            messagebox.showerror("Ошибка", "Выберите файл модели!")
            return
        
        model_quoted, params = result
        model = self.model_path.get().strip()
        if not os.path.exists(model):
            messagebox.showerror("Ошибка", f"Файл модели не найден:\n{model}")
            return
        
        mmproj = self.mmproj_path.get().strip()
        if mmproj and not os.path.exists(mmproj):
            messagebox.showerror("Ошибка", f"Файл mmproj не найден:\n{mmproj}")
            return
        
        script_dir = os.path.dirname(os.path.abspath(__file__))
        server_path = os.path.join(script_dir, "llama-server.exe")
        if not os.path.exists(server_path):
            import shutil
            server_path = shutil.which("llama-server.exe")
            if not server_path:
                messagebox.showerror("Ошибка", "llama-server.exe не найден! Загрузите его с GitHub llama.cpp")
                return
            script_dir = os.path.dirname(server_path)
        
        # Удаляем старый BAT файл, если существует
        if self.bat_file and os.path.exists(self.bat_file):
            try:
                os.remove(self.bat_file)
            except:
                pass
        
        self.bat_file = os.path.join(script_dir, "llama_server_temp.bat")
        server_cmd = "llama-server.exe" if os.path.dirname(server_path) == script_dir else f'"{server_path}"'
        command_parts = [server_cmd, "-m", model_quoted] + params
        command = ' '.join(command_parts)
        
        self.append_output("─" * 50 + "\n")
        self.append_output(f"Запуск сервера для: {os.path.basename(model)}\n")
        self.append_output(f"API: http://{self.host.get()}:{self.port.get()}\n")
        self.append_output(f"Слоты: {self.parallel_slots.get()}\n")
        if mmproj:
            self.append_output(f"MMPROJ: {os.path.basename(mmproj)}\n")
        if self.no_mmproj_offload.get():
            self.append_output("MMPROJ offload: disabled\n")
        if self.api_key.get().strip():
            self.append_output("API Key: установлен\n")
        self.append_output(f"Flash Attention: {'on' if self.flash_attn.get() else 'off'}\n")
        if self.reasoning_budget.get().strip():
            self.append_output(f"Reasoning budget: {self.reasoning_budget.get()}\n")
        self.append_output("─" * 50 + "\n\n")
        
        try:
            with open(self.bat_file, 'w', encoding='utf-8') as f:
                f.write('@echo off\n')
                f.write('chcp 65001 >nul 2>&1\n')
                f.write(f'cd /d "{script_dir}"\n')
                f.write(f'echo Запуск LLaMA сервера...\n')
                f.write(f'echo.\n')
                f.write(f'{command}\n')
                f.write('echo.\n')
                f.write('echo Сервер остановлен\n')
                f.write('echo.\n')
                f.write('pause\n')
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))
            return
        
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.output_text.delete(1.0, tk.END)
        self.running = True
        
        self.thread = threading.Thread(target=self.run_process, daemon=True)
        self.thread.start()
    
    def run_process(self):
        try:
            self.process = subprocess.Popen(
                [self.bat_file],
                shell=True,
                creationflags=subprocess.CREATE_NEW_CONSOLE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
            self.append_output(f"✅ Сервер запущен (PID: {self.process.pid})\n")
            self.append_output(f"🌐 API: http://{self.host.get()}:{self.port.get()}\n")
            self.append_output(f"📖 Документация: http://{self.host.get()}:{self.port.get()}/docs\n")
            self.append_output("\n🛑 Для остановки нажмите 'Остановить'\n\n")
            
            def read_output():
                try:
                    if self.process and self.process.stdout:
                        for line in iter(self.process.stdout.readline, ''):
                            if not self.running:
                                break
                            if line:
                                self.append_output(line)
                            if self.process.poll() is not None:
                                break
                except Exception as e:
                    self.append_output(f"Ошибка чтения вывода: {e}\n")
                finally:
                    if self.process and self.process.stdout:
                        try:
                            self.process.stdout.close()
                        except:
                            pass
            
            output_thread = threading.Thread(target=read_output, daemon=True)
            output_thread.start()
            self.process.wait()
            self.append_output(f"\n✅ Сервер остановлен (код: {self.process.returncode})\n")
        except Exception as e:
            self.append_output(f"\n❌ Ошибка: {str(e)}\n")
        finally:
            self.running = False
            self.root.after(0, self.reset_buttons)
    
    def kill_all_llama_servers(self, silent=False):
        """Принудительно убивает все процессы llama-server.exe"""
        if os.name == 'nt':
            if not silent:
                self.append_output("Принудительное завершение всех процессов llama-server.exe...\n")
            try:
                subprocess.run('taskkill /F /IM llama-server.exe /T', shell=True, capture_output=True, timeout=5)
                time.sleep(1)
                if not silent:
                    self.append_output("✅ Все процессы llama-server.exe остановлены\n")
            except Exception as e:
                if not silent:
                    self.append_output(f"Ошибка при завершении: {e}\n")
    
    def stop_model(self, silent=False):
        """Остановка сервера с гарантированной выгрузкой модели из памяти"""
        if not (self.process and self.process.poll() is None):
            if not silent:
                self.append_output("ℹ️ Нет активного сервера для остановки\n")
            self.reset_buttons()
            return

        if not silent:
            self.append_output("\n" + "="*50 + "\n")
            self.append_output("🛑 Остановка сервера...\n")
        self.running = False

        pid = self.process.pid
        if not silent:
            self.append_output(f"PID процесса cmd: {pid}\n")

        # ---- 1. Ctrl+C ----
        if os.name == 'nt':
            try:
                import ctypes
                CTRL_C_EVENT = 0
                kernel32 = ctypes.windll.kernel32
                if not silent:
                    self.append_output("Отправка Ctrl+C...\n")
                result = kernel32.GenerateConsoleCtrlEvent(CTRL_C_EVENT, pid)
                if not result:
                    if not silent:
                        self.append_output("Не удалось отправить Ctrl+C\n")
            except Exception as e:
                if not silent:
                    self.append_output(f"Ошибка при отправке Ctrl+C: {e}\n")

        # Ожидаем до 3 секунд
        for _ in range(6):
            time.sleep(0.5)
            if self.process.poll() is not None:
                break

        if self.process.poll() is not None:
            if not silent:
                self.append_output(f"✅ Процесс cmd остановлен (код: {self.process.returncode})\n")
            self.kill_all_llama_servers(silent)
            self.reset_buttons()
            if not silent:
                self.append_output("💾 Модель выгружена из памяти\n")
                self.append_output("="*50 + "\n")
            self.cleanup_temp_files()
            return

        # ---- 2. terminate ----
        if not silent:
            self.append_output("Завершение через terminate()...\n")
        self.process.terminate()
        for _ in range(4):
            time.sleep(0.5)
            if self.process.poll() is not None:
                break

        if self.process.poll() is not None:
            if not silent:
                self.append_output(f"✅ Процесс cmd остановлен (код: {self.process.returncode})\n")
            self.kill_all_llama_servers(silent)
            self.reset_buttons()
            if not silent:
                self.append_output("💾 Модель выгружена из памяти\n")
                self.append_output("="*50 + "\n")
            self.cleanup_temp_files()
            return

        # ---- 3. taskkill /F по PID ----
        if os.name == 'nt':
            if not silent:
                self.append_output("Принудительное завершение cmd через taskkill...\n")
            try:
                subprocess.run(f'taskkill /F /T /PID {pid}', shell=True, capture_output=True, timeout=5)
                time.sleep(1)
                if self.process.poll() is not None:
                    if not silent:
                        self.append_output(f"✅ Процесс cmd остановлен\n")
                    self.kill_all_llama_servers(silent)
                    self.reset_buttons()
                    if not silent:
                        self.append_output("💾 Модель выгружена из памяти\n")
                        self.append_output("="*50 + "\n")
                    self.cleanup_temp_files()
                    return
            except Exception as e:
                if not silent:
                    self.append_output(f"Ошибка taskkill: {e}\n")

        # ---- 4. Финал: убить все процессы llama-server.exe ----
        self.kill_all_llama_servers(silent)
        self.reset_buttons()
        if not silent:
            self.append_output("💾 Модель выгружена из памяти\n")
            self.append_output("="*50 + "\n")
        self.cleanup_temp_files()
    
    def cleanup_temp_files(self):
        """Удаляет временный BAT файл, если он существует"""
        if self.bat_file and os.path.exists(self.bat_file):
            try:
                os.remove(self.bat_file)
            except Exception as e:
                print(f"Не удалось удалить {self.bat_file}: {e}")
    
    def on_closing(self):
        """Обработчик закрытия окна с подтверждением, если сервер запущен"""
        if self.process and self.process.poll() is None:
            if messagebox.askyesno("Подтверждение", "Сервер запущен. Остановить и закрыть приложение?"):
                self.stop_model(silent=True)
                self.cleanup_temp_files()
                self.root.destroy()
        else:
            self.cleanup_temp_files()
            self.root.destroy()
    
    def reset_buttons(self):
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.process = None
        self.running = False
        self.update_start_button_text()
        self.cleanup_temp_files()

def hide_console():
    """Полностью отключает консоль у текущего процесса Windows"""
    if os.name == 'nt':
        try:
            import ctypes
            ctypes.windll.kernel32.FreeConsole()
        except:
            pass

def main():
    hide_console()
    root = tk.Tk()
    app = LlamaGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()