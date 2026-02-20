import tkinter as tk
from tkinter import ttk
import math
import os
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

class simApp:
    def __init__(self, main):
        self.main = main
        self.main.title("Моделирование полёта тела с сопротивлением воздуха")

        self.g = 9.81
        self.rho = 1.29
        self.C = 0.15

        self.is_running = False
        self.current_job = None

        self.params = ttk.LabelFrame(main, text="Параметры")
        self.params.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)

        self.v0_var = self.add_spin("Начальная скорость v0 (м/с)", 0, 50, 1, 30)
        self.angle_var = self.add_spin("Угол (градусы)", 0, 90, 1, 40)
        self.height_var = self.add_spin("Начальная высота y0 (м)", 0, 50, 1, 0)
        self.S_var = self.add_spin("Площадь поперечного сечения S (м²)", 0.001, 5, 0.01, 0.1)
        self.mass_var = self.add_spin("Масса m (кг)", 0.01, 100, 0.1, 1.5)
        self.dt_var = self.add_spin("Шаг моделирования dt (с)", 0.0001, 1, 0.01, 0.1)

        self.table = ttk.Treeview(self.params, columns=("dt", "range", "height", "speed"), show="headings", height=6)
        columns_info = [("dt", "dt, c", 50), ("range", "Дальность, м", 100), ("height", "Макс. высота, м", 120), ("speed", "Скорость в конце, м/с", 150)]

        for col, text, width in columns_info:
            self.table.heading(col, text=text)
            self.table.column(col, width=width, anchor="center", stretch=False)

        self.table.pack(pady=10)

        buttons_frame = ttk.Frame(self.params)
        buttons_frame.pack(fill="x", pady=5)
        ttk.Button(buttons_frame, text="Запустить", command=self.start_simulation).pack(fill="x", pady=2)
        ttk.Button(buttons_frame, text="Остановить", command=self.stop_simulation).pack(fill="x", pady=2)
        ttk.Button(buttons_frame, text="Построить сразу", command=self.plot_and_record).pack(fill="x", pady=2)
        ttk.Button(buttons_frame, text="Очистить", command=self.clear_all).pack(fill="x", pady=2)
        ttk.Button(buttons_frame, text="Закрыть", command=self.close_app).pack(fill="x", pady=2)

        self.fig, self.ax = plt.subplots(figsize=(7, 5))
        self.ax.set_xlabel("Дальность, м")
        self.ax.set_ylabel("Высота, м")
        self.ax.set_title("Траектория полёта")
        self.ax.grid()
        self.canvas = FigureCanvasTkAgg(self.fig, master=main)
        self.canvas.get_tk_widget().pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

    def add_spin(self, label, start, end, step, default):
        ttk.Label(self.params, text=label).pack(anchor="w")
        var = tk.DoubleVar(value=default)
        ttk.Spinbox(self.params, from_=start, to=end, increment=step, textvariable=var).pack(fill="x", pady=2)
        return var

    def record_in_table(self, dt, distance, max_height, speed_end):
        self.table.insert("", tk.END, values=(f"{dt}", f"{distance:.2f}", f"{max_height:.2f}", f"{speed_end:.2f}"))

    def init_state(self):
        v0 = self.v0_var.get()
        angle = math.radians(self.angle_var.get())
        y0 = self.height_var.get()
        m = self.mass_var.get()
        S = self.S_var.get()
        self.k = self.C * S * self.rho / (2 * m)
        self.vx = v0 * math.cos(angle)
        self.vy = v0 * math.sin(angle)
        self.x = 0
        self.y = y0
        self.t = 0
        self.max_height = y0

    def step(self, dt):
        v = math.sqrt(self.vx ** 2 + self.vy ** 2)
        self.vx -= self.k * self.vx * v * dt
        self.vy -= (self.g + self.k * self.vy * v) * dt
        self.x += self.vx * dt
        self.y += self.vy * dt

    def trajectory(self):
        dt = self.dt_var.get()
        self.init_state()
        x_data = []
        y_data = []

        while self.y >= 0:
            x_data.append(self.x)
            y_data.append(self.y)

            if self.y > self.max_height:
                self.max_height = self.y

            self.step(dt)

        speed_end = math.sqrt(self.vx ** 2 + self.vy ** 2)
        return x_data, y_data, self.x, self.max_height, speed_end

    def plot_and_record(self):
        if self.is_running:
            return

        x_data, y_data, distance, max_height, speed_end = self.trajectory()
        dt = self.dt_var.get()
        self.ax.plot(x_data, y_data, label=f"dt={dt}")
        self.ax.legend()
        self.ax.relim()
        self.ax.autoscale_view()
        self.canvas.draw()
        self.record_in_table(dt, distance, max_height, speed_end)

    def start_simulation(self):
        if self.is_running:
            return

        self.is_running = True
        self.init_state()
        self.x_data = []
        self.y_data = []
        dt = self.dt_var.get()
        self.line, = self.ax.plot([], [], label=f"dt={dt}")
        self.ax.legend()
        self.update()

    def update(self):
        if not self.is_running:
            return

        dt = self.dt_var.get()
        self.x_data.append(self.x)
        self.y_data.append(self.y)

        if self.y > self.max_height:
            self.max_height = self.y

        self.step(dt)
        self.line.set_data(self.x_data, self.y_data)
        self.ax.relim()
        self.ax.autoscale_view()
        self.canvas.draw()

        if self.y <= 0 and self.t > 0:
            self.is_running = False
            speed_end = math.sqrt(self.vx ** 2 + self.vy ** 2)
            self.record_in_table(dt, self.x, self.max_height, speed_end)
            return

        self.t += dt
        self.current_job = self.main.after(20, self.update)


    def stop_simulation(self):
        self.is_running = False
        if self.current_job:
            self.main.after_cancel(self.current_job)
            self.current_job = None

    def clear_all(self):
        self.stop_simulation()
        self.ax.cla()
        self.ax.set_xlabel("Дальность, м")
        self.ax.set_ylabel("Высота, м")
        self.ax.set_title("Траектория полёта")
        self.ax.grid()
        self.canvas.draw()

        for row in self.table.get_children():
            self.table.delete(row)

    def close_app(self):
        self.stop_simulation()
        self.main.destroy()
        os._exit(0)

if __name__ == "__main__":
    main = tk.Tk()
    app = simApp(main)
    main.mainloop()
