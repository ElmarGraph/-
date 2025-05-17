# Программа позволяет рисовать графы и выводить их матрицу смежности
# Добавление вершины - ЛКМ
# Добавление ребра - выделить две вершины и нажать e
# Удаление вершины - выделить вершину и нажать d
# Удаление ребра - выделить две вершины ребра и нажать r
# Также доступно добавление контрольных точек на рёбра для их изгибания, выделение контрольной точки и нажатие r удаляет её
# Нажатие "Показать матрицу" выводит матрицу смежности в виде списка списков

import math
import tkinter as tk
from tkinter import filedialog
import networkx as nx
import json

class GraphEditor:
    def __init__(self, root):
        self.root = root
        self.root.title("Graph Editor")
        self.canvas = tk.Canvas(root, bg="white", width=800, height=600)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        # Добавляем поле для вывода матрицы и кнопку
        self.text_output = tk.Text(root, height=10)
        self.text_output.pack(fill=tk.X)
        btn_show_matrix = tk.Button(root, text="Показать матрицу", command=self.show_matrix)
        btn_show_matrix.pack(fill=tk.X)
        
        self.graph = nx.Graph()
        self.vertices = {}
        self.edges = {}
        self.drag_data = {"vertex": None, "offset_x": 0, "offset_y": 0,
                          "edge_ctrl": None, "ctrl_offset_x": 0, "ctrl_offset_y": 0}
        self.selected_vertices = []
        self.selected_edge_ctrl = None  # кортеж (edge, ctrl_point_index) или None
        self.active_edge = None
        
        self.canvas.bind("<Button-1>", self.on_click)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.root.bind("d", self.delete_vertex)
        self.root.bind("r", self.delete_edge)
        self.root.bind("e", self.start_edge)
        self.create_menu()
        
    def show_matrix(self):
        matrix = nx.to_numpy_array(self.graph).astype(int).tolist()
        self.text_output.delete("1.0", tk.END)
        self.text_output.insert(tk.END, str(matrix))

    def create_menu(self):
        menu = tk.Menu(self.root)
        self.root.config(menu=menu)
        file_menu = tk.Menu(menu, tearoff=0)
        menu.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Save Matrix", command=self.save_matrix)
        file_menu.add_command(label="Print Matrix", command=self.print_matrix)

    def on_click(self, event):
        ctrl_hit = self.find_nearest_edge_ctrl_point(event.x, event.y)
        if ctrl_hit is not None:
            edge, idx = ctrl_hit
            self.selected_edge_ctrl = (edge, idx)
            cx, cy = self.edges[edge][idx]
            self.drag_data["edge_ctrl"] = (edge, idx)
            self.drag_data["ctrl_offset_x"] = cx - event.x
            self.drag_data["ctrl_offset_y"] = cy - event.y
            self.selected_vertices.clear()
            self.draw_graph()
            return
        
        clicked_node = self.find_nearest_vertex(event.x, event.y)
        if clicked_node is not None:
            if clicked_node not in self.selected_vertices:
                self.selected_vertices.append(clicked_node)
            else:
                self.selected_vertices.remove(clicked_node)
            if len(self.selected_vertices) == 1:
                self.drag_data["vertex"] = clicked_node
                x, y = self.vertices[clicked_node]
                self.drag_data["offset_x"] = x - event.x
                self.drag_data["offset_y"] = y - event.y
            self.selected_edge_ctrl = None
            self.draw_graph()
            return

        # Если кликнули по пустому месту — пытаемся добавить контрольную точку на ребро (если клик близко к ребру)
        if self.try_add_ctrl_point(event.x, event.y):
            self.selected_edge_ctrl = None
            self.selected_vertices.clear()
            self.draw_graph()
            return

        # Иначе добавляем новую вершину
        if self.active_edge is not None:
            self.active_edge = None

        node_id = len(self.vertices) + 1
        self.vertices[node_id] = (event.x, event.y)
        self.graph.add_node(node_id)
        self.selected_vertices.clear()
        self.selected_edge_ctrl = None
        self.draw_graph()

    def try_add_ctrl_point(self, x, y, threshold=7):
        """
        Попытка добавить контрольную точку на ребро, если клик близко к одному из сегментов ребра.
        threshold — максимальное расстояние до сегмента, чтобы считать, что клик по ребру.
        """
        def dist_point_to_segment(px, py, x1, y1, x2, y2):
            # Расстояние от точки к отрезку
            line_mag = math.hypot(x2 - x1, y2 - y1)
            if line_mag < 1e-6:
                return math.hypot(px - x1, py - y1)
            u = ((px - x1) * (x2 - x1) + (py - y1) * (y2 - y1)) / (line_mag ** 2)
            u = max(0, min(1, u))
            ix = x1 + u * (x2 - x1)
            iy = y1 + u * (y2 - y1)
            return math.hypot(px - ix, py - iy), (ix, iy), u

        for (u, v), points in self.edges.items():
            path = [self.vertices[u]] + points + [self.vertices[v]]
            for i in range(len(path) - 1):
                x1, y1 = path[i]
                x2, y2 = path[i + 1]
                dist, proj_point, u_param = dist_point_to_segment(x, y, x1, y1, x2, y2)
                if dist <= threshold:
                    # Вставляем новую контрольную точку между i-й и (i+1)-й точками пути ребра
                    # Учтём, что points — список контрольных точек между вершинами
                    # Индекс вставки в points = i (если i == 0, вставка в начало, если i == len(points), вставка в конец)
                    insert_index = i if i > 0 else 0
                    self.edges[(u, v)].insert(insert_index, proj_point)
                    return True
        return False

    def on_drag(self, event):
        if self.drag_data["vertex"] is not None:
            node = self.drag_data["vertex"]
            self.vertices[node] = (event.x + self.drag_data["offset_x"],
                                  event.y + self.drag_data["offset_y"])
            self.draw_graph()
        elif self.drag_data["edge_ctrl"] is not None:
            edge, idx = self.drag_data["edge_ctrl"]
            self.edges[edge][idx] = (event.x + self.drag_data["ctrl_offset_x"],
                                    event.y + self.drag_data["ctrl_offset_y"])
            self.draw_graph()

    def on_release(self, event):
        self.drag_data["vertex"] = None
        self.drag_data["edge_ctrl"] = None

    def start_edge(self, event):
        if len(self.selected_vertices) == 2:
            u, v = self.selected_vertices
            if u != v:
                self.graph.add_edge(u, v)
                self.edges[(u, v)] = []
                self.active_edge = (u, v)
            self.selected_vertices.clear()
            self.selected_edge_ctrl = None
            self.draw_graph()

    def delete_vertex(self, event):
        if self.selected_vertices:
            for node in self.selected_vertices:
                self.graph.remove_node(node)
                self.vertices.pop(node, None)
            # Удаляем рёбра, связанные с удалёнными вершинами
            self.edges = {e: pts for e, pts in self.edges.items() if all(n not in self.selected_vertices for n in e)}
            self.selected_vertices.clear()
            self.selected_edge_ctrl = None
            self.draw_graph()

    def delete_edge(self, event):
        # Удаляем ребро, если выбраны две вершины, между которыми оно есть
        if len(self.selected_vertices) == 2:
            u, v = self.selected_vertices
            if self.graph.has_edge(u, v):
                self.graph.remove_edge(u, v)
                self.edges.pop((u, v), None)
                self.edges.pop((v, u), None)
            self.selected_vertices.clear()
            self.selected_edge_ctrl = None
            self.draw_graph()
        # Или удаляем выделенную контрольную точку ребра (если нужна такая логика)
        elif self.selected_edge_ctrl is not None:
            edge, idx = self.selected_edge_ctrl
            self.edges[edge].pop(idx)
            self.selected_edge_ctrl = None
            self.draw_graph()

    def find_nearest_vertex(self, x, y):
        for node, (vx, vy) in self.vertices.items():
            if (x - vx)**2 + (y - vy)**2 <= 15**2:
                return node
        return None

    def find_nearest_edge_ctrl_point(self, x, y, radius=10):
        for edge, points in self.edges.items():
            for i, (px, py) in enumerate(points):
                if (x - px)**2 + (y - py)**2 <= radius**2:
                    return edge, i
        return None

    def draw_graph(self):
        self.canvas.delete("all")
        for node, (x, y) in self.vertices.items():
            color = "lightgreen" if node in self.selected_vertices else "skyblue"
            self.canvas.create_oval(x - 15, y - 15, x + 15, y + 15, fill=color, outline="black", width=2)
            self.canvas.create_text(x, y, text=str(node), font=("Arial", 12, "bold"))
        for (u, v), points in self.edges.items():
            x1, y1 = self.vertices[u]
            x2, y2 = self.vertices[v]
            path = [(x1, y1)] + points + [(x2, y2)]
            color = "red" if self.selected_edge_ctrl is not None and self.selected_edge_ctrl[0] == (u,v) else "gray"
            for p1, p2 in zip(path[:-1], path[1:]):
                self.canvas.create_line(*p1, *p2, fill=color, width=2)
            # Рисуем контрольные точки ребра
            for i, (cx, cy) in enumerate(points):
                ctrl_color = "orange" if self.selected_edge_ctrl == ((u, v), i) else "black"
                self.canvas.create_oval(cx - 6, cy - 6, cx + 6, cy + 6, fill=ctrl_color)

    def save_matrix(self):
        matrix = nx.to_numpy_matrix(self.graph).tolist()
        file_path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON files", "*.json")])
        if file_path:
            with open(file_path, "w") as file:
                json.dump(matrix, file, indent=2)

    def print_matrix(self):
        matrix = nx.to_numpy_matrix(self.graph).tolist()
        print(matrix)

