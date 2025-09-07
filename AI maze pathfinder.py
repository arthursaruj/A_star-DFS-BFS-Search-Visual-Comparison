
import tkinter as tk
from tkinter import ttk, messagebox
import random
import time

# Config 
CANVAS_SIZE = 800        # pixels 
DEFAULT_N   = 30         # grid size NxN
MIN_N, MAX_N = 10, 80
WALL_PROB   = 0.28       # for random maze
BG = "#0e1520"
COLOR_EMPTY = "#152231"
COLOR_WALL  = "#2b394a"
COLOR_OPEN  = "#1e3f58"
COLOR_CLOSED= "#23344a"
COLOR_PATH  = "#4fd1c5"
COLOR_START = "#7ee081"
COLOR_GOAL  = "#ffb366"
GRID_LINE   = "#0f1a26"

#Helpers
def manhattan(a, b):
    return abs(a[0]-b[0]) + abs(a[1]-b[1])

def in_bounds(x, y, n):
    return 0 <= x < n and 0 <= y < n

def neighbors4(x, y, grid):
    n = len(grid)
    cand = []
    if y > 0:      cand.append((x, y-1))
    if x > 0:      cand.append((x-1, y))
    if x < n-1:    cand.append((x+1, y))
    if y < n-1:    cand.append((x, y+1))
    return [p for p in cand if grid[p[1]][p[0]] == 0]

def reconstruct_path(came_from, start, goal):
    if goal not in came_from and goal != start:
        return []
    path = [goal]
    cur = goal
    while cur != start:
        cur = came_from.get(cur)
        if cur is None:
            return []
        path.append(cur)
    path.reverse()
    return path

# Algorithms as generators
def bfs_gen(grid, start, goal):
    from collections import deque
    q = deque([start])
    seen = {start}
    came = {}
    visited = 0
    steps = 0
    while q:
        cur = q.popleft()
        visited += 1
        if cur == goal:
            path = reconstruct_path(came, start, goal)
            yield {"label":"BFS","done":True,"fail":False,"visited":visited,"steps":steps,"path":path}
            return
        for nb in neighbors4(cur[0], cur[1], grid):
            if nb not in seen:
                seen.add(nb)
                came[nb] = cur
                q.append(nb)
        steps += 1
        yield {
            "label":"BFS","done":False,"open":set(q),
            "closed":set(seen),"came":came,"visited":visited,"steps":steps
        }
    yield {"label":"BFS","done":True,"fail":True,"visited":visited,"steps":steps,"path":[]}

def dfs_gen(grid, start, goal):
    st = [start]
    seen = {start}
    came = {}
    visited = 0
    steps = 0
    while st:
        cur = st.pop()
        visited += 1
        if cur == goal:
            path = reconstruct_path(came, start, goal)
            yield {"label":"DFS","done":True,"fail":False,"visited":visited,"steps":steps,"path":path}
            return
        for nb in neighbors4(cur[0], cur[1], grid):
            if nb not in seen:
                seen.add(nb)
                came[nb] = cur
                st.append(nb)
        steps += 1
        yield {
            "label":"DFS","done":False,"open":set(st),
            "closed":set(seen),"came":came,"visited":visited,"steps":steps
        }
    yield {"label":"DFS","done":True,"fail":True,"visited":visited,"steps":steps,"path":[]}

def A_star_gen(grid, start, goal):
    # f(n)=g(n)+h(n), Manhattan h is admissible for 4-way grids
    import heapq
    open_heap = []
    g = {start: 0}
    came = {}
    visited = 0
    steps = 0
    # heap items: (f, g, (x,y))
    heapq.heappush(open_heap, (manhattan(start, goal), 0, start))
    open_set = {start}
    closed = set()

    while open_heap:
        fcur, gcur, cur = heapq.heappop(open_heap)
        if cur in closed:
            continue
        open_set.discard(cur)
        closed.add(cur)
        visited += 1

        if cur == goal:
            path = reconstruct_path(came, start, goal)
            yield {"label":"A*","done":True,"fail":False,"visited":visited,"steps":steps,"path":path}
            return

        for nb in neighbors4(cur[0], cur[1], grid):
            tentative = gcur + 1
            if tentative < g.get(nb, float("inf")):
                g[nb] = tentative
                came[nb] = cur
                fnb = tentative + manhattan(nb, goal)
                heapq.heappush(open_heap, (fnb, tentative, nb))
                open_set.add(nb)

        steps += 1
        yield {
            "label":"A*","done":False,"open":set(open_set),
            "closed":set(closed),"came":came,"visited":visited,"steps":steps
        }

    yield {"label":"A*","done":True,"fail":True,"visited":visited,"steps":steps,"path":[]}

