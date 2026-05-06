import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import numpy as np
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.gridspec as gridspec
import matplotlib.patches as mpatches
import csv
import threading
import time
import os
from datetime import datetime

STATES = {1: "Ясно", 2: "Облачно", 3: "Пасмурно"}
STATE_COLORS = {1: "#F4A020", 2: "#5B9BD5", 3: "#6E8C6E"}
DEFAULT_Q = [
    ["-0.20", "0.15", "0.05"],
    ["0.10", "-0.25", "0.15"],
    ["0.05", "0.10", "-0.15"],
]
DEFAULT_DAYS = "1000"
DEFAULT_DELAY = "0.5"
DEFAULT_FREQ = "1"

def stationary_distribution(Q: np.ndarray) -> np.ndarray:
    n = Q.shape[0]
    A = Q.T.copy()
    A[-1, :] = 1.0
    b = np.zeros(n)
    b[-1] = 1.0
    return np.linalg.solve(A, b)

def next_event(state: int, Q: np.ndarray):
    i = state - 1
    rate = -Q[i, i]
    dwell = np.random.exponential(1.0 / rate)
    off = Q[i].copy()
    off[i] = 0.0
    new_state = np.random.choice([1, 2, 3], p=off / rate)
    return new_state, dwell

def validate_Q(Q: np.ndarray) -> str:
    for i in range(3):
        if Q[i, i] >= 0:
            return f"Диагональный элемент Q[{i+1},{i+1}] должен быть < 0"
        for j in range(3):
            if i != j and Q[i, j] < 0:
                return f"Внедиагональный элемент Q[{i+1},{j+1}] должен быть ≥ 0"
        row_sum = Q[i].sum()
        if abs(row_sum) > 1e-9:
            return f"Сумма строки {i+1} = {row_sum:.4f} ≠ 0  (должна равняться нулю)"
    return ""

class WeatherApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Марковская модель погоды")
        self.resizable(True, True)
        style = ttk.Style(self)
        style.theme_use("clam")
        self._apply_style(style)
        self._sim_running = False
        self._sim_thread = None
        self._stop_flag = threading.Event()
        self._lock = threading.Lock()
        self._times = []
        self._states_hist = []
        self._durations = {s: 0.0 for s in STATES}
        self._current_state = 1
        self._current_time = 0.0
        self._transition_id = 0
        self._pi_theor = np.zeros(3)
        self._sim_days = 365
        self._log_rows = []
        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _apply_style(self, s: ttk.Style):
        BG = "#F0F0F0"
        FRM = "#E4E4E4"
        ACC = "#2563EB"
        TXT = "#1A1A1A"
        s.configure(".", background=BG, foreground=TXT, font=("Segoe UI", 10))
        s.configure("TFrame", background=BG)
        s.configure("TLabelframe", background=FRM, foreground=TXT, font=("Segoe UI", 10, "bold"), relief="groove", borderwidth=2)
        s.configure("TLabelframe.Label", background=FRM, foreground=ACC, font=("Segoe UI", 10, "bold"))
        s.configure("TLabel", background=BG, foreground=TXT)
        s.configure("Inner.TLabel", background=FRM, foreground=TXT)
        s.configure("TEntry", fieldbackground="white", foreground=TXT, borderwidth=1, relief="solid")
        s.configure("TButton", font=("Segoe UI", 10, "bold"), relief="flat", borderwidth=0, padding=(12, 6))
        s.configure("Start.TButton", background="#16A34A", foreground="white")
        s.configure("Stop.TButton", background="#DC2626", foreground="white")
        s.configure("Save.TButton", background="#2563EB", foreground="white")
        s.configure("Resume.TButton", background="#7C3AED", foreground="white")
        s.map("Start.TButton", background=[("active", "#15803D"), ("disabled", "#BBF7D0")])
        s.map("Stop.TButton", background=[("active", "#B91C1C"), ("disabled", "#FECACA")])
        s.map("Save.TButton", background=[("active", "#1D4ED8"), ("disabled", "#BFDBFE")])
        s.map("Resume.TButton", background=[("active", "#6D28D9"), ("disabled", "#DDD6FE")])
        s.configure("Status.TLabel", font=("Segoe UI", 10, "bold"), background="#1E3A5F", foreground="white", padding=(8, 4))
        s.configure("Header.TLabel", font=("Segoe UI", 11, "bold"), background="#F0F0F0", foreground="#1A1A1A")
        s.configure("MatrixEntry.TEntry", font=("Consolas", 10), fieldbackground="white")

    def _build_ui(self):
        self.configure(bg="#F0F0F0")
        ctrl = ttk.Frame(self, padding=10)
        ctrl.grid(row=0, column=0, sticky="nsew")
        ttk.Label(ctrl, text="Марковская модель погоды", style="Header.TLabel").grid(row=0, column=0, columnspan=2, pady=(0, 12), sticky="w")
        lf_q = ttk.LabelFrame(ctrl, text="Матрица интенсивностей Q", padding=8)
        lf_q.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        state_names = ["Ясно", "Облачно", "Пасмурно"]
        ttk.Label(lf_q, text="", style="Inner.TLabel", width=8).grid(row=0, column=0)

        for j, name in enumerate(state_names):
            ttk.Label(lf_q, text=name, style="Inner.TLabel", font=("Segoe UI", 9, "bold"), width=9, anchor="center").grid(row=0, column=j+1, padx=2)
        self._q_entries = []

        for i in range(3):
            ttk.Label(lf_q, text=state_names[i], style="Inner.TLabel", font=("Segoe UI", 9, "bold"), width=8).grid(row=i+1, column=0, pady=2)
            row_entries = []
            for j in range(3):
                var = tk.StringVar(value=DEFAULT_Q[i][j])
                e = ttk.Entry(lf_q, textvariable=var, width=8, style="MatrixEntry.TEntry", justify="center")
                e.grid(row=i+1, column=j+1, padx=3, pady=2)
                row_entries.append(var)
            self._q_entries.append(row_entries)

        ttk.Button(lf_q, text="Пересчитать диагональ", command=self._auto_diagonal).grid(row=4, column=0, columnspan=4, pady=(6, 0), sticky="ew")
        lf_par = ttk.LabelFrame(ctrl, text="Параметры", padding=8)
        lf_par.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(0, 10))

        params = [
            ("Дней симуляции:", "days_var", DEFAULT_DAYS),
            ("Задержка (сек):", "delay_var", DEFAULT_DELAY),
            ("Обновл. каждые N переходов:", "freq_var", DEFAULT_FREQ),
        ]

        for idx, (lbl, attr, default) in enumerate(params):
            ttk.Label(lf_par, text=lbl, style="Inner.TLabel").grid(row=idx, column=0, sticky="w", pady=3)
            var = tk.StringVar(value=default)
            setattr(self, f"_{attr}", var)
            ttk.Entry(lf_par, textvariable=var, width=10).grid(row=idx, column=1, sticky="w", padx=(8, 0))

        btn_frame = ttk.Frame(ctrl)
        btn_frame.grid(row=3, column=0, columnspan=2, pady=(4, 10), sticky="ew")
        btn_frame.columnconfigure((0, 1, 2), weight=1)
        self._btn_start = ttk.Button(btn_frame, text="▶  Запуск", style="Start.TButton", command=self._start_sim)
        self._btn_start.grid(row=0, column=0, padx=(0, 4), pady=(0, 4), sticky="ew")
        self._btn_stop = ttk.Button(btn_frame, text="■  Стоп", style="Stop.TButton", command=self._stop_sim, state="disabled")
        self._btn_stop.grid(row=0, column=1, padx=4, pady=(0, 4), sticky="ew")
        self._btn_resume = ttk.Button(btn_frame, text="▶▶  Продолжить", style="Resume.TButton", command=self._resume_sim, state="disabled")
        self._btn_resume.grid(row=0, column=2, padx=(4, 0), pady=(0, 4), sticky="ew")
        self._btn_save = ttk.Button(btn_frame, text="💾  Сохранить", style="Save.TButton", command=self._save_csv, state="disabled")
        self._btn_save.grid(row=1, column=0, columnspan=3, pady=(0, 0), sticky="ew")

        lf_theor = ttk.LabelFrame(ctrl, text="Теоретическое стац. распределение", padding=8)
        lf_theor.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        self._theor_labels = {}

        for idx, s in enumerate(STATES):
            ttk.Label(lf_theor, text=f"{STATES[s]}:", style="Inner.TLabel").grid(row=idx, column=0, sticky="w", pady=2)
            lbl = ttk.Label(lf_theor, text="—", style="Inner.TLabel", font=("Consolas", 10))
            lbl.grid(row=idx, column=1, sticky="w", padx=(10, 0))
            self._theor_labels[s] = lbl

        self._status_var = tk.StringVar(value="Готово к запуску")
        ttk.Label(ctrl, textvariable=self._status_var, style="Status.TLabel", width=38).grid(row=5, column=0, columnspan=2, sticky="ew", pady=(6, 0))
        plot_frame = ttk.Frame(self, padding=(0, 10, 10, 10))
        plot_frame.grid(row=0, column=1, sticky="nsew")

        self._fig = plt.figure(figsize=(11, 7), facecolor="#FAFAFA")
        self._canvas = FigureCanvasTkAgg(self._fig, master=plot_frame)
        self._canvas.get_tk_widget().pack(fill="both", expand=True)
        self._setup_axes()
        self.columnconfigure(0, minsize=320, weight=0)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

    def _setup_axes(self):
        self._fig.clf()
        gs = gridspec.GridSpec(2, 2, figure=self._fig, hspace=0.52, wspace=0.35, left=0.07, right=0.97, top=0.93, bottom=0.09)
        self._ax_tl = self._fig.add_subplot(gs[0, :])
        self._ax_cmp = self._fig.add_subplot(gs[1, 0])
        self._ax_pie = self._fig.add_subplot(gs[1, 1])
        self._fig.suptitle("Марковская модель погоды", fontsize=13, fontweight="bold", color="#1A1A1A")

        for ax in (self._ax_tl, self._ax_cmp, self._ax_pie):
            ax.set_facecolor("#F7F7F7")
        self._canvas.draw()

    def _auto_diagonal(self):
        for i in range(3):
            try:
                off_sum = sum(float(self._q_entries[i][j].get()) for j in range(3) if j != i)
                self._q_entries[i][i].set(f"{-off_sum:.4f}")
            except ValueError:
                messagebox.showerror("Ошибка", f"Некорректное значение во строке {i+1}")
                return

    def _read_Q(self):
        Q = np.zeros((3, 3))
        for i in range(3):
            for j in range(3):
                try:
                    Q[i, j] = float(self._q_entries[i][j].get())
                except ValueError:
                    raise ValueError(f"Некорректное число в Q[{i+1},{j+1}]")
        return Q

    def _start_sim(self):
        try:
            Q = self._read_Q()
        except ValueError as e:
            messagebox.showerror("Ошибка матрицы", str(e))
            return
        err = validate_Q(Q)
        if err:
            messagebox.showerror("Ошибка матрицы Q", err)
            return

        try:
            sim_days = float(self._days_var.get())
            delay = float(self._delay_var.get())
            freq = int(self._freq_var.get())
            assert sim_days > 0 and delay >= 0 and freq >= 1
        except Exception:
            messagebox.showerror("Ошибка параметров", "Проверьте поля «Параметры»:\n  Дней > 0, Задержка ≥ 0, Частота ≥ 1 (целое)")
            return
        pi = stationary_distribution(Q)
        self._pi_theor = pi

        for idx, s in enumerate(STATES):
            self._theor_labels[s].config(text=f"{pi[idx]:.4f}")
        with self._lock:
            self._times = [0.0]
            self._states_hist = []
            self._durations = {s: 0.0 for s in STATES}
            self._current_state = np.random.choice([1, 2, 3])
            self._current_time = 0.0
            self._transition_id = 0
            self._sim_days = sim_days
            self._log_rows = []

        self._setup_axes()
        self._btn_start.config(state="disabled")
        self._btn_stop.config(state="normal")
        self._btn_save.config(state="disabled")
        self._stop_flag.clear()
        self._sim_running = True
        self._sim_thread = threading.Thread(target=self._sim_worker, args=(Q, sim_days, delay, freq), daemon=True)
        self._sim_thread.start()

    def _stop_sim(self):
        self._stop_flag.set()

    def _resume_sim(self):
        try:
            Q = self._read_Q()
        except ValueError as e:
            messagebox.showerror("Ошибка матрицы", str(e))
            return
        err = validate_Q(Q)
        if err:
            messagebox.showerror("Ошибка матрицы Q", err)
            return

        try:
            delay = float(self._delay_var.get())
            freq = int(self._freq_var.get())
            assert delay >= 0 and freq >= 1
        except Exception:
            messagebox.showerror("Ошибка параметров", "Задержка ≥ 0, Частота ≥ 1 (целое)")
            return
        with self._lock:
            sim_days = self._sim_days

        self._btn_start.config(state="disabled")
        self._btn_stop.config(state="normal")
        self._btn_resume.config(state="disabled")
        self._btn_save.config(state="disabled")
        self._stop_flag.clear()
        self._sim_running = True
        self._sim_thread = threading.Thread(target=self._sim_worker, args=(Q, sim_days, delay, freq), daemon=True)
        self._sim_thread.start()

    def _save_csv(self):
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV файлы", "*.csv"), ("Все файлы", "*.*")], initialfile="weather_log.csv", title="Сохранить лог симуляции")
        if not path:
            return
        with self._lock:
            rows = list(self._log_rows)
            durations = dict(self._durations)
            pi = self._pi_theor.copy()
            tid = self._transition_id

        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(["transition_id", "time_start", "time_end", "duration_days", "state_id", "state_name", "timestamp_real"])
            w.writerows(rows)
        summary_path = os.path.splitext(path)[0] + "_summary.csv"
        total = sum(durations.values()) or 1
        emp = [durations[s] / total for s in STATES]

        with open(summary_path, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(["state_id", "state_name", "total_days", "empirical_prob", "theoretical_prob", "delta"])
            for idx, s in enumerate(STATES):
                w.writerow([s, STATES[s], f"{durations[s]:.4f}", f"{emp[idx]:.6f}", f"{pi[idx]:.6f}", f"{emp[idx] - pi[idx]:+.6f}"])
        messagebox.showinfo("Сохранено", f"Лог: {path}\nСводка: {summary_path}")

    def _sim_worker(self, Q, sim_days, delay, freq):
        with self._lock:
            state = self._current_state
            t = self._current_time
            tid = self._transition_id

        while t < sim_days and not self._stop_flag.is_set():
            new_state, dwell = next_event(state, Q)
            actual = min(dwell, sim_days - t)
            t_start = t
            t += actual
            tid += 1
            log_row = [tid, f"{t_start:.4f}", f"{t:.4f}", f"{actual:.4f}", state, STATES[state], datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]]

            with self._lock:
                self._durations[state] += actual
                self._current_state = new_state
                self._current_time = t
                self._transition_id = tid
                self._states_hist.append(state)
                self._times.append(t)
                self._log_rows.append(log_row)

            state = new_state
            if tid % freq == 0 or t >= sim_days or self._stop_flag.is_set():
                self.after(0, self._refresh_plots)
                time.sleep(delay)
        self.after(0, self._on_sim_done)

    def _refresh_plots(self):
        with self._lock:
            times = list(self._times)
            states_h = list(self._states_hist)
            durations = dict(self._durations)
            cur_state = self._current_state
            cur_time = self._current_time
            tid = self._transition_id
            sim_days = self._sim_days
            pi = self._pi_theor.copy()

        total = sum(durations.values()) or 1
        emp = [durations[s] / total for s in STATES]
        self._draw_timeline(times, states_h, sim_days)
        self._draw_cmp(emp, list(pi), tid)
        self._draw_pie(emp)
        pct = cur_time / sim_days * 100
        self._status_var.set(f"День: {cur_time:.1f} / {sim_days:.0f}  ({pct:.0f}%) | Переход: {tid} | {STATES[cur_state]}")
        self._canvas.draw_idle()

    def _draw_timeline(self, times, states_h, total_time):
        ax = self._ax_tl
        ax.clear()
        ax.set_facecolor("#F7F7F7")

        if states_h:
            t_starts = [times[i] for i in range(len(states_h))]
            t_ends = [times[i + 1] if i + 1 < len(times) else times[-1] for i in range(len(states_h))]
            for i in range(len(states_h)):
                ax.axvspan(t_starts[i], t_ends[i], color=STATE_COLORS[states_h[i]], alpha=0.30, linewidth=0)
            step_x = []
            step_y = []
            for i in range(len(states_h)):
                step_x += [t_starts[i], t_ends[i]]
                step_y += [states_h[i], states_h[i]]
            ax.plot(step_x, step_y, color="#1A1A1A", linewidth=1.4, solid_joinstyle="miter", zorder=3)
            for i in range(len(states_h) - 1):
                ax.plot([t_ends[i], t_ends[i]], [states_h[i], states_h[i + 1]], color="#1A1A1A", linewidth=1.4, zorder=3)

        ax.set_xlim(0, total_time)
        ax.set_ylim(0.5, 3.5)
        ax.set_yticks([1, 2, 3])
        ax.set_yticklabels([STATES[s] for s in STATES], fontsize=8)
        ax.set_xlabel("Время (дни)", fontsize=9, color="#444")
        ax.set_title("Хронология смены погоды", fontsize=10, fontweight="bold", color="#1A1A1A", pad=5)
        ax.tick_params(colors="#555", labelsize=8)
        patches = [mpatches.Patch(color=STATE_COLORS[s], label=STATES[s]) for s in STATES]
        ax.legend(handles=patches, loc="upper right", fontsize=8, framealpha=0.8)

    def _draw_cmp(self, emp, theor, tid):
        ax = self._ax_cmp
        ax.clear()
        ax.set_facecolor("#F7F7F7")
        x = np.arange(3)
        width = 0.35
        labels = [STATES[s] for s in STATES]
        colors = [STATE_COLORS[s] for s in STATES]
        bars_e = ax.bar(x - width / 2, emp, width, color=colors, edgecolor="white", linewidth=1.2, label="Эмпирика", alpha=0.90)
        bars_t = ax.bar(x + width / 2, theor, width, color=colors, edgecolor="#555", linewidth=1.2, label="Теория", alpha=0.45, hatch="///")

        for bar, v in zip(bars_e, emp):
            ax.text(bar.get_x() + bar.get_width() / 2, v + 0.013, f"{v:.3f}", ha="center", va="bottom", fontsize=8, fontweight="bold", color="#1A1A1A")
        for bar, v in zip(bars_t, theor):
            ax.text(bar.get_x() + bar.get_width() / 2, v + 0.013, f"{v:.3f}", ha="center", va="bottom", fontsize=8, color="#444")

        ax.set_xticks(x)
        ax.set_xticklabels(labels, fontsize=8)
        ax.set_ylim(0, 1.05)
        ax.set_title(f"Эмпирика и теория  (N = {tid})", fontsize=9, fontweight="bold", color="#1A1A1A", pad=5)
        ax.set_ylabel("Вероятность", fontsize=8, color="#444")
        ax.tick_params(colors="#555", labelsize=8)
        ax.legend(fontsize=8, framealpha=0.8)

    def _draw_pie(self, emp_vals):
        ax = self._ax_pie
        ax.clear()
        ax.set_facecolor("#F7F7F7")
        colors = [STATE_COLORS[s] for s in STATES]
        ax.pie(emp_vals, labels=[STATES[s] for s in STATES], colors=colors, autopct="%1.1f%%", startangle=90, wedgeprops={"edgecolor": "white", "linewidth": 1.5}, textprops={"fontsize": 8, "color": "#1A1A1A"})
        ax.set_title("Доли времени\n", fontsize=9, fontweight="bold", color="#1A1A1A", pad=5)

    def _on_sim_done(self):
        self._sim_running = False
        self._refresh_plots()
        with self._lock:
            t = self._current_time
            tid = self._transition_id
            sd = self._sim_days

        finished = t >= sd
        self._btn_start.config(state="normal")
        self._btn_stop.config(state="disabled")
        self._btn_resume.config(state="disabled" if finished else "normal")
        self._btn_save.config(state="normal")
        if finished:
            self._status_var.set(f"Смоделировано {sd:.0f} дней, переходов: {tid}.")
        else:
            self._status_var.set(f"Остановлено на {t:.1f} / {sd:.0f}  ({t/sd*100:.0f}%),  переходов: {tid}.")

    def _on_close(self):
        self._stop_flag.set()
        self.destroy()

if __name__ == "__main__":
    app = WeatherApp()
    app.mainloop()