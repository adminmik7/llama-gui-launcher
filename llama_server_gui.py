import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
import subprocess
import os
import threading
import shlex
import time
import sys

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

class LlamaGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("LLaMA GUI Server Launcher")
        self.root.geometry("850x680")
        self.root.minsize(750, 600)
        self.root.configure(bg="#f5f5f5")
        
        # Переменные
        self.model_path = tk.StringVar()
        self.port = tk.StringVar(value="1515")
        self.host = tk.StringVar(value="127.0.0.1")
        self.process = None
        self.bat_file = None
        
        # Параметры модели
        self.ngl = tk.StringVar(value="99")
        self.context = tk.StringVar(value="32000")
        self.temp = tk.StringVar(value="0.8")
        self.threads = tk.StringVar(value="16")
        self.batch = tk.StringVar(value="512")
        self.cache_type_k = tk.StringVar(value="q8_0")
        self.cache_type_v = tk.StringVar(value="q8_0")
        self.parallel_slots = tk.StringVar(value="2")
        
        # Стили
        self.setup_styles()
        
        if os.name == 'nt':
            self.hide_console()
        
        self.create_widgets()
    
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
    
    def hide_console(self):
        try:
            import ctypes
            ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)
        except:
            pass
    
    def create_widgets(self):
        main = ttk.Frame(self.root, padding="12")
        main.pack(fill=tk.BOTH, expand=True)
        
        # Заголовок
        header = ttk.Frame(main)
        header.pack(fill=tk.X, pady=(0, 12))
        ttk.Label(header, text="🦙 LLaMA GUI Server Launcher", font=('Segoe UI', 14, 'bold')).pack()
        
        # === Модель ===
        model_frame = ttk.LabelFrame(main, text="Модель", padding="8")
        model_frame.pack(fill=tk.X, pady=(0, 12))
        
        model_row = ttk.Frame(model_frame)
        model_row.pack(fill=tk.X)
        self.model_entry = ttk.Entry(model_row, textvariable=self.model_path)
        self.model_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))
        ttk.Button(model_row, text="Обзор", command=self.browse_file, width=8).pack(side=tk.RIGHT)
        ToolTip(self.model_entry, "Путь к GGUF файлу модели")
        
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
        ToolTip(port_entry, "Порт для HTTP API (по умолчанию 1515)")
        
        ttk.Label(server_row, text="Слоты:").pack(side=tk.LEFT, padx=(0, 5))
        slots_entry = ttk.Entry(server_row, textvariable=self.parallel_slots, width=4)
        slots_entry.pack(side=tk.LEFT)
        ToolTip(slots_entry, "Количество параллельных сессий (-np, по умолчанию 2)")
        
        # === Параметры модели ===
        params_frame = ttk.LabelFrame(main, text="Параметры модели", padding="8")
        params_frame.pack(fill=tk.X, pady=(0, 12))
        
        params_inner = ttk.Frame(params_frame)
        params_inner.pack(fill=tk.X)
        
        # Заголовки
        ttk.Label(params_inner, text="ngl", font=('Consolas', 9, 'bold'), width=12, anchor=tk.W).grid(row=0, column=0, padx=(0, 15), pady=(0, 2), sticky=tk.W)
        ttk.Label(params_inner, text="c", font=('Consolas', 9, 'bold'), width=12, anchor=tk.W).grid(row=0, column=1, padx=(0, 15), pady=(0, 2), sticky=tk.W)
        ttk.Label(params_inner, text="temp", font=('Consolas', 9, 'bold'), width=12, anchor=tk.W).grid(row=0, column=2, padx=0, pady=(0, 2), sticky=tk.W)
        
        # Поля ввода
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
        
        # Подписи
        ttk.Label(params_inner, text="GPU слои", font=('Segoe UI', 7), foreground="#888").grid(row=2, column=0, padx=(0, 15), sticky=tk.W)
        ttk.Label(params_inner, text="Размер контекста", font=('Segoe UI', 7), foreground="#888").grid(row=2, column=1, padx=(0, 15), sticky=tk.W)
        ttk.Label(params_inner, text="Температура", font=('Segoe UI', 7), foreground="#888").grid(row=2, column=2, padx=0, sticky=tk.W)
        
        ToolTip(ngl_entry, "Количество слоев на GPU (-1 = все)")
        ToolTip(ctx_entry, "Максимальная длина контекста (по умолчанию 32000)")
        ToolTip(temp_scale, "Креативность ответов (по умолчанию 0.8)")
        
        # Второй ряд параметров (t, b, кэш)
        ttk.Label(params_inner, text="t", font=('Consolas', 9, 'bold'), width=12, anchor=tk.W).grid(row=3, column=0, padx=(0, 15), pady=(8, 2), sticky=tk.W)
        ttk.Label(params_inner, text="b", font=('Consolas', 9, 'bold'), width=12, anchor=tk.W).grid(row=3, column=1, padx=(0, 15), pady=(8, 2), sticky=tk.W)
        ttk.Label(params_inner, text="cache", font=('Consolas', 9, 'bold'), width=12, anchor=tk.W).grid(row=3, column=2, padx=0, pady=(8, 2), sticky=tk.W)
        
        # t (потоки)
        threads_frame = ttk.Frame(params_inner)
        threads_frame.grid(row=4, column=0, padx=(0, 15), pady=(0, 2), sticky=tk.W)
        threads_scale = tk.Scale(threads_frame, from_=1, to=32, orient=tk.HORIZONTAL, 
                                  variable=self.threads, length=100, bg="#f5f5f5", fg="#333",
                                  highlightthickness=0, troughcolor="#ddd")
        threads_scale.pack(side=tk.LEFT)
        threads_label = ttk.Label(threads_frame, textvariable=self.threads, width=4, font=('Consolas', 8))
        threads_label.pack(side=tk.LEFT, padx=(5, 0))
        
        # b (batch size)
        batch_entry = ttk.Entry(params_inner, textvariable=self.batch, width=12)
        batch_entry.grid(row=4, column=1, padx=(0, 15), pady=(0, 2), sticky=tk.W)
        
        # cache type (k и v одинаковые)
        cache_frame = ttk.Frame(params_inner)
        cache_frame.grid(row=4, column=2, padx=0, pady=(0, 2), sticky=tk.W)
        ttk.Label(cache_frame, text="k:").pack(side=tk.LEFT)
        k_entry = ttk.Entry(cache_frame, textvariable=self.cache_type_k, width=5)
        k_entry.pack(side=tk.LEFT, padx=(2, 5))
        ttk.Label(cache_frame, text="v:").pack(side=tk.LEFT)
        v_entry = ttk.Entry(cache_frame, textvariable=self.cache_type_v, width=5)
        v_entry.pack(side=tk.LEFT, padx=(2, 0))
        
        # Подписи
        ttk.Label(params_inner, text="Потоки CPU", font=('Segoe UI', 7), foreground="#888").grid(row=5, column=0, padx=(0, 15), sticky=tk.W)
        ttk.Label(params_inner, text="Размер батча", font=('Segoe UI', 7), foreground="#888").grid(row=5, column=1, padx=(0, 15), sticky=tk.W)
        ttk.Label(params_inner, text="Тип кэша K/V", font=('Segoe UI', 7), foreground="#888").grid(row=5, column=2, padx=0, sticky=tk.W)
        
        ToolTip(threads_scale, "Количество потоков CPU")
        ToolTip(batch_entry, "Размер батча для обработки")
        ToolTip(k_entry, "Тип кэша для ключей (q8_0, f16 и др.)")
        ToolTip(v_entry, "Тип кэша для значений")
        
        # === Дополнительные аргументы ===
        extra_frame = ttk.LabelFrame(main, text="Дополнительные аргументы", padding="6")
        extra_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.extra_params = tk.Text(extra_frame, height=2, wrap=tk.WORD, font=('Consolas', 9), 
                                     borderwidth=1, relief=tk.SOLID, bg="white")
        self.extra_params.pack(fill=tk.X)
        self.extra_params.insert("1.0", "--jinja --color on")
        ToolTip(self.extra_params, "Дополнительные аргументы командной строки для сервера")
        
        # === Кнопки ===
        btn_frame = ttk.Frame(main)
        btn_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.start_btn = ttk.Button(btn_frame, text="Запустить", command=self.start_model, width=10)
        self.start_btn.pack(side=tk.LEFT, padx=(0, 6))
        
        self.stop_btn = ttk.Button(btn_frame, text="Остановить", command=self.stop_model, width=10, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=(0, 6))
        
        ttk.Button(btn_frame, text="Команда", command=self.show_command, width=10).pack(side=tk.LEFT)
        
        # === Вывод ===
        output_frame = ttk.LabelFrame(main, text="Вывод", padding="6")
        output_frame.pack(fill=tk.BOTH, expand=True)
        
        self.output_text = tk.Text(output_frame, height=10, wrap=tk.WORD, font=('Consolas', 9), 
                                    borderwidth=1, relief=tk.SOLID, bg="#1e1e1e", fg="#d4d4d4")
        self.output_text.pack(fill=tk.BOTH, expand=True)
        
        scroll = ttk.Scrollbar(self.output_text, orient=tk.VERTICAL, command=self.output_text.yview)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.output_text.configure(yscrollcommand=scroll.set)
    
    def browse_file(self):
        filename = filedialog.askopenfilename(
            title="Выберите GGUF файл модели",
            filetypes=[("GGUF files", "*.gguf"), ("All files", "*.*")]
        )
        if filename:
            self.model_path.set(filename)
    
    def build_command(self):
        model = self.model_path.get().strip()
        if not model:
            return None
        
        params = []
        
        # Параметры сервера
        params.extend(["--host", self.host.get().strip()])
        params.extend(["--port", self.port.get().strip()])
        
        if self.parallel_slots.get().strip():
            params.extend(["-np", self.parallel_slots.get().strip()])
        
        # Параметры модели
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
        
        # Дополнительные параметры
        extra_text = self.extra_params.get("1.0", tk.END).strip()
        if extra_text:
            try:
                extra_params = shlex.split(extra_text, posix=False)
                params.extend(extra_params)
            except:
                params.extend(extra_text.split())
        
        model_quoted = f'"{model}"' if ' ' in model else model
        return model_quoted, params
    
    def show_command(self):
        result = self.build_command()
        if not result:
            messagebox.showerror("Ошибка", "Выберите файл модели!")
            return
        
        model_quoted, params = result
        command_parts = ["llama-server.exe", "-m", model_quoted] + params
        command_str = ' '.join(command_parts)
        
        cmd_window = tk.Toplevel(self.root)
        cmd_window.title("Команда")
        cmd_window.geometry("750x180")
        cmd_window.configure(bg="#f5f5f5")
        
        ttk.Label(cmd_window, text="Команда для выполнения:", font=('Segoe UI', 10, 'bold')).pack(pady=8)
        
        cmd_text = tk.Text(cmd_window, height=5, wrap=tk.WORD, font=('Consolas', 9), borderwidth=1, relief=tk.SOLID)
        cmd_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        cmd_text.insert("1.0", command_str)
        
        ttk.Button(cmd_window, text="Копировать", command=lambda: self.copy_command(command_str, cmd_window)).pack(pady=8)
    
    def copy_command(self, text, window):
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        messagebox.showinfo("Успех", "Команда скопирована")
        window.destroy()
    
    def append_output(self, text):
        self.output_text.insert(tk.END, text)
        self.output_text.see(tk.END)
        self.root.update_idletasks()
    
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
        
        # Ищем llama-server.exe
        script_dir = os.path.dirname(os.path.abspath(__file__))
        server_path = os.path.join(script_dir, "llama-server.exe")
        
        if not os.path.exists(server_path):
            import shutil
            server_path = shutil.which("llama-server.exe")
            if not server_path:
                messagebox.showerror("Ошибка", "llama-server.exe не найден! Загрузите его с GitHub llama.cpp")
                return
            script_dir = os.path.dirname(server_path)
        
        # Создаем BAT файл
        self.bat_file = os.path.join(script_dir, "llama_server_temp.bat")
        server_cmd = "llama-server.exe" if os.path.dirname(server_path) == script_dir else f'"{server_path}"'
        
        command_parts = [server_cmd, "-m", model_quoted] + params
        command = ' '.join(command_parts)
        
        self.append_output("─" * 50 + "\n")
        self.append_output(f"Запуск сервера для: {os.path.basename(model)}\n")
        self.append_output(f"API будет доступно по адресу: http://{self.host.get()}:{self.port.get()}\n")
        self.append_output(f"Параллельных слотов: {self.parallel_slots.get()}\n")
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
                f.write('echo Нажмите любую клавишу...\n')
                f.write('pause >nul\n')
                f.write(f'del /f /q "{self.bat_file}" 2>nul\n')
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))
            return
        
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.output_text.delete(1.0, tk.END)
        
        self.thread = threading.Thread(target=self.run_process, daemon=True)
        self.thread.start()
    
    def run_process(self):
        try:
            creation_flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            
            self.process = subprocess.Popen(
                [self.bat_file],
                shell=True,
                creationflags=creation_flags,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
            
            self.append_output(f"✅ Сервер запущен (PID: {self.process.pid})\n")
            self.append_output(f"🌐 Адрес API: http://{self.host.get()}:{self.port.get()}\n")
            self.append_output(f"📖 Документация: http://{self.host.get()}:{self.port.get()}/docs\n")
            self.append_output(f"🔄 Параллельных слотов: {self.parallel_slots.get()}\n")
            self.append_output("\n🛑 Для остановки нажмите 'Остановить'\n\n")
            
            def read_output():
                for line in iter(self.process.stdout.readline, ''):
                    if line:
                        self.append_output(line)
                self.process.stdout.close()
            
            output_thread = threading.Thread(target=read_output, daemon=True)
            output_thread.start()
            
            self.process.wait()
            self.append_output(f"\n✅ Сервер остановлен (код: {self.process.returncode})\n")
            
        except Exception as e:
            self.append_output(f"\n❌ Ошибка: {str(e)}\n")
        finally:
            self.root.after(0, self.reset_buttons)
    
    def stop_model(self):
        if self.process and self.process.poll() is None:
            self.append_output("\n🛑 Остановка сервера...\n")
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
                if self.process.poll() is None:
                    self.process.kill()
                    self.process.wait()
                self.append_output("✅ Сервер остановлен\n")
            except Exception as e:
                self.append_output(f"❌ Ошибка: {str(e)}\n")
        else:
            self.append_output("ℹ️ Нет активного сервера\n")
    
    def reset_buttons(self):
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.process = None

def main():
    if os.name == 'nt':
        try:
            import ctypes
            ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)
        except:
            pass
    
    root = tk.Tk()
    app = LlamaGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
