import tkinter as tk
from tkinter import ttk, messagebox
import math
import random
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np
from scipy import stats as scipy_stats

def generate_dsv(alpha: float, values: list, probs: list) -> float:
    A = alpha
    for k in range(len(probs)):
        A -= probs[k]
        if A <= 0:
            return values[k]
    return values[-1]

def generate_normal_bm() -> float:
    a1 = random.random()
    a2 = random.random()
    while a1 == 0:
        a1 = random.random()
    return math.sqrt(-2 * math.log(a1)) * math.cos(2 * math.pi * a2)

def generate_normal(mean: float, variance: float) -> float:
    return math.sqrt(variance) * generate_normal_bm() + mean

def empirical_stats_dsv(sample, values, probs):
    N = len(sample)
    counts = {v: 0 for v in values}
    for s in sample:
        counts[s] = counts.get(s, 0) + 1
    emp_probs = [counts[v] / N for v in values]
    Ex = sum(p * x for p, x in zip(probs, values))
    Dx = sum(p * x**2 for p, x in zip(probs, values)) - Ex**2
    Ex_hat = sum(p * x for p, x in zip(emp_probs, values))
    Dx_hat = sum(p * x**2 for p, x in zip(emp_probs, values)) - Ex_hat**2
    rel_E = abs(Ex_hat - Ex) / abs(Ex) if Ex != 0 else float('inf')
    rel_D = abs(Dx_hat - Dx) / abs(Dx) if Dx != 0 else float('inf')
    observed = np.array([counts[v] for v in values], dtype=float)
    expected = np.array([p * N for p in probs], dtype=float)
    chi2_stat, _ = scipy_stats.chisquare(observed, f_exp=expected + 1e-10)
    chi2_crit = scipy_stats.chi2.ppf(0.95, len(values) - 1)
    return dict(emp_probs=emp_probs, counts=[counts[v] for v in values], Ex=Ex, Dx=Dx, Ex_hat=Ex_hat, Dx_hat=Dx_hat,
                rel_E=rel_E, rel_D=rel_D, chi2=chi2_stat, chi2_crit=chi2_crit, chi2_reject=chi2_stat > chi2_crit)

def build_histogram(sample, num_bins=None):
    N = len(sample)
    if num_bins is None:
        num_bins = math.ceil(math.log2(N)) + 1
    lo, hi = min(sample), max(sample)
    width = (hi - lo + 1e-10) / num_bins
    edges = [lo + i * width for i in range(num_bins + 1)]
    counts = [0] * num_bins
    for x in sample:
        idx = min(int((x - lo) / width), num_bins - 1)
        counts[idx] += 1
    intervals = [(edges[i], edges[i+1]) for i in range(num_bins)]
    return intervals, [c / N for c in counts], counts

def empirical_stats_continuous(sample, mean, variance):
    N = len(sample)
    Ex_hat = sum(sample) / N
    Dx_hat = sum(x**2 for x in sample) / N - Ex_hat**2
    rel_E = abs(Ex_hat - mean) / abs(mean) if mean != 0 else float('inf')
    rel_D = abs(Dx_hat - variance) / abs(variance) if variance != 0 else float('inf')
    sigma = math.sqrt(variance)
    intervals, rel_freqs, counts = build_histogram(sample)
    cdf_vals = scipy_stats.norm.cdf([b for _, b in intervals], mean, sigma)
    cdf_lo = scipy_stats.norm.cdf([a for a, _ in intervals], mean, sigma)
    expected_probs = np.maximum(cdf_vals - cdf_lo, 1e-10)
    expected_probs = expected_probs / expected_probs.sum()
    expected = expected_probs * N
    chi2_stat, _ = scipy_stats.chisquare(counts, f_exp=expected)
    chi2_crit = scipy_stats.chi2.ppf(0.95, len(intervals) - 1)
    return dict(Ex_hat=Ex_hat, Dx_hat=Dx_hat, Ex=mean, Dx=variance, rel_E=rel_E, rel_D=rel_D, chi2=chi2_stat, chi2_crit=chi2_crit,
                chi2_reject=chi2_stat > chi2_crit, intervals=intervals, rel_freqs=rel_freqs)

def write_box(box, lines):
    box.configure(state="normal")
    box.delete("1.0", "end")
    for text, tag in lines:
        box.insert("end", text, tag or "")
    box.configure(state="disabled")

N_SIZES = [10, 100, 1_000, 10_000]

class DSVTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        left = ttk.Frame(self)
        left.pack(side="left", fill="y", padx=10, pady=10)
        ttk.Label(left, text="Значения x (через пробел):").grid(row=0, column=0, sticky="w")
        self.e_vals = ttk.Entry(left, width=28)
        self.e_vals.insert(0, "1 2 3 4 5")
        self.e_vals.grid(row=1, column=0, pady=(0, 8), sticky="w")
        ttk.Label(left, text="Вероятности p (через пробел):").grid(row=2, column=0, sticky="w")
        self.e_probs = ttk.Entry(left, width=28)
        self.e_probs.insert(0, "0.2 0.15 0.3 0.2 0.15")
        self.e_probs.grid(row=3, column=0, pady=(0, 8), sticky="w")
        ttk.Label(left, text="Объём выборки N:").grid(row=4, column=0, sticky="w")
        self.e_N = ttk.Entry(left, width=12)
        self.e_N.insert(0, "100")
        self.e_N.grid(row=5, column=0, pady=(0, 10), sticky="w")
        ttk.Button(left, text="Запустить", command=self.run).grid(row=6, column=0, sticky="w", pady=(0, 10))
        ttk.Separator(left, orient="horizontal").grid(row=7, column=0, sticky="ew", pady=6)
        ttk.Label(left, text="Быстрый запуск:").grid(row=8, column=0, sticky="w")
        for i, n_val in enumerate(N_SIZES):
            ttk.Button(left, text=f"N = {n_val}", command=lambda v=n_val: self.quick_run(v)).grid(row=9 + i, column=0, sticky="w", pady=1)
        ttk.Button(left, text="Все N (10…10000)", command=self.run_all).grid(row=9 + len(N_SIZES), column=0, sticky="w", pady=(4, 1))
        ttk.Separator(left, orient="horizontal").grid(row=14, column=0, sticky="ew", pady=6)
        ttk.Label(left, text="Результаты:").grid(row=15, column=0, sticky="w")
        self.result_box = tk.Text(left, width=38, height=18, state="disabled", wrap="word", font=("Courier New", 9))
        self.result_box.grid(row=16, column=0, sticky="nsew")
        self.result_box.tag_configure("ok", foreground="green")
        self.result_box.tag_configure("bad", foreground="red")
        right = ttk.Frame(self)
        right.pack(side="left", fill="both", expand=True, padx=(0, 10), pady=10)
        self.fig, self.ax = plt.subplots(figsize=(6, 4))
        self.canvas = FigureCanvasTkAgg(self.fig, master=right)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

    def _parse(self):
        values = list(map(float, self.e_vals.get().split()))
        probs = list(map(float, self.e_probs.get().split()))
        if len(values) != len(probs):
            raise ValueError("Число значений и вероятностей должно совпадать!")
        neg_probs = [p for p in probs if p < 0]
        if neg_probs:
            raise ValueError(f"Вероятности не могут быть отрицательными!\nНайдены: {neg_probs}")
        total_p = sum(probs)
        if abs(total_p - 1.0) > 0.01:
            raise ValueError(f"Сумма вероятностей = {total_p:.4f} ≠ 1!")
        probs = [p / total_p for p in probs]
        return values, probs

    def _result_lines(self, N, values, probs, s):
        lines = []
        lines.append((f"N = {N}\n\n", None))
        lines.append(("xi    | теор. p  | эмп. p^\n", None))
        lines.append(("-" * 30 + "\n", None))
        for v, tp, ep in zip(values, probs, s["emp_probs"]):
            lines.append((f"{v:5.1f} |  {tp:.4f}  |  {ep:.4f}\n", None))
        lines.append(("\n", None))
        lines.append((f"Ex  = {s['Ex']:.4f}\n", None))
        lines.append((f"Ex^ = {s['Ex_hat']:.4f}  (погр. {s['rel_E']:.1%})\n", "ok" if s["rel_E"] < 0.15 else "bad"))
        lines.append(("\n", None))
        lines.append((f"Dx  = {s['Dx']:.4f}\n", None))
        lines.append((f"Dx^ = {s['Dx_hat']:.4f}  (погр. {s['rel_D']:.1%})\n", "ok" if s["rel_D"] < 0.15 else "bad"))
        sign = ">" if s["chi2"] > s["chi2_crit"] else "<"
        lines.append((f"\nchi2 = {s['chi2']:.3f} {sign} {s['chi2_crit']:.3f} → ", None))
        lines.append(("ОТВЕРГАЕМ H0\n" if s["chi2_reject"] else "Не отвергаем H0\n", "bad" if s["chi2_reject"] else "ok"))
        return lines

    def _draw(self, N, values, probs, s):
        self.ax.clear()
        x = np.arange(len(values))
        w = 0.35
        self.ax.bar(x - w/2, s["emp_probs"], w, label="Эмп. частоты")
        self.ax.bar(x + w/2, probs, w, label="Теор. вероятности")
        self.ax.set_xticks(x)
        self.ax.set_xticklabels([str(int(v)) if v == int(v) else str(v) for v in values])
        self.ax.set_xlabel("Значения x")
        self.ax.set_ylabel("Вероятность")
        self.ax.set_title(f"ДСВ (N = {N})")
        self.ax.legend()
        self.fig.tight_layout()
        self.canvas.draw()

    def quick_run(self, n):
        self.e_N.delete(0, "end")
        self.e_N.insert(0, str(n))
        self.run()

    def run(self):
        try:
            values, probs = self._parse()
            N = int(self.e_N.get())
            if N <= 0:
                raise ValueError("Объём выборки N должен быть положительным!")
        except ValueError as e:
            messagebox.showerror("Ошибка", str(e)); return
        sample = [generate_dsv(random.random(), values, probs) for _ in range(N)]
        s = empirical_stats_dsv(sample, values, probs)
        write_box(self.result_box, self._result_lines(N, values, probs, s))
        self._draw(N, values, probs, s)

    def run_all(self):
        try:
            values, probs = self._parse()
        except ValueError as e:
            messagebox.showerror("Ошибка", str(e)); return
        conclusions = [
            "N=10:    низкая точность, велики отклонения.\n",
            "N=100:   погрешности заметны, χ² нестабилен.\n",
            "N=1000:  хорошая сходимость с теорией.\n",
            "N=10000: высокая точность, χ² стабилен.\n",]
        all_lines = []
        last_s = None
        for i, N in enumerate(N_SIZES):
            sample = [generate_dsv(random.random(), values, probs) for _ in range(N)]
            s = empirical_stats_dsv(sample, values, probs)
            all_lines += self._result_lines(N, values, probs, s)
            all_lines.append(("\nВывод: " + conclusions[i], None))
            all_lines.append(("─" * 32 + "\n", None))
            last_s = (N, s)
        write_box(self.result_box, all_lines)
        if last_s:
            N, s = last_s
            self._draw(N, values, probs, s)
        self.e_N.delete(0, "end")
        self.e_N.insert(0, str(N_SIZES[-1]))


class NormalTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        left = ttk.Frame(self)
        left.pack(side="left", fill="y", padx=10, pady=10)
        ttk.Label(left, text="Среднее (a):").grid(row=0, column=0, sticky="w")
        self.e_mean = ttk.Entry(left, width=12)
        self.e_mean.insert(0, "0.1")
        self.e_mean.grid(row=1, column=0, pady=(0, 8), sticky="w")
        ttk.Label(left, text="Дисперсия (σ²):").grid(row=2, column=0, sticky="w")
        self.e_var = ttk.Entry(left, width=12)
        self.e_var.insert(0, "1")
        self.e_var.grid(row=3, column=0, pady=(0, 8), sticky="w")
        ttk.Label(left, text="Объём выборки N:").grid(row=4, column=0, sticky="w")
        self.e_N = ttk.Entry(left, width=12)
        self.e_N.insert(0, "1000")
        self.e_N.grid(row=5, column=0, pady=(0, 10), sticky="w")
        ttk.Button(left, text="Запустить", command=self.run).grid(row=6, column=0, sticky="w", pady=(0, 10))
        ttk.Separator(left, orient="horizontal").grid(row=7, column=0, sticky="ew", pady=6)
        ttk.Label(left, text="Быстрый запуск:").grid(row=8, column=0, sticky="w")
        for i, n_val in enumerate(N_SIZES):
            ttk.Button(left, text=f"N = {n_val}", command=lambda v=n_val: self.quick_run(v)).grid(row=9 + i, column=0, sticky="w", pady=1)
        ttk.Button(left, text="Все N (10…10000)", command=self.run_all).grid(row=9 + len(N_SIZES), column=0, sticky="w", pady=(4, 1))
        ttk.Separator(left, orient="horizontal").grid(row=14, column=0, sticky="ew", pady=6)
        ttk.Label(left, text="Результаты:").grid(row=15, column=0, sticky="w")
        self.result_box = tk.Text(left, width=38, height=18, state="disabled", wrap="word", font=("Courier New", 9))
        self.result_box.grid(row=16, column=0, sticky="nsew")
        self.result_box.tag_configure("ok", foreground="green")
        self.result_box.tag_configure("bad", foreground="red")
        right = ttk.Frame(self)
        right.pack(side="left", fill="both", expand=True, padx=(0, 10), pady=10)
        self.fig, self.ax = plt.subplots(figsize=(6, 4))
        self.canvas = FigureCanvasTkAgg(self.fig, master=right)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

    def _conclusion(self, N):
        if N <= 10:
            return "N=10: точность низкая, выборка мала."
        elif N <= 100:
            return "N=100: погрешности заметны, χ² нестабилен."
        elif N <= 1000:
            return "N=1000: хорошая точность."
        else:
            return "N=10000: высокая точность."

    def _result_lines(self, N, mean, var, s):
        lines = []
        lines.append((f"N = {N}  |  a = {mean}  |  σ² = {var}\n\n", None))
        lines.append((f"Ex  = {s['Ex']:.4f}\n", None))
        lines.append((f"Ex^ = {s['Ex_hat']:.4f}  (погр. {s['rel_E']:.1%})\n", "ok" if s["rel_E"] < 0.15 else "bad"))
        lines.append(("\n", None))
        lines.append((f"Dx  = {s['Dx']:.4f}\n", None))
        lines.append((f"Dx^ = {s['Dx_hat']:.4f}  (погр. {s['rel_D']:.1%})\n", "ok" if s["rel_D"] < 0.15 else "bad"))
        sign = ">" if s["chi2"] > s["chi2_crit"] else "<"
        lines.append((f"\nchi2 = {s['chi2']:.3f} {sign} {s['chi2_crit']:.3f} → ", None))
        lines.append(("ОТВЕРГАЕМ H0\n" if s["chi2_reject"] else "Не отвергаем H0\n", "bad" if s["chi2_reject"] else "ok"))
        conclusion = self._conclusion(N)
        lines.append((f"\nВывод: {conclusion}\n", "ok" if N >= 1000 else "bad"))
        return lines

    def _draw(self, N, mean, var, sample, s):
        self.ax.clear()
        intervals = s["intervals"]
        rel_freqs = s["rel_freqs"]
        lefts = [a for a, b in intervals]
        widths = [b - a for a, b in intervals]
        bin_w = widths[0] if widths else 1
        self.ax.bar(lefts, rel_freqs, widths, align="edge", alpha=0.7, label="Гистограмма", edgecolor="white")
        sigma = math.sqrt(var)
        xs = np.linspace(min(sample) - sigma, max(sample) + sigma, 300)
        ys = [math.exp(-0.5 * ((x - mean) / sigma)**2) / (sigma * math.sqrt(2 * math.pi)) * bin_w for x in xs]
        self.ax.plot(xs, ys, color="red", linewidth=2, label=f"N({mean}, {var})")
        labels = [f"({a:.1f};{b:.1f}]" for a, b in intervals]
        self.ax.set_xticks([l + w/2 for l, w in zip(lefts, widths)])
        self.ax.set_xticklabels(labels, rotation=30, ha="right", fontsize=7)
        self.ax.set_xlabel("Интервалы")
        self.ax.set_ylabel("Относит. частота")
        self.ax.set_title(f"Нормальная СВ (N = {N})")
        self.ax.legend()
        self.fig.tight_layout()
        self.canvas.draw()

    def quick_run(self, n):
        self.e_N.delete(0, "end")
        self.e_N.insert(0, str(n))
        self.run()

    def run(self):
        try:
            mean = float(self.e_mean.get())
            var = float(self.e_var.get())
            N = int(self.e_N.get())
        except ValueError:
            messagebox.showerror("Ошибка", "Проверьте входные данные!"); return
        if var <= 0:
            messagebox.showerror("Ошибка", "Дисперсия должна быть > 0!"); return
        if N <= 0:
            messagebox.showerror("Ошибка", "Объём выборки N должен быть положительным!"); return
        sample = [generate_normal(mean, var) for _ in range(N)]
        s = empirical_stats_continuous(sample, mean, var)
        write_box(self.result_box, self._result_lines(N, mean, var, s))
        self._draw(N, mean, var, sample, s)

    def run_all(self):
        try:
            mean = float(self.e_mean.get())
            var = float(self.e_var.get())
        except ValueError:
            messagebox.showerror("Ошибка", "Проверьте входные данные!"); return
        if var <= 0:
            messagebox.showerror("Ошибка", "Дисперсия должна быть > 0!"); return
        all_lines = []
        last = None
        for N in N_SIZES:
            sample = [generate_normal(mean, var) for _ in range(N)]
            s = empirical_stats_continuous(sample, mean, var)
            all_lines += self._result_lines(N, mean, var, s)
            all_lines.append(("─" * 32 + "\n", None))
            last = (N, sample, s)
        write_box(self.result_box, all_lines)
        if last:
            N, sample, s = last
            self._draw(N, mean, var, sample, s)
        self.e_N.delete(0, "end")
        self.e_N.insert(0, str(N_SIZES[-1]))


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Имитационное моделирование СВ")
        self.geometry("1100x700")
        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=6, pady=6)
        tab1 = ttk.Frame(nb)
        tab2 = ttk.Frame(nb)
        nb.add(tab1, text="ДСВ")
        nb.add(tab2, text="Нормальная СВ")
        DSVTab(tab1).pack(fill="both", expand=True)
        NormalTab(tab2).pack(fill="both", expand=True)

if __name__ == "__main__":
    App().mainloop()
