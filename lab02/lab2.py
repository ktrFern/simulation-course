import tkinter as tk
from tkinter import ttk
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import os

class HeatApp:
    def __init__(self, main):
        self.main = main
        self.main.title("Уравнение теплопроводности")

        self.running = False
        self.after_id = None
        self.cbar = None
        self.current_time = 0
        self.last_table_second = -1

        self.params = ttk.LabelFrame(main, text="Параметры")
        self.params.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)

        self.rho_var = self.add_spin("Плотность ρ", 100, 10000, 100, 2700)
        self.c_var = self.add_spin("Теплоёмкость c", 100, 2000, 10, 900)
        self.lmbd_var = self.add_spin("Теплопроводность λ", 1, 500, 1, 237)
        self.L_var = self.add_spin("Длина L (м)", 0.1, 10, 0.1, 0.4)
        self.T0_var = self.add_spin("Начальная T₀", -50, 200, 1, 0)
        self.TL_var = self.add_spin("T слева", -50, 300, 1, -5)
        self.TR_var = self.add_spin("T справа", -50, 300, 1, 35)
        self.tend_var = self.add_spin("Время моделирования", 0.1, 20, 0.1, 100.0)
        self.dt_var = self.add_spin("dt", 0.0001, 0.5, 0.001, 0.01)
        self.dx_var = self.add_spin("dx", 0.0001, 0.1, 0.001, 0.01)

        ttk.Label(self.params, text="Параметры моделирования").pack(pady=(10, 0))
        columns = ("dx", "dt", "T_center", "time")
        self.table = ttk.Treeview(self.params, columns=columns, show="headings", height=7)

        self.table.heading("dx", text="dx")
        self.table.heading("dt", text="dt")
        self.table.heading("T_center", text="T(центр)")
        self.table.heading("time", text="Время")

        for col in columns:
            self.table.column(col, width=90, anchor="center")

        self.table.pack(fill="x", pady=5)

        btns = ttk.Frame(self.params)
        btns.pack(fill="x", pady=10)

        ttk.Button(btns, text="Рассчитать", command=self.calculate).pack(fill="x", pady=2)
        ttk.Button(btns, text="Анимация", command=self.start_animation).pack(fill="x", pady=2)
        ttk.Button(btns, text="Стоп", command=self.stop_animation).pack(fill="x", pady=2)
        ttk.Button(btns, text="Очистить", command=self.clear).pack(fill="x", pady=2)
        ttk.Button(btns, text="Закрыть", command=self.close).pack(fill="x", pady=2)

        self.right_frame = ttk.Frame(main)
        self.right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self.fig, (self.ax1, self.ax2) = plt.subplots(2, 1, figsize=(8, 8), gridspec_kw={'height_ratios': [3, 2]})
        self.fig.subplots_adjust(hspace=0.4)

        self.canvas = FigureCanvasTkAgg(self.fig, master=self.right_frame)
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        self.timer_label = ttk.Label(self.right_frame, text="Время: 0.00 c", font=("Arial", 12))
        self.timer_label.pack(pady=5)

    def add_spin(self, label, start, end, step, default):
        ttk.Label(self.params, text=label).pack(anchor="w")
        var = tk.DoubleVar(value=default)
        ttk.Spinbox(self.params, from_=start, to=end, increment=step, textvariable=var).pack(fill="x", pady=2)
        return var

    def add_table_row(self):
        center_index = self.Nx // 2
        T_center = self.T[center_index]
        self.table.insert("", "end", values=(round(self.dx, 5), round(self.dt, 5), round(T_center, 2), round(self.current_time, 2)))

    def full_reset(self):
        self.stop_animation()
        self.current_time = 0
        self.last_table_second = -1

        if hasattr(self, "timer_label"):
            self.timer_label.config(text="Время: 0.00 c")

        for row in self.table.get_children():
            self.table.delete(row)

        if self.cbar:
            try:
                self.cbar.remove()
            except:
                pass
            self.cbar = None

        self.ax1.cla()
        self.ax2.cla()
        self.canvas.draw()

    def calculate(self):
        self.full_reset()

        dt = self.dt_var.get()
        dx = self.dx_var.get()
        t_end = self.tend_var.get()

        self.rho = self.rho_var.get()
        self.c = self.c_var.get()
        self.lmbd = self.lmbd_var.get()
        self.L = self.L_var.get()

        self.Nx = int(self.L / dx)
        self.x = np.linspace(0, self.L, self.Nx + 1)

        self.T = np.ones(self.Nx + 1) * self.T0_var.get()
        self.T[0] = self.TL_var.get()
        self.T[-1] = self.TR_var.get()

        self.dt = dt
        self.dx = dx

        self.A = self.lmbd / dx ** 2
        self.C = self.A
        self.B = 2 * self.lmbd / dx ** 2 + self.rho * self.c / dt

        self.alpha = np.zeros(self.Nx + 1)
        self.beta = np.zeros(self.Nx + 1)

        steps = int(t_end / dt)

        for _ in range(steps):
            self.alpha[0] = 0
            self.beta[0] = self.T[0]

            for i in range(1, self.Nx):
                Fi = -(self.rho * self.c / dt) * self.T[i]
                denom = self.B - self.C * self.alpha[i - 1]
                self.alpha[i] = self.A / denom
                self.beta[i] = (self.C * self.beta[i - 1] - Fi) / denom

            T_new = self.T.copy()
            for i in reversed(range(1, self.Nx)):
                T_new[i] = self.alpha[i] * T_new[i + 1] + self.beta[i]

            self.T = T_new

        self.current_time = t_end

        self.add_table_row()

        self.ax1.plot(self.x, self.T, color='red')
        self.ax1.set_xlim(0, self.L)
        self.ax1.grid()

        self.ax2.cla()

        self.im = self.ax2.imshow(
            [self.T],
            aspect='auto',
            cmap='hot',
            extent=[0, self.L, 0, 1]
        )

        if self.cbar:
            self.cbar.remove()
        self.cbar = self.fig.colorbar(self.im, ax=self.ax2)

        self.canvas.draw()

    def start_animation(self):
        self.full_reset()
        self.running = True

        self.current_time = 0
        self.last_table_second = -1

        self.rho = self.rho_var.get()
        self.c = self.c_var.get()
        self.lmbd = self.lmbd_var.get()
        self.L = self.L_var.get()
        self.dt = self.dt_var.get()
        self.dx = self.dx_var.get()
        self.t_end = self.tend_var.get()

        self.Nx = int(self.L / self.dx)
        self.x = np.linspace(0, self.L, self.Nx + 1)

        self.T = np.ones(self.Nx + 1) * self.T0_var.get()
        self.T[0] = self.TL_var.get()
        self.T[-1] = self.TR_var.get()

        self.A = self.lmbd / self.dx**2
        self.C = self.A
        self.B = 2 * self.lmbd / self.dx ** 2 + self.rho*self.c / self.dt

        self.alpha = np.zeros(self.Nx + 1)
        self.beta = np.zeros(self.Nx + 1)

        self.line, = self.ax1.plot(self.x, self.T, color='red')
        self.ax1.set_xlim(0, self.L)
        self.ax1.grid()

        self.im = self.ax2.imshow([self.T], aspect='auto', cmap='hot', extent=[0, self.L, 0, self.t_end])

        self.cbar = self.fig.colorbar(self.im, ax=self.ax2)

        self.add_table_row()

        self.canvas.draw()
        self.animate()

    def animate(self):
        if not self.running:
            return

        if self.current_time >= self.t_end:
            self.stop_animation()
            return

        self.current_time += self.dt

        self.timer_label.config(text=f"Время: {self.current_time:.2f} c")

        self.alpha[0] = 0
        self.beta[0] = self.T[0]

        for i in range(1, self.Nx):
            Fi = -(self.rho * self.c / self.dt) * self.T[i]
            denom = self.B - self.C * self.alpha[i - 1]
            self.alpha[i] = self.A / denom
            self.beta[i] = (self.C * self.beta[i - 1] - Fi) / denom

        T_new = self.T.copy()
        for i in reversed(range(1, self.Nx)):
            T_new[i] = self.alpha[i] * T_new[i + 1] + self.beta[i]

        self.T = T_new

        self.line.set_ydata(self.T)
        self.im.set_data([self.T])

        current_second = int(self.current_time)
        if current_second != self.last_table_second:
            self.add_table_row()
            self.last_table_second = current_second

        self.canvas.draw()
        self.after_id = self.main.after(30, self.animate)

    def stop_animation(self):
        self.running = False
        if self.after_id:
            self.main.after_cancel(self.after_id)

    def clear(self):
        self.full_reset()

    def close(self):
        self.stop_animation()
        self.main.destroy()
        os._exit(0)

if __name__ == "__main__":
    root = tk.Tk()
    app = HeatApp(root)
    root.mainloop()