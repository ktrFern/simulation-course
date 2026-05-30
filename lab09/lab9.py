import tkinter as tk
from tkinter import ttk
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

NUMB = 100
DELAY = 20

class MM1App:
    def __init__(self, main):
        self.main = main
        self.main.title("Моделирование системы")
        self._anim_id = None
        self._anim_running = False
        self._anim_paused = False
        self._anim_idx = 0
        self._arr_times = None
        self._svc_times = None
        self._N_anim = 0
        self._lam_anim = 1.0
        self._mu_anim = 1.0
        self._srv_free = 0.0
        self._accepted = 0
        self._rejected = 0

        self.params = ttk.LabelFrame(main, text="Параметры")
        self.params.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)

        self.lambda_var = self.add_spin("Интенсивность потока λ:", 0.1, 100.0, 0.5, 5.0)
        self.mu_var = self.add_spin("Интенсивность обслуживания μ:", 0.1, 100.0, 0.5, 6.0)
        self.N_var = self.add_spin("Число заявок N:", 100, 1_000_000, 1000, 10_000)

        cols = ("lambda", "mu", "N", "p0_emp", "p0_th", "p1_emp", "p1_th", "rho", "A_emp")
        self.table = ttk.Treeview(self.params, columns=cols, show="headings", height=6)
        for col, text, width in [
            ("lambda", "λ", 40),
            ("mu", "μ", 40),
            ("N", "N", 60),
            ("p0_emp", "P0 эмп", 70),
            ("p0_th", "P0 теор", 70),
            ("p1_emp", "P1 эмп", 70),
            ("p1_th", "P1 теор", 70),
            ("rho", "ρ", 50),
            ("A_emp", "A эмп", 70),
        ]:
            self.table.heading(col, text=text)
            self.table.column(col, width=width, anchor="center", stretch=False)
        self.table.pack(pady=10, padx=4)

        bf = ttk.Frame(self.params)
        bf.pack(fill="x", pady=5, padx=4)
        ttk.Button(bf, text="Запустить", command=self.run_simulation).pack(fill="x", pady=2)
        ttk.Button(bf, text="Анимация", command=self.start_animation).pack(fill="x", pady=2)
        ttk.Button(bf, text="Стоп", command=self.pause_animation).pack(fill="x", pady=2)
        ttk.Button(bf, text="Продолжить", command=self.resume_animation).pack(fill="x", pady=2)
        ttk.Button(bf, text="Очистить", command=self.clear_all).pack(fill="x", pady=2)
        ttk.Button(bf, text="Закрыть", command=self.main.destroy).pack(fill="x", pady=2)

        self.fig, self.ax = plt.subplots(figsize=(7, 5))
        self._reset_axes()
        self.canvas = FigureCanvasTkAgg(self.fig, master=main)
        self.canvas.get_tk_widget().pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

    def add_spin(self, label, start, end, step, default):
        ttk.Label(self.params, text=label).pack(anchor="w", padx=4)
        var = tk.DoubleVar(value=default)
        ttk.Spinbox(self.params, from_=start, to=end, increment=step, textvariable=var).pack(fill="x", padx=4, pady=2)
        return var

    def _reset_axes(self):
        self.ax.cla()
        self.ax.set_xlabel("Состояние системы")
        self.ax.set_ylabel("Вероятность")
        self.ax.set_title("Сравнение вероятностей состояний СМО")
        self.ax.grid(axis="y", linestyle="--", alpha=0.4)

    @staticmethod
    def simulate(lam, mu, n_requests):
        inter_arrivals = np.random.exponential(1.0 / lam, n_requests)
        service_times = np.random.exponential(1.0 / mu, n_requests)
        arrival_times = np.cumsum(inter_arrivals)

        server_free_time = 0.0
        accepted = 0
        rejected = 0

        for i in range(n_requests):
            t_arr = arrival_times[i]
            if t_arr >= server_free_time:
                accepted += 1
                server_free_time = t_arr + service_times[i]
            else:
                rejected += 1

        return accepted / n_requests, rejected / n_requests

    @staticmethod
    def _erlang(lam, mu):
        rho = lam / mu
        p0_th = 1.0 / (1.0 + rho)
        p1_th = rho / (1.0 + rho)
        return rho, p0_th, p1_th

    def _draw_bars(self, p0_emp, p1_emp, lam, mu, final=False):
        rho, p0_th, p1_th = self._erlang(lam, mu)
        self._reset_axes()

        labels = ["P0 (свободен)", "P1 (занят/потеря)"]
        x = np.arange(2)
        w = 0.35
        tag = f"λ={lam} μ={mu}"

        self.ax.bar(x - w / 2, [p0_emp, p1_emp], w, alpha=0.8, label=f"Эмп. {tag}")
        self.ax.bar(x + w / 2, [p0_th, p1_th], w, alpha=0.6, label=f"Теор. {tag}")
        self.ax.set_xticks(x)
        self.ax.set_xticklabels(labels)
        self.ax.set_ylim(0, 1.05)
        self.ax.legend(fontsize=9)

        if not final:
            self.ax.set_title(f"Анимация {self._anim_idx}/{self._N_anim}")
        self.canvas.draw()

    def run_simulation(self):
        self._stop_animation()
        lam = self.lambda_var.get()
        mu = self.mu_var.get()
        N = int(self.N_var.get())
        np.random.seed(42)
        p0_emp, p1_emp = self.simulate(lam, mu, N)
        self._finish(lam, mu, N, p0_emp, p1_emp)

    def _finish(self, lam, mu, N, p0_emp, p1_emp):
        rho, p0_th, p1_th = self._erlang(lam, mu)
        A_emp = lam * p0_emp
        self.table.insert("", tk.END, values=(
            f"{lam}", f"{mu}", f"{N}",
            f"{p0_emp:.4f}", f"{p0_th:.4f}",
            f"{p1_emp:.4f}", f"{p1_th:.4f}",
            f"{rho:.3f}", f"{A_emp:.3f}",
        ))
        self._draw_bars(p0_emp, p1_emp, lam, mu, final=True)

    def start_animation(self):
        self._stop_animation()
        lam = self.lambda_var.get()
        mu = self.mu_var.get()
        N = int(self.N_var.get())
        np.random.seed(42)
        self._arr_times = np.cumsum(np.random.exponential(1.0 / lam, N))
        self._svc_times = np.random.exponential(1.0 / mu, N)
        self._N_anim = N
        self._lam_anim = lam
        self._mu_anim = mu
        self._anim_idx = 0
        self._srv_free = 0.0
        self._accepted = 0
        self._rejected = 0
        self._anim_paused = False
        self._anim_running = True
        self._anim_tick()

    def pause_animation(self):
        if self._anim_running:
            self._anim_paused = True
            if self._anim_id is not None:
                self.main.after_cancel(self._anim_id)
                self._anim_id = None
            self._anim_running = False

    def resume_animation(self):
        if self._anim_paused and self._anim_idx < self._N_anim:
            self._anim_paused = False
            self._anim_running = True
            self._anim_tick()

    def _anim_tick(self):
        if not self._anim_running:
            return

        chunk_end = min(self._anim_idx + NUMB, self._N_anim)
        for i in range(self._anim_idx, chunk_end):
            t_arr = self._arr_times[i]
            if t_arr >= self._srv_free:
                self._accepted += 1
                self._srv_free = t_arr + self._svc_times[i]
            else:
                self._rejected += 1

        self._anim_idx = chunk_end
        processed = self._anim_idx
        total = self._N_anim

        p0_emp = self._accepted / processed
        p1_emp = self._rejected / processed
        self._draw_bars(p0_emp, p1_emp, self._lam_anim, self._mu_anim, final=False)

        if processed < total:
            self._anim_id = self.main.after(DELAY, self._anim_tick)
        else:
            self._anim_running = False
            self._anim_paused = False
            self._finish(self._lam_anim, self._mu_anim, total, p0_emp, p1_emp)

    def _stop_animation(self):
        if self._anim_id is not None:
            self.main.after_cancel(self._anim_id)
            self._anim_id = None
        self._anim_running = False
        self._anim_paused = False

    def clear_all(self):
        self._stop_animation()
        for row in self.table.get_children():
            self.table.delete(row)
        self._reset_axes()
        self.canvas.draw()

if __name__ == "__main__":
    main = tk.Tk()
    app = MM1App(main)
    main.mainloop()