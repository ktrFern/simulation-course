import tkinter as tk
from tkinter import ttk
import random
import math

class CoinCanvas:
    def __init__(self, parent):
        self.parent = parent
        self.canvas = tk.Canvas(parent, width=220, height=220, bg='#f0f0f0', highlightthickness=0)
        self.canvas.pack(anchor="center")
        self.cx, self.cy = 110, 110
        self.radius = 60
        self.animating = False
        self.frame = 0
        self.max_frames = 15
        self.result = None
        self.pending = None
        self.callback = None
        self._draw()

    def _draw(self):
        self.canvas.delete("all")
        scale = abs(math.cos(self.frame * math.pi / 8)) if self.animating else 1
        width = self.radius * scale
        if width > 5:
            self.canvas.create_oval(self.cx - width, self.cy - self.radius, self.cx + width, self.cy + self.radius, fill='#FFD700', outline='#DAA520', width=3)
            self.canvas.create_oval(self.cx - width + 10, self.cy - self.radius + 10, self.cx + width - 10, self.cy + self.radius - 10, fill='#FFC700')
            if not self.animating:
                text = "?" if self.result is None else "ДА" if self.result else "НЕТ"
                font_size = 48 if self.result is None else (32 if self.result else 28)
                self.canvas.create_text(self.cx, self.cy, text=text, font=("Arial", font_size, "bold"), fill="#B8860B")
        else:
            self.canvas.create_rectangle(self.cx - 5, self.cy - self.radius, self.cx + 5, self.cy + self.radius, fill='#DAA520')

    def start(self, result=None, callback=None):
        self.pending, self.callback = result, callback
        self.animating, self.frame, self.result = True, 0, None
        self._animate()

    def _animate(self):
        if self.frame < self.max_frames:
            self.frame += 1
            self._draw()
            self.canvas.after(100, self._animate)
        else:
            self.animating = False
            self.frame = 0
            if self.pending is not None:
                self.result = self.pending
            self._draw()
            if self.callback:
                self.callback()

    def show(self, result):
        self.result = result
        self._draw()

    def reset(self):
        self.result = self.pending = self.callback = None
        self.animating = False
        self.frame = 0
        self._draw()

class BallCanvas:
    def __init__(self, parent):
        self.parent = parent
        self.canvas = tk.Canvas(parent, width=300, height=300, bg='#f0f0f0', highlightthickness=0)
        self.canvas.pack(anchor="center")
        self.cx, self.cy, self.radius = 150, 150, 120
        self.offset_x = self.offset_y = self.rotation = 0
        self.showing = False
        self.answer = ""
        self.pending = None
        self.callback = None
        self._draw()

    def _draw(self):
        self.canvas.delete("all")
        cx, cy = self.cx + self.offset_x, self.cy + self.offset_y
        self.canvas.create_oval(cx - self.radius + 15, cy - self.radius + 15, cx + self.radius - 15, cy + self.radius - 15, fill='#1a1a1a', outline='#0a0a0a', width=3)
        self.canvas.create_oval(cx - self.radius + 25, cy - self.radius + 25, cx + self.radius - 25, cy + self.radius - 25, fill='#2a2a2a')
        if not self.showing:
            r = 65
            self.canvas.create_oval(cx - r, cy - r, cx + r, cy + r, fill='white', outline='#cccccc', width=2)
            self.canvas.create_text(cx, cy, text="8", font=("Arial", 64, "bold"), fill="black")
        else:
            self._draw_answer(cx, cy)

    def _draw_answer(self, cx, cy):
        r = 65
        self.canvas.create_oval(cx - r, cy - r, cx + r, cy + r, fill='black', outline='#333333', width=2)
        lines = self._wrap(self.answer, 2 * (r - 10), max_lines=3)
        h, start = 14, cy - (len(lines) - 1) * 7
        for i, line in enumerate(lines):
            fs = 8 if len(lines) > 1 else 9
            self.canvas.create_text(cx, start + i * h, text=line, font=("Arial", fs, "bold"), fill="#aaccff", justify="center")

    def _wrap(self, text, max_w, max_lines=3):
        words, lines, cur = text.split(), [], ""
        for w in words:
            test = cur + (" " if cur else "") + w
            if len(test) * 7 <= max_w:
                cur = test
            else:
                if cur: lines.append(cur)
                cur = w
                if len(lines) >= max_lines: break
        if cur and len(lines) < max_lines: lines.append(cur)
        return lines[:max_lines]

    def start(self, answer=None, callback=None):
        self.pending, self.callback = answer, callback
        self.frame, self.max_frames = 0, 20
        self._animate()

    def _animate(self):
        if self.frame < self.max_frames:
            self.offset_x, self.offset_y = random.randint(-20, 20), random.randint(-15, 15)
            self.rotation = random.randint(-5, 5)
            self._draw()
            self.frame += 1
            self.max_frames = 20 - self.frame // 2
            self.canvas.after(80, self._animate)
        else:
            self.offset_x = self.offset_y = self.rotation = 0
            self.showing = True
            if self.pending: self.answer = self.pending
            self._draw()
            if self.callback: self.callback()

    def show(self, answer):
        self.answer, self.showing = answer, True
        self._draw()

    def reset(self):
        self.showing = False
        self.answer = self.pending = self.callback = None
        self.offset_x = self.offset_y = 0
        self._draw()

