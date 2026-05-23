import tkinter as tk
from tkinter import ttk
import numpy as np
from scipy.stats import poisson
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

class PoissonApp:
    def __init__(self, main):
        self.main = main
        self.main.title("Моделирование пуассоновского потока заявок")
        self.params = ttk.LabelFrame(main, text="Параметры")
        self.params.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)
        self.lambda_var = self.add_spin("Интенсивность потока λ:", 0.1, 20, 0.1, 3.0)
        self.T_var = self.add_spin("Интервал наблюдения T:", 0.1, 50, 0.5, 5.0)
        self.N_var = self.add_spin("Число экспериментов N:", 100, 100000, 100, 10000)
        self.table = ttk.Treeview(self.params, columns=("lambda", "T", "N", "mean_emp", "mean_th", "var_emp", "var_th"), show="headings", height=6)
        columns_info = [
            ("lambda", "λ", 40),
            ("T", "T", 40),
            ("N", "N", 60),
            ("mean_emp", "M эмп.", 70),
            ("mean_th", "M теор.", 70),
            ("var_emp", "D эмп.", 70),
            ("var_th", "D теор.", 70),
        ]
        for col, text, width in columns_info:
            self.table.heading(col, text=text)
            self.table.column(col, width=width, anchor="center", stretch=False)
        self.table.pack(pady=10, padx=4)
        buttons_frame = ttk.Frame(self.params)
        buttons_frame.pack(fill="x", pady=5, padx=4)
        ttk.Button(buttons_frame, text="Запустить", command=self.run_simulation).pack(fill="x", pady=2)
        ttk.Button(buttons_frame, text="Очистить", command=self.clear_all).pack(fill="x", pady=2)
        ttk.Button(buttons_frame, text="Закрыть", command=self.main.destroy).pack(fill="x", pady=2)
        self.fig, self.ax = plt.subplots(figsize=(7, 5))
        self.ax.set_xlabel("Число заявок k")
        self.ax.set_ylabel("Вероятность P(X = k)")
        self.ax.set_title("Распределение числа заявок")
        self.ax.grid(axis="y", linestyle="--", alpha=0.4)
        self.canvas = FigureCanvasTkAgg(self.fig, master=main)
        self.canvas.get_tk_widget().pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

    def add_spin(self, label, start, end, step, default):
        ttk.Label(self.params, text=label).pack(anchor="w", padx=4)
        var = tk.DoubleVar(value=default)
        ttk.Spinbox(self.params, from_=start, to=end, increment=step, textvariable=var).pack(fill="x", padx=4, pady=2)
        return var

    def simulate_poisson_stream(self, lam, t_end):
        count = 0
        t = 0.0
        while True:
            t += np.random.exponential(1.0 / lam)
            if t > t_end:
                break
            count += 1
        return count

    def run_simulation(self):
        lam = self.lambda_var.get()
        T = self.T_var.get()
        N = int(self.N_var.get())
        np.random.seed(42)
        counts = np.array([self.simulate_poisson_stream(lam, T) for _ in range(N)])
        mean_emp = np.mean(counts)
        var_emp = np.var(counts, ddof=1)
        mean_th = lam * T
        var_th = lam * T
        self.table.insert("", tk.END, values=(f"{lam}", f"{T}", f"{N}", f"{mean_emp:.3f}", f"{mean_th:.3f}", f"{var_emp:.3f}", f"{var_th:.3f}"))
        k_vals = np.arange(counts.min(), counts.max() + 1)
        freq = np.array([(counts == k).sum() / N for k in k_vals])
        theory_pmf = poisson.pmf(k_vals, mu=lam * T)
        self.ax.bar(k_vals, freq, width=0.6, alpha=0.75, label=f"Эмп. λ={lam} T={T}")
        self.ax.plot(k_vals, theory_pmf, marker="o", linewidth=2, markersize=4, label=f"Теор. λ={lam} T={T}")
        self.ax.legend(fontsize=9)
        self.ax.xaxis.set_major_locator(plt.MaxNLocator(integer=True, nbins=20))
        self.ax.relim()
        self.ax.autoscale_view()
        self.canvas.draw()

    def clear_all(self):
        for row in self.table.get_children():
            self.table.delete(row)
        self.ax.cla()
        self.ax.set_xlabel("Число заявок k")
        self.ax.set_ylabel("Вероятность P(X = k)")
        self.ax.set_title("Распределение числа заявок")
        self.ax.grid(axis="y", linestyle="--", alpha=0.4)
        self.canvas.draw()

if __name__ == "__main__":
    main = tk.Tk()
    app = PoissonApp(main)
    main.mainloop()