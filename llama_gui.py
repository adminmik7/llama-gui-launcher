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
        self.root.title("LLaMA GUI Launcher")
        self.root.geometry("850x620")
        self.root.minsize(750, 550)
        self.root.configure(bg="#f5f5f5")
        
        # Переменные
        self.model_path = tk.StringVar()
        self.process = None
        self.bat_file = None
        
        # Параметры модели
        self.ncmoe = tk.StringVar(value="25")
        self.ngl = tk.StringVar(value="99")
        self.context = tk.StringVar(value="265000")
        self.temp = tk.StringVar(value="0.6")
        self.flash_attn = tk.BooleanVar(value=True)
        self.threads = tk.StringVar(value="16")
        self.reasoning_budget = tk.StringVar(value="0")
        
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
        ttk.Label(header, text="🦙 LLaMA GUI Launcher", font=('Segoe UI', 14, 'bold')).pack()
        
        # === Модель ===
        model_frame = ttk.LabelFrame(main, text="Модель", padding="8")
        model_frame.pack(fill=tk.X, pady=(0, 12))
        
        model_row = ttk.Frame(model_frame)
        model_row.pack(fill=tk.X)
        self.model_entry = ttk.Entry(model_row, textvariable=self.model_path)
        self.model_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))
        ttk.Button(model_row, text="Обзор", command=self.browse_file, width=8).pack(side=tk.RIGHT)
        ToolTip(self.model_entry, "Путь к GGUF файлу модели")
        
        # === Параметры (компактная сетка) ===
        params_frame = ttk.LabelFrame(main, text="Параметры", padding="8")
        params_frame.pack(fill=tk.X, pady=(0, 12))
        
        # Создаем таблицу 3x3 для параметров
        # Используем grid для точного позиционирования
        params_inner = ttk.Frame(params_frame)
        params_inner.pack(fill=tk.X)
        
        # Заголовки параметров (моноширинным шрифтом)
        ttk.Label(params_inner, text="ncmoe", font=('Consolas', 9, 'bold'), width=12, anchor=tk.W).grid(row=0, column=0, padx=(0, 15), pady=(0, 2), sticky=tk.W)
        ttk.Label(params_inner, text="ngl", font=('Consolas', 9, 'bold'), width=12, anchor=tk.W).grid(row=0, column=1, padx=(0, 15), pady=(0, 2), sticky=tk.W)
        ttk.Label(params_inner, text="c", font=('Consolas', 9, 'bold'), width=12, anchor=tk.W).grid(row=0, column=2, padx=0, pady=(0, 2), sticky=tk.W)
        
        # Поля ввода
        ncmoe_entry = ttk.Entry(params_inner, textvariable=self.ncmoe, width=12)
        ncmoe_entry.grid(row=1, column=0, padx=(0, 15), pady=(0, 2), sticky=tk.W)
        
        ngl_entry = ttk.Entry(params_inner, textvariable=self.ngl, width=12)
        ngl_entry.grid(row=1, column=1, padx=(0, 15), pady=(0, 2), sticky=tk.W)
        
        ctx_entry = ttk.Entry(params_inner, textvariable=self.context, width=12)
        ctx_entry.grid(row=1, column=2, padx=0, pady=(0, 2), sticky=tk.W)
        
        # Подписи
        ttk.Label(params_inner, text="MoE экспертов", font=('Segoe UI', 7), foreground="#888").grid(row=2, column=0, padx=(0, 15), sticky=tk.W)
        ttk.Label(params_inner, text="GPU слои", font=('Segoe UI', 7), foreground="#888").grid(row=2, column=1, padx=(0, 15), sticky=tk.W)
        ttk.Label(params_inner, text="Размер контекста", font=('Segoe UI', 7), foreground="#888").grid(row=2, column=2, padx=0, sticky=tk.W)
        
        ToolTip(ncmoe_entry, "Количество экспертов для MoE")
        ToolTip(ngl_entry, "Количество слоев на GPU")
        ToolTip(ctx_entry, "Максимальная длина контекста")
        
        # Второй ряд параметров (temp, t, reasoning-budget)
        ttk.Label(params_inner, text="temp", font=('Consolas', 9, 'bold'), width=12, anchor=tk.W).grid(row=3, column=0, padx=(0, 15), pady=(8, 2), sticky=tk.W)
        ttk.Label(params_inner, text="t", font=('Consolas', 9, 'bold'), width=12, anchor=tk.W).grid(row=3, column=1, padx=(0, 15), pady=(8, 2), sticky=tk.W)
        ttk.Label(params_inner, text="reasoning-budget", font=('Consolas', 9, 'bold'), width=12, anchor=tk.W).grid(row=3, column=2, padx=0, pady=(8, 2), sticky=tk.W)
        
        # temp с слайдером
        temp_frame = ttk.Frame(params_inner)
        temp_frame.grid(row=4, column=0, padx=(0, 15), pady=(0, 2), sticky=tk.W)
        temp_scale = tk.Scale(temp_frame, from_=0.0, to=2.0, resolution=0.01, orient=tk.HORIZONTAL, 
                               variable=self.temp, length=100, bg="#f5f5f5", fg="#333",
                               highlightthickness=0, troughcolor="#ddd", activebackground="#0078d4")
        temp_scale.pack(side=tk.LEFT)
        temp_label = ttk.Label(temp_frame, textvariable=self.temp, width=4, font=('Consolas', 8))
        temp_label.pack(side=tk.LEFT, padx=(5, 0))
        
        # t с слайдером
        threads_frame = ttk.Frame(params_inner)
        threads_frame.grid(row=4, column=1, padx=(0, 15), pady=(0, 2), sticky=tk.W)
        threads_scale = tk.Scale(threads_frame, from_=1, to=32, orient=tk.HORIZONTAL, 
                                  variable=self.threads, length=100, bg="#f5f5f5", fg="#333",
                                  highlightthickness=0, troughcolor="#ddd", activebackground="#0078d4")
        threads_scale.pack(side=tk.LEFT)
        threads_label = ttk.Label(threads_frame, textvariable=self.threads, width=4, font=('Consolas', 8))
        threads_label.pack(side=tk.LEFT, padx=(5, 0))
        
        # reasoning-budget
        budget_entry = ttk.Entry(params_inner, textvariable=self.reasoning_budget, width=12)
        budget_entry.grid(row=4, column=2, padx=0, pady=(0, 2), sticky=tk.W)
        
        # Подписи второго ряда
        ttk.Label(params_inner, text="Температура", font=('Segoe UI', 7), foreground="#888").grid(row=5, column=0, padx=(0, 15), sticky=tk.W)
        ttk.Label(params_inner, text="Потоки CPU", font=('Segoe UI', 7), foreground="#888").grid(row=5, column=1, padx=(0, 15), sticky=tk.W)
        ttk.Label(params_inner, text="Бюджет рассуждений", font=('Segoe UI', 7), foreground="#888").grid(row=5, column=2, padx=0, sticky=tk.W)
        
        ToolTip(temp_scale, "Креативность ответов (0=детерминировано, 2=случайно)")
        ToolTip(threads_scale, "Количество потоков CPU")
        ToolTip(budget_entry, "Лимит токенов для рассуждений (0=отключено)")
        
        # flash-attn (отдельная строка)
        flash_frame = ttk.Frame(params_inner)
        flash_frame.grid(row=6, column=0, columnspan=3, pady=(8, 0), sticky=tk.W)
        flash_check = ttk.Checkbutton(flash_frame, text="flash-attn (Flash Attention)", variable=self.flash_attn)
        flash_check.pack(anchor=tk.W)
        ToolTip(flash_check, "Ускоряет обработку внимания на GPU")
        
        # === Дополнительные аргументы ===
        extra_frame = ttk.LabelFrame(main, text="Дополнительные аргументы", padding="6")
        extra_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.extra_params = tk.Text(extra_frame, height=2, wrap=tk.WORD, font=('Consolas', 9), 
                                     borderwidth=1, relief=tk.SOLID, bg="white")
        self.extra_params.pack(fill=tk.X)
        self.extra_params.insert("1.0", "--cache-type-k q8_0 --cache-type-v q8_0 -b 512 --jinja --color on")
        ToolTip(self.extra_params, "Дополнительные аргументы командной строки")
        
        # === Системный промпт ===
        sys_frame = ttk.LabelFrame(main, text="Системный промпт", padding="6")
        sys_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.system_text = tk.Text(sys_frame, height=2, wrap=tk.WORD, font=('Segoe UI', 9), 
                                    borderwidth=1, relief=tk.SOLID, bg="white")
        self.system_text.pack(fill=tk.X)
        self.system_text.insert("1.0", "Ты полезный помощник. Отвечай на русском языке.")
        ToolTip(self.system_text, "Начальная инструкция для модели")
        
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
        
        if self.ncmoe.get().strip():
            params.extend(["-ncmoe", self.ncmoe.get().strip()])
        if self.ngl.get().strip():
            params.extend(["-ngl", self.ngl.get().strip()])
        if self.context.get().strip():
            params.extend(["-c", self.context.get().strip()])
        if self.temp.get().strip():
            params.extend(["--temp", self.temp.get().strip()])
        if self.flash_attn.get():
            params.extend(["--flash-attn", "on"])
        if self.threads.get().strip():
            params.extend(["-t", self.threads.get().strip()])
        if self.reasoning_budget.get().strip():
            params.extend(["--reasoning-budget", self.reasoning_budget.get().strip()])
        
        system_text = self.system_text.get("1.0", tk.END).strip()
        if system_text:
            params.extend(["-sys", f'"{system_text}"'])
        
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
        command_parts = [".\\llama-cli.exe", "-m", model_quoted] + params
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
        
        script_dir = os.path.dirname(os.path.abspath(__file__))
        llama_path = os.path.join(script_dir, "llama-cli.exe")
        
        if not os.path.exists(llama_path):
            import shutil
            llama_path = shutil.which("llama-cli.exe")
            if not llama_path:
                messagebox.showerror("Ошибка", "llama-cli.exe не найден!")
                return
            script_dir = os.path.dirname(llama_path)
        
        self.bat_file = os.path.join(script_dir, "llama_run_temp.bat")
        llama_cmd = "llama-cli.exe" if os.path.dirname(llama_path) == script_dir else f'"{llama_path}"'
        
        command_parts = [llama_cmd, "-m", model_quoted] + params
        command = ' '.join(command_parts)
        
        self.append_output("─" * 50 + "\n")
        self.append_output(f"Запуск: {os.path.basename(model)}\n")
        self.append_output("─" * 50 + "\n\n")
        
        try:
            with open(self.bat_file, 'w', encoding='utf-8') as f:
                f.write('@echo off\n')
                f.write('chcp 65001 >nul 2>&1\n')
                f.write(f'cd /d "{script_dir}"\n')
                f.write(f'{command}\n')
                f.write('echo.\n')
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
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
            )
            
            self.append_output(f"✅ Процесс запущен (PID: {self.process.pid})\n\n")
            
            def read_output():
                for line in iter(self.process.stdout.readline, ''):
                    if line:
                        self.append_output(line)
                self.process.stdout.close()
            
            output_thread = threading.Thread(target=read_output, daemon=True)
            output_thread.start()
            
            self.process.wait()
            self.append_output(f"\n✅ Завершён (код: {self.process.returncode})\n")
            
        except Exception as e:
            self.append_output(f"\n❌ Ошибка: {str(e)}\n")
        finally:
            self.root.after(0, self.reset_buttons)
    
    def stop_model(self):
        if self.process and self.process.poll() is None:
            self.append_output("\nОстановка...\n")
            
            try:
                if self.process.stdin:
                    self.process.stdin.write('/exit\n')
                    self.process.stdin.flush()
                    time.sleep(2)
                    
                    if self.process.poll() is None:
                        self.process.terminate()
                        self.process.wait(timeout=3)
                        if self.process.poll() is None:
                            self.process.kill()
                            self.process.wait()
                    
                    self.append_output("✅ Модель выгружена из памяти\n")
                else:
                    self.process.terminate()
                    self.process.wait()
            except Exception as e:
                self.append_output(f"Ошибка: {str(e)}\n")
        else:
            self.append_output("Нет активного процесса\n")
    
    def reset_buttons(self):
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.process = None

def main():
    root = tk.Tk()
    app = LlamaGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