# Main Application
class App:
    def __init__(self, root):
        self.root = root
        root.title("Maze Pathfinding — BFS / DFS / A* (Tkinter)")

        # Top bar
        top = ttk.Frame(root, padding=8)
        top.pack(side=tk.TOP, fill=tk.X)

        ttk.Label(top, text="Algo").pack(side=tk.LEFT)
        self.algo = tk.StringVar(value="A_star")
        algo_menu = ttk.Combobox(top, textvariable=self.algo, width=10, state="readonly",
                                 values=["bfs","dfs","A_star"])
        algo_menu.pack(side=tk.LEFT, padx=6)

        ttk.Label(top, text="Grid").pack(side=tk.LEFT)
        self.n_var = tk.IntVar(value=DEFAULT_N)
        n_entry = ttk.Spinbox(top, from_=MIN_N, to=MAX_N, textvariable=self.n_var, width=5, command=self.resize_grid)
        n_entry.pack(side=tk.LEFT, padx=6)

        ttk.Label(top, text="Speed").pack(side=tk.LEFT)
        self.speed = tk.IntVar(value=30)  # frames per second
        speed_scale = ttk.Scale(top, from_=1, to=60, variable=self.speed, orient=tk.HORIZONTAL, length=150)
        speed_scale.pack(side=tk.LEFT, padx=6)

        ttk.Button(top, text="Run", command=self.run).pack(side=tk.LEFT, padx=4)
        ttk.Button(top, text="Step", command=self.step).pack(side=tk.LEFT, padx=4)
        ttk.Button(top, text="Clear", command=self.clear).pack(side=tk.LEFT, padx=4)
        ttk.Button(top, text="Random Maze", command=self.random_maze).pack(side=tk.LEFT, padx=4)

        self.stats = tk.StringVar(value="steps: 0 | visited: 0 | path: 0")
        ttk.Label(top, textvariable=self.stats).pack(side=tk.RIGHT)

        # Canvas
        self.canvas = tk.Canvas(root, width=CANVAS_SIZE, height=CANVAS_SIZE, bg=BG, highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        # Grid data
        self.N = self.n_var.get()
        self.grid = [[0]*self.N for _ in range(self.N)]
        self.cell = CANVAS_SIZE // self.N
        self.start = (1, 1)
        self.goal  = (self.N-2, self.N-2)

        # Input state
        self.dragging = False
        self.mode = "wall"  # wall|start|goal
        self.engine = None
        self.animating = False
        self.key_down = set()

        # Bindings
        self.canvas.bind("<ButtonPress-1>", self.on_left_down)
        self.canvas.bind("<B1-Motion>", self.on_left_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_left_up)
        self.canvas.bind("<ButtonPress-3>", self.on_right_down)
        self.canvas.bind("<B3-Motion>", self.on_right_drag)
        self.canvas.bind("<ButtonRelease-3>", self.on_right_up)
        root.bind("<KeyPress>", self.on_key_press)
        root.bind("<KeyRelease>", self.on_key_release)

        self.draw()

    # Drawing
    def draw(self, state=None):
        self.canvas.delete("all")
        n = self.N; c = self.cell

        # cells
        for y in range(n):
            for x in range(n):
                color = COLOR_WALL if self.grid[y][x]==1 else COLOR_EMPTY
                self.canvas.create_rectangle(x*c, y*c, (x+1)*c, (y+1)*c, fill=color, outline="")

        # overlays
        if state:
            if state.get("open"):
                for (x,y) in state["open"]:
                    self.canvas.create_rectangle(x*c, y*c, (x+1)*c, (y+1)*c, fill=COLOR_OPEN, outline="")
            if state.get("closed"):
                for (x,y) in state["closed"]:
                    self.canvas.create_rectangle(x*c, y*c, (x+1)*c, (y+1)*c, fill=COLOR_CLOSED, outline="")
            if state.get("path"):
                for (x,y) in state["path"]:
                    self.canvas.create_rectangle(x*c, y*c, (x+1)*c, (y+1)*c, fill=COLOR_PATH, outline="")
            self.stats.set(f"algo: {state.get('label','?')} | steps: {state.get('steps',0)} | visited: {state.get('visited',0)} | path: {len(state.get('path',[]))}")
        else:
            self.stats.set("steps: 0 | visited: 0 | path: 0")

        # start / goal
        sx, sy = self.start
        gx, gy = self.goal
        self.canvas.create_rectangle(sx*c, sy*c, (sx+1)*c, (sy+1)*c, fill=COLOR_START, outline="")
        self.canvas.create_rectangle(gx*c, gy*c, (gx+1)*c, (gy+1)*c, fill=COLOR_GOAL, outline="")

        # grid lines
        for i in range(n+1):
            self.canvas.create_line(i*c+0.5, 0, i*c+0.5, n*c, fill=GRID_LINE)
            self.canvas.create_line(0, i*c+0.5, n*c, i*c+0.5, fill=GRID_LINE)

    # Input handling
    def canvas_xy(self, event):
        x = event.x // self.cell
        y = event.y // self.cell
        return int(x), int(y)

    def on_left_down(self, event):
        x,y = self.canvas_xy(event)
        if not in_bounds(x,y,self.N): return
        if "s" in self.key_down:
            if self.grid[y][x] != 1:
                self.start = (x,y)
        elif "g" in self.key_down:
            if self.grid[y][x] != 1:
                self.goal = (x,y)
        else:
            if (x,y)!=self.start and (x,y)!=self.goal:
                self.grid[y][x] = 1
        self.dragging = True
        self.draw()

    def on_left_drag(self, event):
        if not self.dragging: return
        x,y = self.canvas_xy(event)
        if not in_bounds(x,y,self.N): return
        if "s" in self.key_down:
            if self.grid[y][x] != 1:
                self.start = (x,y)
        elif "g" in self.key_down:
            if self.grid[y][x] != 1:
                self.goal = (x,y)
        else:
            if (x,y)!=self.start and (x,y)!=self.goal:
                self.grid[y][x] = 1
        self.draw()

    def on_left_up(self, _):
        self.dragging = False

    def on_right_down(self, event):
        x,y = self.canvas_xy(event)
        if not in_bounds(x,y,self.N): return
        if (x,y)!=self.start and (x,y)!=self.goal:
            self.grid[y][x] = 0
        self.dragging = True
        self.draw()

    def on_right_drag(self, event):
        if not self.dragging: return
        x,y = self.canvas_xy(event)
        if not in_bounds(x,y,self.N): return
        if (x,y)!=self.start and (x,y)!=self.goal:
            self.grid[y][x] = 0
        self.draw()

    def on_right_up(self, _):
        self.dragging = False

    def on_key_press(self, event):
        k = event.keysym.lower()
        self.key_down.add(k)
        # 's' or 'g' only change behavior on click; no immediate action.

    def on_key_release(self, event):
        k = event.keysym.lower()
        if k in self.key_down:
            self.key_down.remove(k)

    # Actions
    def resize_grid(self):
        n = max(MIN_N, min(MAX_N, int(self.n_var.get() or DEFAULT_N)))
        self.N = n
        self.grid = [[0]*n for _ in range(n)]
        self.cell = CANVAS_SIZE // n
        self.start = (1,1)
        self.goal  = (n-2, n-2)
        self.engine = None
        self.animating = False
        self.draw()

    def clear(self):
        self.grid = [[0]*self.N for _ in range(self.N)]
        self.start = (1,1)
        self.goal  = (self.N-2, self.N-2)
        self.engine = None
        self.animating = False
        self.draw()

    def random_maze(self):
        for y in range(self.N):
            for x in range(self.N):
                self.grid[y][x] = 1 if random.random() < WALL_PROB else 0
        sx, sy = self.start
        gx, gy = self.goal
        self.grid[sy][sx] = 0
        self.grid[gy][gx] = 0
        self.engine = None
        self.animating = False
        self.draw()

    def pick_engine(self):
        # Validate start/goal
        if self.grid[self.start[1]][self.start[0]] == 1 or self.grid[self.goal[1]][self.goal[0]] == 1:
            messagebox.showwarning("Invalid", "Start/Goal cannot be on a wall.")
            return None
        a = self.algo.get()
        if a == "bfs":
            return bfs_gen(self.grid, self.start, self.goal)
        elif a == "dfs":
            return dfs_gen(self.grid, self.start, self.goal)
        else:
            return A_star_gen(self.grid, self.start, self.goal)

    def run(self):
        if self.animating:
            return
        if self.engine is None:
            self.engine = self.pick_engine()
            if self.engine is None:
                return
        self.animating = True
        self._animate()

    def _animate(self):
        if not self.animating or self.engine is None:
            return
        try:
            state = next(self.engine)
            self.draw(state)
            if state.get("done"):
                self.animating = False
                self.engine = None
            else:
                delay = max(1, int(1000 / max(1, int(self.speed.get()))))
                self.root.after(delay, self._animate)
        except StopIteration:
            self.animating = False
            self.engine = None

    def step(self):
        if self.engine is None:
            self.engine = self.pick_engine()
            if self.engine is None:
                return
        try:
            state = next(self.engine)
            self.draw(state)
            if state.get("done"):
                self.engine = None
        except StopIteration:
            self.engine = None

# Main Application
if __name__ == "__main__":
    root = tk.Tk()
    style = ttk.Style()
    # Try a cleaner theme if available
    try:
        style.theme_use("clam")
    except:
        pass
    app = App(root)
    root.mainloop()
