import tkinter as tk
from tkinter import ttk
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

def mcg(n, seed=42, a=2 ** 32 + 3, m=2 ** 63):
    x = seed % m
    res = []
    for _ in range(n):
        x = (a * x) % m
        res.append(x / m)
    return np.array(res)

def fibonacci_gen(n, seed=42, m=2 ** 63):
    res = []
    x_prev2 = seed % m
    x_prev1 = (seed + 1) % m

    for _ in range(n):
        x_new = (x_prev1 + x_prev2) % m
        res.append(x_new / m)
        x_prev2 = x_prev1
        x_prev1 = x_new
    return np.array(res)

class RandomApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Базовый датчик случайных чисел")

        self.params_frame = ttk.LabelFrame(root, text="Параметры")
        self.params_frame.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)

        self.n_var = tk.IntVar(value=10000)
        self.seed_var = tk.IntVar(value=42)
        self.add_spin("Размер выборки (N)", self.n_var, 1000, 1000000, 1000)
        self.add_spin("Seed", self.seed_var, 1, 2147483646, 1)

        columns = ("Метрика", "MCG", "Фибоначчи", "Встроенный", "Теория")
        self.table = ttk.Treeview(self.params_frame, columns=columns, show="headings", height=6)
        for col in columns:
            self.table.heading(col, text=col)
            self.table.column(col, width=75, anchor="center")
        self.table.pack(pady=5)

        btn_frame = ttk.Frame(self.params_frame)
        btn_frame.pack(fill="x", pady=10)
        ttk.Button(btn_frame, text="Сгенерировать", command=self.run).pack(fill="x", pady=2)
        ttk.Button(btn_frame, text="Очистить", command=self.clear).pack(fill="x", pady=2)
        ttk.Button(btn_frame, text="Закрыть", command=self.close_app).pack(fill="x", pady=2)

        self.right_frame = ttk.Frame(root)
        self.right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self.fig, self.ax = plt.subplots(figsize=(6, 5))
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.right_frame)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

    def close_app(self):
        plt.close(self.fig)
        self.root.quit()

    def add_spin(self, label, var, start, end, step):
        ttk.Label(self.params_frame, text=label).pack(anchor="w")
        ttk.Spinbox(self.params_frame, from_=start, to=end, increment=step, textvariable=var).pack(fill="x", pady=2)

    def sample_stats(self, sample):
        return {"Среднее": np.mean(sample), "Дисперсия": np.var(sample)}

    def run(self):
        N = self.n_var.get()
        seed = self.seed_var.get()

        mcg_sample = mcg(N, seed)
        fib_sample = fibonacci_gen(N, seed)
        np.random.seed(seed)
        builtin_sample = np.random.random(N)

        mcg_stats = self.sample_stats(mcg_sample)
        fib_stats = self.sample_stats(fib_sample)
        builtin_stats = self.sample_stats(builtin_sample)

        theory_stats = {"Среднее": 0.5, "Дисперсия": 1 / 12}

        for row in self.table.get_children():
            self.table.delete(row)
        for key in mcg_stats.keys():
            self.table.insert("", "end", values=(
            key, f"{mcg_stats[key]:.5f}", f"{fib_stats[key]:.5f}", f"{builtin_stats[key]:.5f}",
            f"{theory_stats[key]:.5f}"))

        self.ax.clear()
        self.ax.hist(mcg_sample, bins=50, alpha=0.4, label="MCG", color='skyblue', edgecolor='black', linewidth=0.5)
        self.ax.hist(fib_sample, bins=50, alpha=0.4, label="Фибоначчи", color='salmon', edgecolor='black',
                     linewidth=0.5)
        self.ax.hist(builtin_sample, bins=50, alpha=0.4, label="Встроенный", color='lightgreen', edgecolor='black',
                     linewidth=0.5)

        self.ax.set_title("Сравнение гистограмм")
        self.ax.set_xlabel("Значение")
        self.ax.set_ylabel("Частота")
        self.ax.legend(loc='lower center', bbox_to_anchor=(0.5, -0.25), ncol=3, fontsize=8)
        self.fig.tight_layout()
        self.canvas.draw()

    def clear(self):
        for row in self.table.get_children():
            self.table.delete(row)
        self.ax.clear()
        self.canvas.draw()

if __name__ == "__main__":
    root = tk.Tk()
    app = RandomApp(root)
    root.mainloop()
