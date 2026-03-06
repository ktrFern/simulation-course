import tkinter as tk
from tkinter import ttk
import random

C = 12
WIDTH = 80
HEIGHT = 60
EMPTY = 0
TREE = 1
BURNING = 2
WATER = 3

NEIGHBORS = [(-1,-1), (0,-1), (1,-1), (-1,0), (1,0), (-1,1), (0,1), (1,1)]

class WindCompass:
    def __init__(self,parent,callback):
        self.callback = callback
        self.size = 120
        self.center = self.size // 2
        self.radius = 42

        self.canvas = tk.Canvas(parent, width=self.size, height=self.size)
        self.canvas.pack(pady=5)
        self.canvas.create_oval(self.center-self.radius, self.center-self.radius, self.center+self.radius, self.center+self.radius)
        self.arrow = self.canvas.create_line(self.center,self.center, self.center, self.center-self.radius, width=3, arrow=tk.LAST)
        self.canvas.create_text(self.center, 10, text="N")
        self.canvas.create_text(self.size-10, self.center, text="E")
        self.canvas.create_text(self.center, self.size-10, text="S")
        self.canvas.create_text(10, self.center, text="W")

        self.canvas.bind("<Button-1>", self.set_wind)
        self.canvas.bind("<B1-Motion>", self.set_wind)

    def set_wind(self,event):
        dx = event.x - self.center
        dy = event.y - self.center
        dist = (dx * dx + dy * dy) ** 0.5

        if dist == 0: return
        if dist > self.radius:
            dx = dx / dist * self.radius
            dy = dy / dist * self.radius
            dist = self.radius

        self.canvas.coords(self.arrow, self.center, self.center, self.center+dx, self.center+dy)
        wx = dx / dist
        wy = dy / dist
        strength = dist / self.radius
        self.callback((wx, wy, strength))