class App:
    def __init__(self, root):
        self.root = root
        root.title("Моделирование случайных событий")
        root.geometry("750x700")
        self.mode = tk.IntVar(value=1)
        self.default_q = "Пойти сегодня в университет?"
        self.show_stats = False
        self._setup_ui()
        self._init_stats()
        self.cur_mode = 1
        self._switch()

    def _setup_ui(self):
        left = ttk.LabelFrame(root, text="Выбор задания")
        left.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)
        right = ttk.Frame(root, width=450)
        right.pack(side=tk.RIGHT, fill=tk.BOTH, padx=(0, 10), pady=10)
        right.pack_propagate(False)
        rf = ttk.Frame(left)
        rf.pack(pady=10, fill="x")

        ttk.Radiobutton(rf, text="Скажи Да или Нет", variable=self.mode, value=1, command=self._switch).pack(anchor="w")
        ttk.Radiobutton(rf, text="Шар предсказаний", variable=self.mode, value=2, command=self._switch).pack(anchor="w")
        ttk.Separator(left).pack(fill="x", pady=10)
        ttk.Label(left, text="Ваш вопрос:").pack(anchor="w")
        self.q_entry = ttk.Entry(left, width=45)
        self.q_entry.pack(fill="x", pady=5)
        self.q_entry.insert(0, self.default_q)
        bf = ttk.Frame(left)
        bf.pack(fill="x", pady=10)

        self.btn_action = ttk.Button(bf, command=self._run)
        self.btn_action.pack(fill="x", pady=2)
        ttk.Button(bf, text="Статистика", command=self._toggle_stats).pack(fill="x", pady=2)
        ttk.Button(bf, text="Очистить", command=self._clear_stats).pack(fill="x", pady=2)
        ttk.Button(bf, text="Закрыть", command=self.root.destroy).pack(fill="x", pady=2)
        ttk.Separator(left).pack(fill="x", pady=10)

        self.stats_frame = ttk.Frame(left)
        self.stats_frame.pack(fill="both", expand=True, pady=5)
        cols = ('event', 'nk', 'pk')
        self.tree = ttk.Treeview(self.stats_frame, columns=cols, show='headings', height=12)
        self.tree.heading('event', text='Событие')
        self.tree.heading('nk', text='nk')
        self.tree.heading('pk', text='pk')
        self.tree.column('event', width=200)
        self.tree.column('nk', width=50, anchor="center")
        self.tree.column('pk', width=70, anchor="center")
        sb = ttk.Scrollbar(self.stats_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side=tk.LEFT, fill="both", expand=True)
        sb.pack(side=tk.RIGHT, fill="y")
        self.tree.pack_forget()
        sb.pack_forget()

        center = ttk.Frame(right)
        center.pack(expand=True, fill="both")
        self.anim_frame = ttk.Frame(center)
        self.anim_frame.pack(pady=20, anchor="center")
        self.res_frame = ttk.Frame(center)
        self.res_frame.pack(pady=10, anchor="center")
        self.lbl_res = ttk.Label(self.res_frame, text="", font=("Arial", 16, "bold"), foreground="blue", wraplength=350, justify="center")
        self.lbl_res.pack(pady=5)
        self.lbl_alpha = ttk.Label(self.res_frame, text="", font=("Courier", 9), foreground="gray", wraplength=350, justify="center")
        self.lbl_alpha.pack(pady=2)

    def _init_stats(self):
        self.yes_stats = {"ДА": 0, "НЕТ": 0}
        self.yes_total = 0
        self.ball_events = self._get_events()
        self.ball_stats = {i: 0 for i in range(len(self.ball_events))}
        self.ball_total = 0

    def _select_event_subtract(self, alpha, events):
        A = alpha
        for k, ev in enumerate(events):
            A -= ev["prob"]
            if A <= 0:
                return k
        return len(events) - 1

    def _toggle_stats(self):
        self.show_stats = not self.show_stats
        if self.show_stats:
            self.tree.pack(side=tk.LEFT, fill="both", expand=True)
            for w in self.stats_frame.winfo_children():
                if isinstance(w, ttk.Scrollbar): w.pack(side=tk.RIGHT, fill="y")
            self._upd_stats()
            self._set_stats_btn_text("Скрыть статистику")
        else:
            self.tree.pack_forget()
            for w in self.stats_frame.winfo_children():
                if isinstance(w, ttk.Scrollbar): w.pack_forget()
            self._set_stats_btn_text("Статистика")

    def _set_stats_btn_text(self, text):
        for btn in self._find_buttons():
            if btn.cget("text") in ("Статистика", "Скрыть статистику"):
                btn.config(text=text)
                break

    def _find_buttons(self):
        buttons = []
        for child in self.root.winfo_children():
            if isinstance(child, ttk.LabelFrame) and child.cget("text") == "Выбор задания":
                for w in child.winfo_children():
                    if isinstance(w, ttk.Frame):
                        for b in w.winfo_children():
                            if isinstance(b, ttk.Button):
                                buttons.append(b)
        return buttons

    def _clear_stats(self):
        if self.cur_mode == 1:
            self.yes_stats = {"ДА": 0, "НЕТ": 0}
            self.yes_total = 0
        else:
            self.ball_stats = {i: 0 for i in range(len(self.ball_events))}
            self.ball_total = 0
        self._upd_stats()
        self.lbl_alpha.config(text="Статистика очищена")

    def _switch(self):
        for w in self.anim_frame.winfo_children(): w.destroy()
        if self.mode.get() == 1:
            self.cur_mode = 1
            self.btn_action.config(text="Подбросить монетку")
            self.q_entry.delete(0, tk.END)
            self.q_entry.insert(0, self.default_q)
            self.coin = CoinCanvas(self.anim_frame)
            self.lbl_res.config(text="", foreground="blue")
        else:
            self.cur_mode = 2
            self.btn_action.config(text="Потрясти шар")
            self.q_entry.delete(0, tk.END)
            self.q_entry.insert(0, self.default_q)
            self.ball = BallCanvas(self.anim_frame)
            self.lbl_res.config(text="", foreground="#1a3a6c")
        self.lbl_alpha.config(text="")
        self._upd_stats()

    def _run(self):
        alpha = random.random()
        if self.cur_mode == 1:
            self.coin.reset()
            self.lbl_res.config(text="", foreground="blue")
            self.lbl_alpha.config(text="")
            p = 0.5
            if alpha < p:
                res_text, result, color = "ДА!", True, "#22aa22"
                self.yes_stats["ДА"] += 1
            else:
                res_text, result, color = "НЕТ!", False, "#cc3333"
                self.yes_stats["НЕТ"] += 1
            self.yes_total += 1
            alpha_txt = f"α: {alpha:.4f} | p: {p} | N: {self.yes_total}"
            def on_done():
                self.coin.show(result)
                self.lbl_res.config(text=res_text, foreground=color)
                self.lbl_alpha.config(text=alpha_txt)
                if self.show_stats: self._upd_stats()
            self.coin.start(result=result, callback=on_done)
        else:
            self.ball.reset()
            self.lbl_res.config(text="", foreground="#1a3a6c")
            self.lbl_alpha.config(text="")
            idx = self._select_event_subtract(alpha, self.ball_events)
            self.ball_stats[idx] += 1
            self.ball_total += 1
            res_text = self.ball_events[idx]["text"]
            alpha_txt = f"α: {alpha:.4f} | N: {self.ball_total}"
            def on_done():
                self.ball.show(res_text)
                self.lbl_res.config(text=res_text)
                self.lbl_alpha.config(text=alpha_txt)
                if self.show_stats: self._upd_stats()
            self.ball.start(answer=res_text, callback=on_done)

    def _upd_stats(self):
        for item in self.tree.get_children(): self.tree.delete(item)
        if self.cur_mode == 1:
            for ev in ["ДА", "НЕТ"]:
                nk = self.yes_stats[ev]
                pk = nk / self.yes_total if self.yes_total else 0
                self.tree.insert('', "end", values=(ev, nk, f"{pk:.4f}"))
        else:
            for i, ev in enumerate(self.ball_events):
                nk = self.ball_stats[i]
                pk = nk / self.ball_total if self.ball_total else 0
                self.tree.insert('', "end", values=(ev['text'], nk, f"{pk:.4f}"))

    def _get_events(self):
        texts = ["Это бесспорно",
                 "Определенно да",
                 "Знаки указывают, что да",
                 "Мои источники говорят да",
                 "ДА!",
                 "Перспектива хорошая",
                 "Да",
                 "Наиболее вероятно",
                 "Определенно нет",
                 "Я так не думаю",
                 "Знаки указывают, что нет",
                 "Мои источники говорят нет",
                 "НЕТ!",
                 "Извини, нет",
                 "Перспектива не очень хорошая",
                 "Очень сомневаюсь",
                 "Не могу сейчас сказать",
                 "Будущее туманно, спроси позже",
                 "Соберись с мыслями и спроси снова",
                 "Лучше тебе не говорить сейчас"]
        return [{"text": t, "prob": 0.05} for t in texts]

if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()