if __name__ == "__main__":
    root = tk.Tk()
    app = GraphEditor(root)
    root.mainloop()

'''
# после создания контрольных точек можно создавать вершины, контрольные точки удаляются
import math
import tkinter as tk
from tkinter import filedialog
import networkx as nx
import json

class GraphEditor:
    def __init__(self, root):
        self.root = root
        self.root.title("Graph Editor")
        self.canvas = tk.Canvas(root, bg="white", width=800, height=600)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.graph = nx.Graph()
        self.vertices = {}
        self.edges = {}
        self.drag_data = {"vertex": None, "offset_x": 0, "offset_y": 0,
                          "edge_ctrl": None, "ctrl_offset_x": 0, "ctrl_offset_y": 0}
        self.selected_vertices = []
        self.selected_edge_ctrl = None  # кортеж (edge, ctrl_point_index) или None
        self.active_edge = None
        
        self.canvas.bind("<Button-1>", self.on_click)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.root.bind("d", self.delete_vertex)
        self.root.bind("r", self.delete_edge)
        self.root.bind("e", self.start_edge)
        self.create_menu()

    def create_menu(self):
        menu = tk.Menu(self.root)
        self.root.config(menu=menu)
        file_menu = tk.Menu(menu, tearoff=0)
        menu.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Save Matrix", command=self.save_matrix)
        file_menu.add_command(label="Print Matrix", command=self.print_matrix)

    def on_click(self, event):
        ctrl_hit = self.find_nearest_edge_ctrl_point(event.x, event.y)
        if ctrl_hit is not None:
            edge, idx = ctrl_hit
            self.selected_edge_ctrl = (edge, idx)
            cx, cy = self.edges[edge][idx]
            self.drag_data["edge_ctrl"] = (edge, idx)
            self.drag_data["ctrl_offset_x"] = cx - event.x
            self.drag_data["ctrl_offset_y"] = cy - event.y
            self.selected_vertices.clear()
            self.draw_graph()
            return
        
        clicked_node = self.find_nearest_vertex(event.x, event.y)
        if clicked_node is not None:
            if clicked_node not in self.selected_vertices:
                self.selected_vertices.append(clicked_node)
            else:
                self.selected_vertices.remove(clicked_node)
            if len(self.selected_vertices) == 1:
                self.drag_data["vertex"] = clicked_node
                x, y = self.vertices[clicked_node]
                self.drag_data["offset_x"] = x - event.x
                self.drag_data["offset_y"] = y - event.y
            self.selected_edge_ctrl = None
            self.draw_graph()
            return

        # Если кликнули по пустому месту — пытаемся добавить контрольную точку на ребро (если клик близко к ребру)
        if self.try_add_ctrl_point(event.x, event.y):
            self.selected_edge_ctrl = None
            self.selected_vertices.clear()
            self.draw_graph()
            return

        # Иначе добавляем новую вершину
        if self.active_edge is not None:
            self.active_edge = None

        node_id = len(self.vertices) + 1
        self.vertices[node_id] = (event.x, event.y)
        self.graph.add_node(node_id)
        self.selected_vertices.clear()
        self.selected_edge_ctrl = None
        self.draw_graph()

    def try_add_ctrl_point(self, x, y, threshold=7):
        """
        Попытка добавить контрольную точку на ребро, если клик близко к одному из сегментов ребра.
        threshold — максимальное расстояние до сегмента, чтобы считать, что клик по ребру.
        """
        def dist_point_to_segment(px, py, x1, y1, x2, y2):
            # Расстояние от точки к отрезку
            line_mag = math.hypot(x2 - x1, y2 - y1)
            if line_mag < 1e-6:
                return math.hypot(px - x1, py - y1)
            u = ((px - x1) * (x2 - x1) + (py - y1) * (y2 - y1)) / (line_mag ** 2)
            u = max(0, min(1, u))
            ix = x1 + u * (x2 - x1)
            iy = y1 + u * (y2 - y1)
            return math.hypot(px - ix, py - iy), (ix, iy), u

        for (u, v), points in self.edges.items():
            path = [self.vertices[u]] + points + [self.vertices[v]]
            for i in range(len(path) - 1):
                x1, y1 = path[i]
                x2, y2 = path[i + 1]
                dist, proj_point, u_param = dist_point_to_segment(x, y, x1, y1, x2, y2)
                if dist <= threshold:
                    # Вставляем новую контрольную точку между i-й и (i+1)-й точками пути ребра
                    # Учтём, что points — список контрольных точек между вершинами
                    # Индекс вставки в points = i (если i == 0, вставка в начало, если i == len(points), вставка в конец)
                    insert_index = i if i > 0 else 0
                    self.edges[(u, v)].insert(insert_index, proj_point)
                    return True
        return False

    def on_drag(self, event):
        if self.drag_data["vertex"] is not None:
            node = self.drag_data["vertex"]
            self.vertices[node] = (event.x + self.drag_data["offset_x"],
                                  event.y + self.drag_data["offset_y"])
            self.draw_graph()
        elif self.drag_data["edge_ctrl"] is not None:
            edge, idx = self.drag_data["edge_ctrl"]
            self.edges[edge][idx] = (event.x + self.drag_data["ctrl_offset_x"],
                                    event.y + self.drag_data["ctrl_offset_y"])
            self.draw_graph()

    def on_release(self, event):
        self.drag_data["vertex"] = None
        self.drag_data["edge_ctrl"] = None

    def start_edge(self, event):
        if len(self.selected_vertices) == 2:
            u, v = self.selected_vertices
            if u != v:
                self.graph.add_edge(u, v)
                self.edges[(u, v)] = []
                self.active_edge = (u, v)
            self.selected_vertices.clear()
            self.selected_edge_ctrl = None
            self.draw_graph()

    def delete_vertex(self, event):
        if self.selected_vertices:
            for node in self.selected_vertices:
                self.graph.remove_node(node)
                self.vertices.pop(node, None)
            # Удаляем рёбра, связанные с удалёнными вершинами
            self.edges = {e: pts for e, pts in self.edges.items() if all(n not in self.selected_vertices for n in e)}
            self.selected_vertices.clear()
            self.selected_edge_ctrl = None
            self.draw_graph()

    def delete_edge(self, event):
        # Удаляем ребро, если выбраны две вершины, между которыми оно есть
        if len(self.selected_vertices) == 2:
            u, v = self.selected_vertices
            if self.graph.has_edge(u, v):
                self.graph.remove_edge(u, v)
                self.edges.pop((u, v), None)
                self.edges.pop((v, u), None)
            self.selected_vertices.clear()
            self.selected_edge_ctrl = None
            self.draw_graph()
        # Или удаляем выделенную контрольную точку ребра (если нужна такая логика)
        elif self.selected_edge_ctrl is not None:
            edge, idx = self.selected_edge_ctrl
            self.edges[edge].pop(idx)
            self.selected_edge_ctrl = None
            self.draw_graph()

    def find_nearest_vertex(self, x, y):
        for node, (vx, vy) in self.vertices.items():
            if (x - vx)**2 + (y - vy)**2 <= 15**2:
                return node
        return None

    def find_nearest_edge_ctrl_point(self, x, y, radius=10):
        for edge, points in self.edges.items():
            for i, (px, py) in enumerate(points):
                if (x - px)**2 + (y - py)**2 <= radius**2:
                    return edge, i
        return None

    def draw_graph(self):
        self.canvas.delete("all")
        for node, (x, y) in self.vertices.items():
            color = "lightgreen" if node in self.selected_vertices else "skyblue"
            self.canvas.create_oval(x - 15, y - 15, x + 15, y + 15, fill=color, outline="black", width=2)
            self.canvas.create_text(x, y, text=str(node), font=("Arial", 12, "bold"))
        for (u, v), points in self.edges.items():
            x1, y1 = self.vertices[u]
            x2, y2 = self.vertices[v]
            path = [(x1, y1)] + points + [(x2, y2)]
            color = "red" if self.selected_edge_ctrl is not None and self.selected_edge_ctrl[0] == (u,v) else "gray"
            for p1, p2 in zip(path[:-1], path[1:]):
                self.canvas.create_line(*p1, *p2, fill=color, width=2)
            # Рисуем контрольные точки ребра
            for i, (cx, cy) in enumerate(points):
                ctrl_color = "orange" if self.selected_edge_ctrl == ((u, v), i) else "black"
                self.canvas.create_oval(cx - 6, cy - 6, cx + 6, cy + 6, fill=ctrl_color)

    def save_matrix(self):
        matrix = nx.to_numpy_matrix(self.graph).tolist()
        file_path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON files", "*.json")])
        if file_path:
            with open(file_path, "w") as file:
                json.dump(matrix, file, indent=2)

    def print_matrix(self):
        matrix = nx.to_numpy_matrix(self.graph).tolist()
        print(matrix)

if __name__ == "__main__":
    root = tk.Tk()
    app = GraphEditor(root)
    root.mainloop()
'''