class ForestFireApp:
    def __init__(self,root):
        self.root = root
        self.root.title("Симулятор лесного пожара")
        self.running = False
        self.after_id = None

        self.wind_vec = (0, 0)
        self.wind_strength = 0
        self.grid = [[EMPTY for _ in range(WIDTH)] for _ in range(HEIGHT)]
        self.burn_time = [[0 for _ in range(WIDTH)] for _ in range(HEIGHT)]
        self.tree_type = [[0 for _ in range(WIDTH)] for _ in range(HEIGHT)]

        self.tree_types = {1: {"burn": 3, "prob": 0.7, "color": "#2e7d32"}, 2: {"burn": 2, "prob": 0.9, "color": "#388e3c"}, 3: {"burn": 5, "prob": 0.4, "color": "#1b5e20"}}
        self.tree_keys = list(self.tree_types.keys())
        self.create_ui()
        self.rects = [[None for _ in range(WIDTH)] for _ in range(HEIGHT)]
        self.init_grid_graphics()
        self.draw()

    def create_ui(self):
        panel = ttk.Frame(self.root)
        panel.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)

        left_col = ttk.Frame(panel)
        left_col.pack(side=tk.LEFT, fill=tk.Y, padx=5)
        right_col = ttk.Frame(panel)
        right_col.pack(side=tk.LEFT, fill=tk.Y, padx=5)

        params = ttk.LabelFrame(left_col, text="Основные параметры")
        params.pack(fill="x", pady=5)
        self.grow_prob = self.add_spin(params,"Рост деревьев",0,0.1,0.001,0.01)
        self.ignite_prob = self.add_spin(params,"Самовозгорание",0,0.01,0.0001,0.001)
        self.fire_prob = self.add_spin(params,"Распространение огня",0,1,0.05,0.4)
        self.rain_extinguish = self.add_spin(params,"Тушение дождём",0,0.2,0.01,0.01)
        self.puddle_prob = self.add_spin(params,"Образование луж",0,0.01,0.001,0.0001)
        self.speed = self.add_spin(params,"Задержка (мс)",10,500,10,60)

        map_frame = ttk.LabelFrame(left_col, text="Генерация карты")
        map_frame.pack(fill="x", pady=5)
        self.forest_density = self.add_spin(map_frame,"Плотность леса",0,1,0.05,0.65)
        self.rivers = self.add_spin(map_frame, "Количество рек", 0, 10, 1, 2)
        self.lakes = self.add_spin(map_frame, "Количество озер", 0, 10, 1, 3)

        tool_frame = ttk.LabelFrame(left_col, text="Инструменты")
        tool_frame.pack(fill="x", pady=5)
        self.tool_var = tk.StringVar(value="tree")
        tools = {"tree": "Дерево", "fire": "Огонь", "water": "Вода", "erase": "Пустота"}
        for key,name in tools.items(): ttk.Radiobutton(tool_frame,text=name,value=key,variable=self.tool_var).pack(anchor="w")

        wind_frame = ttk.LabelFrame(right_col, text="Погода")
        wind_frame.pack(fill="x", pady=5)
        self.compass = WindCompass(wind_frame, self.set_wind)
        self.wind_enabled = tk.BooleanVar()
        ttk.Checkbutton(wind_frame, text="Ветер", variable=self.wind_enabled).pack()
        self.rain_var = tk.BooleanVar()
        ttk.Checkbutton(wind_frame, text="Дождь", variable=self.rain_var).pack()

        btn_frame = ttk.Frame(right_col)
        btn_frame.pack(fill="x", pady=10)
        ttk.Button(btn_frame, text="Старт", command=self.start).pack(fill="x")
        ttk.Button(btn_frame, text="Стоп", command=self.stop).pack(fill="x")
        ttk.Button(btn_frame, text="Шаг", command=self.step_once).pack(fill="x")
        ttk.Button(btn_frame, text="Случайная карта", command=self.random_forest).pack(fill="x")
        ttk.Button(btn_frame, text="Очистить", command=self.reset).pack(fill="x")
        ttk.Button(btn_frame, text="Закрыть", command=self.root.destroy).pack(fill="x")

        self.canvas = tk.Canvas(self.root, width=WIDTH*C, height=HEIGHT*C, bg="#1e1e1e", highlightthickness=0)
        self.canvas.pack(side=tk.RIGHT)
        self.canvas.bind("<Button-1>", self.paint)
        self.canvas.bind("<B1-Motion>", self.paint)

    def add_spin(self,parent,label,start,end,step,default):
        ttk.Label(parent, text=label).pack(anchor="w")
        var = tk.DoubleVar(value=default)
        ttk.Spinbox(parent, from_=start, to=end, increment=step, textvariable=var).pack(fill="x",pady=2)
        return var

    def init_grid_graphics(self):
        for y in range(HEIGHT):
            for x in range(WIDTH):
                rect = self.canvas.create_rectangle(x*C, y*C, (x+1)*C, (y+1)*C, fill="#1e1e1e", outline="")
                self.rects[y][x] = rect

    def set_wind(self,vec):
        wx,wy,strength = vec
        self.wind_vec = (wx, wy)
        self.wind_strength = strength

    def start(self):
        self.running = True
        self.run()

    def stop(self):
        self.running = False
        if self.after_id: self.root.after_cancel(self.after_id)

    def run(self):
        if self.running: self.step()
        delay = int(self.speed.get())
        self.after_id = self.root.after(delay, self.run)

    def step_once(self):
        self.stop()
        self.step()

    def random_forest(self):
        self.stop()
        for y in range(HEIGHT):
            for x in range(WIDTH):
                self.grid[y][x] = EMPTY
                self.tree_type[y][x] = 0

        river_count = int(self.rivers.get())

        for _ in range(river_count):
            direction = random.choice(["down","up","left","right"])
            if direction == "down":
                x = random.randint(0, WIDTH - 1)
                y = 0
                dx, dy = 0, 1

            elif direction == "up":
                x = random.randint(0, WIDTH - 1)
                y = HEIGHT - 1
                dx, dy = 0, -1

            elif direction == "right":
                x = 0
                y = random.randint(0, HEIGHT - 1)
                dx, dy = 1, 0

            else:
                x = WIDTH - 1
                y = random.randint(0, HEIGHT - 1)
                dx, dy = -1, 0

            while 0 <= x < WIDTH and 0 <= y < HEIGHT:
                self.grid[y][x] = WATER
                if dx == 0:
                    if x + 1 < WIDTH:
                        self.grid[y][x + 1] = WATER
                    if x - 1 >= 0:
                        self.grid[y][x - 1] = WATER

                else:
                    if y + 1 < HEIGHT:
                        self.grid[y + 1][x] = WATER
                    if y - 1 >= 0:
                        self.grid[y - 1][x] = WATER

                if dx == 0: x += random.choice([-1, 0, 1])

                else: y += random.choice([-1, 0, 1])

                x += dx
                y += dy

        lake_count = int(self.lakes.get())

        for _ in range(lake_count):
            cx = random.randint(0, WIDTH - 1)
            cy = random.randint(0, HEIGHT - 1)
            radius = random.randint(3,7)

            for yy in range(cy - radius, cy + radius):
                for xx in range(cx - radius, cx + radius):
                    if 0 <= xx < WIDTH and 0 <= yy < HEIGHT:
                        if (xx - cx) ** 2 + (yy - cy) ** 2 < radius * radius: self.grid[yy][xx] = WATER

        forest_density = self.forest_density.get()

        for y in range(HEIGHT):
            for x in range(WIDTH):
                if self.grid[y][x] != EMPTY: continue
                if random.random() < forest_density:
                    t = random.choice(self.tree_keys)
                    self.grid[y][x] = TREE
                    self.tree_type[y][x] = t

        self.draw()

    def reset(self):
        self.stop()
        for y in range(HEIGHT):
            for x in range(WIDTH):
                self.grid[y][x] = EMPTY
                self.burn_time[y][x] = 0
                self.tree_type[y][x] = 0
        self.draw()

    def paint(self,event):
        x = event.x // C
        y = event.y // C
        if not (0 <= x < WIDTH and 0 <= y < HEIGHT): return
        tool = self.tool_var.get()

        if tool == "tree":
            t = random.choice(self.tree_keys)
            self.grid[y][x] = TREE
            self.tree_type[y][x] = t

        elif tool == "fire":
            if self.grid[y][x] == TREE:
                t = self.tree_type[y][x]
                self.grid[y][x] = BURNING
                self.burn_time[y][x] = self.tree_types[t]["burn"]

        elif tool == "water": self.grid[y][x] = WATER

        elif tool == "erase": self.grid[y][x] = EMPTY

        self.update_cell(x,y)

    def step(self):
        new_grid = [row[:] for row in self.grid]
        new_burn = [row[:] for row in self.burn_time]

        if self.wind_enabled.get():
            wx,wy = self.wind_vec
            wind_strength = self.wind_strength
        else:
            wx,wy = 0,0
            wind_strength = 0

        fire_prob = self.fire_prob.get()
        grow_prob = self.grow_prob.get()
        ignite_prob = self.ignite_prob.get()
        rain = self.rain_var.get()
        puddle_prob = self.puddle_prob.get()

        for y in range(HEIGHT):
            for x in range(WIDTH):
                cell = self.grid[y][x]
                if rain and cell == EMPTY:
                    if random.random() < puddle_prob: new_grid[y][x] = WATER

                if cell == TREE:
                    if random.random() < ignite_prob:
                        t = self.tree_type[y][x]
                        new_grid[y][x] = BURNING
                        new_burn[y][x] = self.tree_types[t]["burn"]
                        continue

                    for dx,dy in NEIGHBORS:
                        nx = x + dx
                        ny = y + dy
                        if 0 <= nx < WIDTH and 0 <= ny < HEIGHT:
                            if self.grid[ny][nx] == BURNING:
                                t = self.tree_type[y][x]
                                base = fire_prob * self.tree_types[t]["prob"]
                                wind = (-dx * wx - dy * wy) * wind_strength * 1.5

                                if wind < 0: wind *= 0.3
                                prob = max(0, min(base + wind, 1))
                                if rain: prob *= 0.3
                                if random.random() < prob:
                                    new_grid[y][x] = BURNING
                                    new_burn[y][x] = self.tree_types[t]["burn"]
                                    break

                elif cell == BURNING:
                    if rain and random.random() < self.rain_extinguish.get():
                        new_grid[y][x] = EMPTY
                        continue
                    new_burn[y][x] -= 1
                    if new_burn[y][x] <= 0:
                        new_grid[y][x] = EMPTY

                elif cell == EMPTY:
                    grow = grow_prob
                    if rain:
                        grow *= 1.8
                    if random.random() < grow:
                        t = random.choice(self.tree_keys)
                        new_grid[y][x] = TREE
                        self.tree_type[y][x] = t

        self.grid = new_grid
        self.burn_time = new_burn
        self.draw()

    def update_cell(self,x,y):
        cell = self.grid[y][x]
        if cell == TREE: color = self.tree_types[self.tree_type[y][x]]["color"]
        elif cell == BURNING: color = "#ff6b3d"
        elif cell == WATER: color = "#1565c0"
        else: color = "#1e1e1e"
        self.canvas.itemconfig(self.rects[y][x],fill=color)

    def draw(self):
        for y in range(HEIGHT):
            for x in range(WIDTH):
                cell = self.grid[y][x]
                if cell == TREE: color = self.tree_types[self.tree_type[y][x]]["color"]
                elif cell == BURNING: color = "#ff6b3d"
                elif cell == WATER: color = "#1565c0"
                else: color = "#1e1e1e"
                self.canvas.itemconfig(self.rects[y][x],fill=color)

root = tk.Tk()
app = ForestFireApp(root)
root.mainloop()