import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
import subprocess
import os
import threading
import shlex
import time
import sys

class LlamaGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("LLaMA GUI Launcher")
        self.root.geometry("900x750")
        
        # Переменные
        self.model_path = tk.StringVar()
        self.process = None
        self.bat_file = None
        
        # Параметры модели
        self.ncmoe = tk.StringVar(value="25")
        self.ngl = tk.StringVar(value="99")
        self.context = tk.StringVar(value="265000")
        self.temp = tk.StringVar(value="0.1")
        self.flash_attn = tk.BooleanVar(value=True)
        self.threads = tk.StringVar(value="16")
        self.reasoning_budget = tk.StringVar(value="0")
        self.system_prompt = tk.StringVar(value="Ты полезный помощник. Отвечай на русском языке.")
        
        # Скрываем консоль Python при запуске (для Windows)
        if os.name == 'nt':
            self.hide_console()
        
        # Интерфейс
        self.create_widgets()
    
    def hide_console(self):
        """Скрывает окно консоли Python"""
        try:
            import ctypes
            # Получаем handle текущего окна консоли
            kernel32 = ctypes.windll.kernel32
            user32 = ctypes.windll.user32
            
            # Скрываем окно консоли
            hwnd = kernel32.GetConsoleWindow()
            if hwnd:
                user32.ShowWindow(hwnd, 0)  # 0 = SW_HIDE
        except:
            pass
    
    def create_widgets(self):
        # Рамка выбора файла
        file_frame = tk.LabelFrame(self.root, text="Выбор модели GGUF", padx=5, pady=5)
        file_frame.pack(fill="x", padx=10, pady=5)
        
        tk.Entry(file_frame, textvariable=self.model_path, width=80).pack(side="left", padx=5, fill="x", expand=True)
        tk.Button(file_frame, text="Обзор...", command=self.browse_file).pack(side="left", padx=5)
        
        # Рамка параметров модели
        params_frame = tk.LabelFrame(self.root, text="Параметры модели", padx=10, pady=10)
        params_frame.pack(fill="x", padx=10, pady=5)
        
        # Создаем сетку для параметров
        row = 0
        
        # Параметр -ncmoe (Number of experts to use for MoE)
        tk.Label(params_frame, text="MoE экспертов (-ncmoe):", width=20, anchor="w").grid(row=row, column=0, padx=5, pady=5, sticky="w")
        tk.Entry(params_frame, textvariable=self.ncmoe, width=15).grid(row=row, column=1, padx=5, pady=5, sticky="w")
        tk.Label(params_frame, text="Количество экспертов для Mixture of Experts", fg="gray").grid(row=row, column=2, padx=5, pady=5, sticky="w")
        row += 1
        
        # Параметр -ngl (GPU layers)
        tk.Label(params_frame, text="Слои на GPU (-ngl):", width=20, anchor="w").grid(row=row, column=0, padx=5, pady=5, sticky="w")
        tk.Entry(params_frame, textvariable=self.ngl, width=15).grid(row=row, column=1, padx=5, pady=5, sticky="w")
        tk.Label(params_frame, text="Количество слоев для загрузки на GPU (-1 = все)", fg="gray").grid(row=row, column=2, padx=5, pady=5, sticky="w")
        row += 1
        
        # Параметр -c (Context size)
        tk.Label(params_frame, text="Размер контекста (-c):", width=20, anchor="w").grid(row=row, column=0, padx=5, pady=5, sticky="w")
        tk.Entry(params_frame, textvariable=self.context, width=15).grid(row=row, column=1, padx=5, pady=5, sticky="w")
        tk.Label(params_frame, text="Максимальная длина контекста", fg="gray").grid(row=row, column=2, padx=5, pady=5, sticky="w")
        row += 1
        
        # Параметр --temp (Temperature)
        tk.Label(params_frame, text="Температура (--temp):", width=20, anchor="w").grid(row=row, column=0, padx=5, pady=5, sticky="w")
        temp_scale = tk.Scale(params_frame, from_=0.0, to=2.0, resolution=0.01, orient=tk.HORIZONTAL, 
                              variable=self.temp, length=200)
        temp_scale.grid(row=row, column=1, padx=5, pady=5, sticky="w")
        tk.Label(params_frame, textvariable=self.temp, width=5).grid(row=row, column=2, padx=5, pady=5, sticky="w")
        tk.Label(params_frame, text="Креативность (0=детерминировано, 2=случайно)", fg="gray").grid(row=row, column=3, padx=5, pady=5, sticky="w")
        row += 1
        
        # Параметр --flash-attn
        tk.Label(params_frame, text="Flash Attention:", width=20, anchor="w").grid(row=row, column=0, padx=5, pady=5, sticky="w")
        tk.Checkbutton(params_frame, variable=self.flash_attn).grid(row=row, column=1, padx=5, pady=5, sticky="w")
        tk.Label(params_frame, text="Использовать Flash Attention (ускоряет обработку)", fg="gray").grid(row=row, column=2, padx=5, pady=5, sticky="w")
        row += 1
        
        # Параметр -t (Threads)
        tk.Label(params_frame, text="Потоки (-t):", width=20, anchor="w").grid(row=row, column=0, padx=5, pady=5, sticky="w")
        threads_scale = tk.Scale(params_frame, from_=1, to=32, orient=tk.HORIZONTAL, 
                                variable=self.threads, length=200)
        threads_scale.grid(row=row, column=1, padx=5, pady=5, sticky="w")
        tk.Label(params_frame, textvariable=self.threads, width=5).grid(row=row, column=2, padx=5, pady=5, sticky="w")
        tk.Label(params_frame, text="Количество потоков CPU", fg="gray").grid(row=row, column=3, padx=5, pady=5, sticky="w")
        row += 1
        
        # Параметр --reasoning-budget
        tk.Label(params_frame, text="Бюджет рассуждений:", width=20, anchor="w").grid(row=row, column=0, padx=5, pady=5, sticky="w")
        tk.Entry(params_frame, textvariable=self.reasoning_budget, width=15).grid(row=row, column=1, padx=5, pady=5, sticky="w")
        tk.Label(params_frame, text="Лимит токенов для рассуждений (0 = отключено)", fg="gray").grid(row=row, column=2, padx=5, pady=5, sticky="w")
        row += 1
        
        # Параметр -sys (System prompt)
        tk.Label(params_frame, text="Системный промпт (-sys):", width=20, anchor="w").grid(row=row, column=0, padx=5, pady=5, sticky="nw")
        self.system_text = tk.Text(params_frame, height=4, width=60, wrap=tk.WORD)
        self.system_text.grid(row=row, column=1, columnspan=3, padx=5, pady=5, sticky="w")
        self.system_text.insert("1.0", self.system_prompt.get())
        row += 1
        
        # Дополнительные параметры
        extra_frame = tk.LabelFrame(self.root, text="Дополнительные параметры", padx=5, pady=5)
        extra_frame.pack(fill="x", padx=10, pady=5)
        
        tk.Label(extra_frame, text="Доп. параметры:").pack(anchor="w", padx=5)
        self.extra_params = tk.Text(extra_frame, height=3, width=80)
        self.extra_params.pack(fill="x", padx=5, pady=5)
        self.extra_params.insert("1.0", "--cache-type-k q8_0 --cache-type-v q8_0 -b 512 --jinja --color on")
        
        # Кнопки управления
        control_frame = tk.Frame(self.root)
        control_frame.pack(fill="x", padx=10, pady=10)
        
        self.start_btn = tk.Button(control_frame, text="Запустить модель", command=self.start_model, 
                                   bg="green", fg="white", font=("Arial", 10, "bold"), padx=20)
        self.start_btn.pack(side="left", padx=5)
        
        self.stop_btn = tk.Button(control_frame, text="Остановить", command=self.stop_model, 
                                  bg="red", fg="white", state="disabled", font=("Arial", 10, "bold"), padx=20)
        self.stop_btn.pack(side="left", padx=5)
        
        # Кнопка для отображения полной команды
        self.show_cmd_btn = tk.Button(control_frame, text="Показать команду", command=self.show_command,
                                      bg="blue", fg="white", font=("Arial", 10))
        self.show_cmd_btn.pack(side="left", padx=5)
        
        # Консоль вывода
        output_frame = tk.LabelFrame(self.root, text="Вывод программы", padx=5, pady=5)
        output_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        self.output_text = scrolledtext.ScrolledText(output_frame, height=15, wrap=tk.WORD)
        self.output_text.pack(fill="both", expand=True)
        
    def browse_file(self):
        filename = filedialog.askopenfilename(
            title="Выберите GGUF файл модели",
            filetypes=[("GGUF files", "*.gguf"), ("All files", "*.*")]
        )
        if filename:
            self.model_path.set(filename)
    
    def build_command(self):
        """Собирает команду из параметров"""
        model = self.model_path.get().strip()
        if not model:
            return None
        
        # Базовые параметры
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
            params.append("--flash-attn")
            params.append("on")
        
        if self.threads.get().strip():
            params.extend(["-t", self.threads.get().strip()])
        
        if self.reasoning_budget.get().strip():
            params.extend(["--reasoning-budget", self.reasoning_budget.get().strip()])
        
        # Системный промпт
        system_text = self.system_text.get("1.0", tk.END).strip()
        if system_text:
            params.extend(["-sys", f'"{system_text}"'])
        
        # Дополнительные параметры
        extra_text = self.extra_params.get("1.0", tk.END).strip()
        if extra_text:
            try:
                extra_params = shlex.split(extra_text, posix=False)
                params.extend(extra_params)
            except:
                params.extend(extra_text.split())
        
        # Путь к модели в кавычках
        if ' ' in model:
            model_quoted = f'"{model}"'
        else:
            model_quoted = model
        
        return model_quoted, params
    
    def show_command(self):
        """Показывает полную команду в отдельном окне"""
        result = self.build_command()
        if not result:
            messagebox.showerror("Ошибка", "Выберите файл модели!")
            return
        
        model_quoted, params = result
        command_parts = [".\\llama-cli.exe", "-m", model_quoted] + params
        command_str = ' '.join(command_parts)
        
        # Создаем окно для отображения команды
        cmd_window = tk.Toplevel(self.root)
        cmd_window.title("Полная команда")
        cmd_window.geometry("800x200")
        
        tk.Label(cmd_window, text="Команда для выполнения:", font=("Arial", 10, "bold")).pack(pady=5)
        cmd_text = scrolledtext.ScrolledText(cmd_window, height=8, wrap=tk.WORD)
        cmd_text.pack(fill="both", expand=True, padx=10, pady=5)
        cmd_text.insert("1.0", command_str)
        
        tk.Button(cmd_window, text="Копировать в буфер", 
                 command=lambda: self.copy_to_clipboard(command_str, cmd_window)).pack(pady=5)
    
    def copy_to_clipboard(self, text, window):
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        messagebox.showinfo("Успех", "Команда скопирована в буфер обмена!")
        window.destroy()
    
    def append_output(self, text):
        """Добавить текст в консоль вывода"""
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
        
        # Определяем папку скрипта
        script_dir = os.path.dirname(os.path.abspath(__file__))
        llama_path = os.path.join(script_dir, "llama-cli.exe")
        
        if not os.path.exists(llama_path):
            import shutil
            llama_path = shutil.which("llama-cli.exe")
            if not llama_path:
                messagebox.showerror("Ошибка", "llama-cli.exe не найден!")
                return
            script_dir = os.path.dirname(llama_path)
        
        # Создаем BAT файл
        self.bat_file = os.path.join(script_dir, "llama_run_temp.bat")
        
        # Формируем команду
        if os.path.dirname(llama_path) == script_dir:
            llama_cmd = "llama-cli.exe"
        else:
            llama_cmd = f'"{llama_path}"'
        
        command_parts = [llama_cmd, "-m", model_quoted] + params
        command = ' '.join(command_parts)
        
        # Показываем команду
        self.append_output("="*50 + "\n")
        self.append_output(f"Рабочая папка: {script_dir}\n")
        self.append_output(f"Команда:\n{command}\n")
        self.append_output("="*50 + "\n\n")
        
        # Создаем BAT файл
        try:
            with open(self.bat_file, 'w', encoding='utf-8') as f:
                f.write('@echo off\n')
                f.write(f'title LLaMA Model\n')
                f.write('chcp 65001 >nul 2>&1\n')
                f.write(f'cd /d "{script_dir}"\n')
                f.write(f'echo Запуск LLaMA модели...\n')
                f.write(f'echo.\n')
                f.write(f'{command}\n')
                f.write(f'echo.\n')
                f.write(f'echo === Процесс завершен ===\n')
                f.write(f'echo Нажмите любую клавишу...\n')
                f.write(f'pause >nul\n')
                f.write(f'del /f /q "{self.bat_file}" 2>nul\n')
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось создать файл: {str(e)}")
            return
        
        # Запускаем
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        
        # Очищаем вывод перед запуском
        self.output_text.delete(1.0, tk.END)
        
        self.thread = threading.Thread(target=self.run_process, daemon=True)
        self.thread.start()
    
    def run_process(self):
        try:
            # Запускаем процесс с поддержкой STDIN для отправки команд
            # Используем CREATE_NO_WINDOW флаг для Windows
            creation_flags = 0
            if os.name == 'nt':
                creation_flags = subprocess.CREATE_NO_WINDOW  # 0x08000000 - не показывает окно
                # Также используем STARTF_USESHOWWINDOW для скрытия окна
            
            # Запускаем процесс
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
            
            self.append_output(f"Процесс запущен (PID: {self.process.pid})\n")
            self.append_output("Для остановки модели используйте кнопку 'Остановить'\n")
            self.append_output("Будет отправлена команда /exit для плавной выгрузки из памяти\n\n")
            
            # Читаем вывод в реальном времени
            def read_output():
                for line in iter(self.process.stdout.readline, ''):
                    if line:
                        self.append_output(line)
                self.process.stdout.close()
            
            # Запускаем чтение вывода в отдельном потоке
            output_thread = threading.Thread(target=read_output, daemon=True)
            output_thread.start()
            
            # Ждем завершения процесса
            self.process.wait()
            self.append_output(f"\nПроцесс завершён с кодом: {self.process.returncode}\n")
            
        except Exception as e:
            self.append_output(f"\nОшибка: {str(e)}\n")
        finally:
            self.root.after(0, self.reset_buttons)
    
    def stop_model(self):
        """Остановка модели с отправкой команды /exit"""
        if self.process and self.process.poll() is None:
            self.append_output("\n" + "="*50 + "\n")
            self.append_output("Остановка модели...\n")
            
            try:
                # Отправляем команду /exit в процесс
                if self.process.stdin:
                    self.append_output("Отправка команды /exit для плавной выгрузки модели из памяти...\n")
                    self.process.stdin.write('/exit\n')
                    self.process.stdin.flush()
                    self.append_output("Команда /exit отправлена. Модель выгружается из памяти...\n")
                    
                    # Даем время на плавное завершение
                    time.sleep(3)
                    
                    # Проверяем, завершился ли процесс
                    if self.process.poll() is None:
                        self.append_output("Ожидание завершения процесса...\n")
                        try:
                            self.process.wait(timeout=10)
                            self.append_output("Модель успешно выгружена из памяти\n")
                        except subprocess.TimeoutExpired:
                            self.append_output("Процесс не завершился вовремя, принудительное завершение...\n")
                            self.process.terminate()
                            try:
                                self.process.wait(timeout=3)
                            except subprocess.TimeoutExpired:
                                self.process.kill()
                                self.process.wait()
                            self.append_output("Процесс принудительно завершен\n")
                else:
                    # Если нет stdin, используем обычное завершение
                    self.append_output("Невозможно отправить команду /exit, выполняем принудительное завершение...\n")
                    self.process.terminate()
                    try:
                        self.process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        self.process.kill()
                        self.process.wait()
                    self.append_output("Процесс завершен\n")
                
                self.append_output("="*50 + "\n")
                
            except Exception as e:
                self.append_output(f"Ошибка при остановке: {str(e)}\n")
                try:
                    self.process.kill()
                    self.process.wait()
                    self.append_output("Процесс принудительно завершен\n")
                except:
                    self.append_output("Не удалось завершить процесс\n")
        else:
            self.append_output("Нет активного процесса для остановки\n")
    
    def reset_buttons(self):
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
        self.process = None

def main():
    # Скрываем консоль при запуске через pythonw.exe
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