'''
# контрольные точки
import tkinter as tk
from tkinter import filedialog
import networkx as nx
import json

class GraphEditor:
    def __init__(self, root):
        self.root = root
        self.root.title("Graph Editor")
        self.canvas = tk.Canvas(root, bg="white", width=800, height=600)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.graph = nx.Graph()
        self.vertices = {}
        self.edges = {}
        
        self.drag_data = {
            "vertex": None,
            "offset_x": 0,
            "offset_y": 0,
            "edge_ctrl": None,
            "ctrl_offset_x": 0,
            "ctrl_offset_y": 0
        }
        self.selected_vertices = []
        self.selected_edge_ctrl = None
        self.active_edge = None
        
        self.canvas.bind("<Button-1>", self.on_click)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.root.bind("d", self.delete_selected)
        self.root.bind("r", self.delete_edge)
        self.root.bind("e", self.start_edge)
        
        self.create_menu()

    def create_menu(self):
        menu = tk.Menu(self.root)
        self.root.config(menu=menu)
        file_menu = tk.Menu(menu, tearoff=0)
        menu.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Save Matrix", command=self.save_matrix)
        file_menu.add_command(label="Print Matrix", command=self.print_matrix)

    def on_click(self, event):
        ctrl_hit = self.find_nearest_edge_ctrl_point(event.x, event.y)
        if ctrl_hit is not None:
            edge, idx = ctrl_hit
            self.selected_edge_ctrl = (edge, idx)
            cx, cy = self.edges[edge][idx]
            self.drag_data["edge_ctrl"] = (edge, idx)
            self.drag_data["ctrl_offset_x"] = cx - event.x
            self.drag_data["ctrl_offset_y"] = cy - event.y
            self.selected_vertices.clear()
            self.draw_graph()
            return
        
        clicked_node = self.find_nearest_vertex(event.x, event.y)
        if clicked_node is not None:
            if clicked_node not in self.selected_vertices:
                self.selected_vertices.append(clicked_node)
            else:
                self.selected_vertices.remove(clicked_node)
            if len(self.selected_vertices) == 1:
                self.drag_data["vertex"] = clicked_node
                x, y = self.vertices[clicked_node]
                self.drag_data["offset_x"] = x - event.x
                self.drag_data["offset_y"] = y - event.y
            self.selected_edge_ctrl = None
            self.draw_graph()
            return
        
        if self.active_edge is not None:
            self.edges[self.active_edge].append((event.x, event.y))
            self.draw_graph()
            return
        
        node_id = len(self.vertices) + 1
        self.vertices[node_id] = (event.x, event.y)
        self.graph.add_node(node_id)
        self.selected_vertices.clear()
        self.selected_edge_ctrl = None
        self.draw_graph()

    def on_drag(self, event):
        if self.drag_data["vertex"] is not None:
            node = self.drag_data["vertex"]
            self.vertices[node] = (event.x + self.drag_data["offset_x"], event.y + self.drag_data["offset_y"])
            self.draw_graph()
            return
        
        if self.drag_data["edge_ctrl"] is not None:
            edge, idx = self.drag_data["edge_ctrl"]
            new_x = event.x + self.drag_data["ctrl_offset_x"]
            new_y = event.y + self.drag_data["ctrl_offset_y"]
            self.edges[edge][idx] = (new_x, new_y)
            self.draw_graph()
            return

    def on_release(self, event):
        self.drag_data["vertex"] = None
        self.drag_data["edge_ctrl"] = None

    def start_edge(self, event):
        if len(self.selected_vertices) == 2:
            u, v = self.selected_vertices
            if u != v and not self.graph.has_edge(u, v):
                self.graph.add_edge(u, v)
                self.edges[(u, v)] = []
                self.active_edge = (u, v)
            self.selected_vertices.clear()
            self.selected_edge_ctrl = None
            self.draw_graph()

    def delete_selected(self, event):
        # Удаляем выделенные вершины
        if self.selected_vertices:
            for node in self.selected_vertices:
                self.graph.remove_node(node)
                del self.vertices[node]
            self.edges = {e: pts for e, pts in self.edges.items() if all(n not in self.selected_vertices for n in e)}
            self.selected_vertices.clear()
            self.selected_edge_ctrl = None
            self.draw_graph()
            return
        
        # Удаляем выделенную контрольную точку ребра
        if self.selected_edge_ctrl is not None:
            edge, idx = self.selected_edge_ctrl
            self.edges[edge].pop(idx)
            self.selected_edge_ctrl = None
            self.draw_graph()
            return

    def delete_edge(self, event):
        if len(self.selected_vertices) == 2:
            u, v = self.selected_vertices
            if self.graph.has_edge(u, v):
                self.graph.remove_edge(u, v)
                self.edges.pop((u, v), None)
                self.edges.pop((v, u), None)
            self.selected_vertices.clear()
            self.selected_edge_ctrl = None
            self.draw_graph()

    def find_nearest_vertex(self, x, y):
        for node, (vx, vy) in self.vertices.items():
            if (x - vx)**2 + (y - vy)**2 <= 15**2:
                return node
        return None

    def find_nearest_edge_ctrl_point(self, x, y, radius=8):
        for edge, points in self.edges.items():
            for i, (px, py) in enumerate(points):
                if (x - px)**2 + (y - py)**2 <= radius**2:
                    return edge, i
        return None

    def draw_graph(self):
        self.canvas.delete("all")
        for (u, v), points in self.edges.items():
            x1, y1 = self.vertices[u]
            x2, y2 = self.vertices[v]
            path = [(x1, y1)] + points + [(x2, y2)]
            for p1, p2 in zip(path[:-1], path[1:]):
                self.canvas.create_line(*p1, *p2, fill="gray", width=2)
            for i, (cx, cy) in enumerate(points):
                color = "red" if self.selected_edge_ctrl == ((u, v), i) else "orange"
                self.canvas.create_oval(cx - 6, cy - 6, cx + 6, cy + 6, fill=color, outline="black")

        for node, (x, y) in self.vertices.items():
            color = "lightgreen" if node in self.selected_vertices else "skyblue"
            self.canvas.create_oval(x - 15, y - 15, x + 15, y + 15, fill=color, outline="black", width=2)
            self.canvas.create_text(x, y, text=str(node), font=("Arial", 12, "bold"))

    def save_matrix(self):
        matrix = nx.to_numpy_matrix(self.graph).tolist()
        file_path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON files", "*.json")])
        if file_path:
            with open(file_path, "w") as file:
                json.dump(matrix, file, indent=2)

    def print_matrix(self):
        matrix = nx.to_numpy_matrix(self.graph).tolist()
        print(matrix)

if __name__ == "__main__":
    root = tk.Tk()
    app = GraphEditor(root)
    root.mainloop()
'''

'''
# добавление, удаление и перетаскивание вершин и рёбер
import tkinter as tk
from tkinter import filedialog
import networkx as nx
import json

class GraphEditor:
    def __init__(self, root):
        self.root = root
        self.root.title("Graph Editor")
        self.canvas = tk.Canvas(root, bg="white", width=800, height=600)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.graph = nx.Graph()
        self.vertices = {}
        self.edges = {}
        self.drag_data = {"vertex": None, "offset_x": 0, "offset_y": 0}
        self.selected_vertices = []
        self.active_edge = None
        
        self.canvas.bind("<Button-1>", self.on_click)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.root.bind("d", self.delete_vertex)
        self.root.bind("r", self.delete_edge)
        self.root.bind("e", self.start_edge)
        self.create_menu()

    def create_menu(self):
        menu = tk.Menu(self.root)
        self.root.config(menu=menu)
        file_menu = tk.Menu(menu, tearoff=0)
        menu.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Save Matrix", command=self.save_matrix)
        file_menu.add_command(label="Print Matrix", command=self.print_matrix)

    def on_click(self, event):
        clicked_node = self.find_nearest_vertex(event.x, event.y)
        if clicked_node is not None:
            if clicked_node not in self.selected_vertices:
                self.selected_vertices.append(clicked_node)
            else:
                self.selected_vertices.remove(clicked_node)
            # Start dragging if only one node is selected
            if len(self.selected_vertices) == 1:
                self.drag_data["vertex"] = clicked_node
                x, y = self.vertices[clicked_node]
                self.drag_data["offset_x"] = x - event.x
                self.drag_data["offset_y"] = y - event.y
            self.draw_graph()
        elif self.active_edge is not None:
            self.edges[self.active_edge].append((event.x, event.y))
            self.draw_graph()
        else:
            node_id = len(self.vertices) + 1
            self.vertices[node_id] = (event.x, event.y)
            self.graph.add_node(node_id)
            self.draw_graph()

    def on_drag(self, event):
        if self.drag_data["vertex"] is not None:
            node = self.drag_data["vertex"]
            self.vertices[node] = (event.x + self.drag_data["offset_x"],
                                  event.y + self.drag_data["offset_y"])
            self.draw_graph()

    def on_release(self, event):
        self.drag_data["vertex"] = None
        if self.active_edge is not None:
            self.active_edge = None
            self.draw_graph()

    def start_edge(self, event):
        if len(self.selected_vertices) == 2:
            u, v = self.selected_vertices
            if u != v:
                self.graph.add_edge(u, v)
                self.edges[(u, v)] = []
                self.active_edge = (u, v)
            self.selected_vertices.clear()
            self.draw_graph()

    def delete_vertex(self, event):
        if self.selected_vertices:
            for node in self.selected_vertices:
                self.graph.remove_node(node)
                del self.vertices[node]
            self.edges = {e: pts for e, pts in self.edges.items() if all(n not in self.selected_vertices for n in e)}
            self.selected_vertices.clear()
            self.draw_graph()

    def delete_edge(self, event):
        if len(self.selected_vertices) == 2:
            u, v = self.selected_vertices
            if self.graph.has_edge(u, v):
                self.graph.remove_edge(u, v)
                self.edges.pop((u, v), None)
                self.edges.pop((v, u), None)
            self.selected_vertices.clear()
            self.draw_graph()

    def find_nearest_vertex(self, x, y):
        for node, (vx, vy) in self.vertices.items():
            if (x - vx)**2 + (y - vy)**2 <= 15**2:
                return node
        return None

    def draw_graph(self):
        self.canvas.delete("all")
        for node, (x, y) in self.vertices.items():
            color = "lightgreen" if node in self.selected_vertices else "skyblue"
            self.canvas.create_oval(x - 15, y - 15, x + 15, y + 15, fill=color, outline="black", width=2)
            self.canvas.create_text(x, y, text=str(node), font=("Arial", 12, "bold"))
        for (u, v), points in self.edges.items():
            x1, y1 = self.vertices[u]
            x2, y2 = self.vertices[v]
            path = [(x1, y1)] + points + [(x2, y2)]
            for p1, p2 in zip(path[:-1], path[1:]):
                self.canvas.create_line(*p1, *p2, fill="gray", width=2)

    def save_matrix(self):
        matrix = nx.to_numpy_matrix(self.graph).tolist()
        file_path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON files", "*.json")])
        if file_path:
            with open(file_path, "w") as file:
                json.dump(matrix, file, indent=2)

    def print_matrix(self):
        matrix = nx.to_numpy_matrix(self.graph).tolist()
        print(matrix)

if __name__ == "__main__":
    root = tk.Tk()
    app = GraphEditor(root)
    root.mainloop()
'''
