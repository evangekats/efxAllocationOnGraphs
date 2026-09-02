import tkinter as tk
import copy
from tkinter import ttk
from tkinter import simpledialog, messagebox, filedialog
from inputMethods import get_input_from_file
from allocationEFX import (run_allocation,
    greedy_allocation,
    reduce_envy,
    allocate_remaining_goods,
    is_envied,
    is_efx)
import matplotlib.pyplot as plt
import networkx as nx
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.lines as mlines

class EFXEdgeInputGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("EFX Allocation - GUI")
        self.input_method = tk.StringVar(value="Text")
        self.show_details = tk.BooleanVar(value=False)
        self.show_graph_var = tk.BooleanVar(value=True)

        self.agents = []
        self.goods = []
        self.valuations = {}

        self.instruction_label = tk.Label(
            root,
            text="📌 INSTRUCTIONS:\nEnter edges in the format: A,B:valA,valB",
            justify="left",
            fg="darkgreen",
            padx=10
        )
        self.instruction_label.pack(anchor='w')

        tk.Label(root, text="Select input method:").pack()
        tk.Radiobutton(root, text="Enter Edges Manually", variable=self.input_method, value="Text", command=self.toggle_input_mode).pack(anchor='w')
        tk.Radiobutton(root, text="Load from File", variable=self.input_method, value="File", command=self.toggle_input_mode).pack(anchor='w')
        tk.Radiobutton(root, text="Enter Agents, Edges and Valuations", variable=self.input_method, value="Wizard", command=self.toggle_input_mode).pack(anchor='w')

        self.text_input = tk.Text(root, width=60, height=12)
        self.text_input.pack()
        self.text_input.bind("<Control-v>", self.paste_clipboard)
        self.text_input.bind("<Button-3>", self.show_context_menu)

        self.file_button = tk.Button(root, text="Select File", command=self.load_file)
        self.file_button.pack()
        self.file_button.pack_forget()

        tk.Checkbutton(root, text="Show detailed allocation steps", variable=self.show_details).pack(pady=5)
        tk.Checkbutton(root, text="Show allocation graph", variable=self.show_graph_var).pack(pady=5)


        button_frame = tk.Frame(root)
        button_frame.pack(pady=5)

        tk.Button(button_frame, text="Clear Input", command=self.clear_input).pack(side='left', padx=5)
        tk.Button(button_frame, text="Run Allocation", command=self.run_allocation_gui).pack(side='left', padx=5)

        self.status_label = tk.Label(root, text="", fg="blue")
        self.status_label.pack()

    def paste_clipboard(self, event=None):
        try:
            text = self.root.clipboard_get()
            self.text_input.insert(tk.INSERT, text)
        except tk.TclError:
            pass
        return "break"

    def show_context_menu(self, event):
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label="Paste", command=lambda: self.paste_clipboard())
        menu.post(event.x_root, event.y_root)

    def toggle_input_mode(self):
        if self.input_method.get() == "Text":
            self.instruction_label.pack(anchor='w')
            self.text_input.pack()
            self.file_button.pack_forget()
        elif self.input_method.get() == "File":
            self.instruction_label.pack(anchor='w')
            self.text_input.pack_forget()
            self.file_button.pack()
        elif self.input_method.get() == "Wizard":
            self.instruction_label.pack_forget()
            self.text_input.pack_forget()
            self.file_button.pack_forget()
            self.manual_input_wizard()

    def manual_input_wizard(self):
        state = {
            'step': 0,
            'agents': [],
            'goods': [],
            'valuations': {},
            'current_good': 0,
            'current_agent': 0,
            'relevant_goods': [],
            'edge_count': 0,
            'edge_index': 0
        }

        wizard = tk.Toplevel(self.root)
        wizard.title("Step-by-Step Wizard")

        label = tk.Label(wizard, text="Enter number of agents:")
        label.pack()
        entry = tk.Entry(wizard)
        entry.pack()

        def step1():
            try:
                count = int(entry.get())
                if count <= 0:
                    raise ValueError
                state['step'] = 1
                state['agent_count'] = count
                entry.delete(0, tk.END)
                label.config(text=f"Enter name for agent 1 of {count}:")
                button.config(command=step2)
            except ValueError:
                messagebox.showerror("Invalid", "Enter a positive integer")

        def step2():
            name = entry.get().strip()
            if not name or name in state['agents']:
                messagebox.showerror("Invalid", "Agent must be unique and non-empty.")
                return
            state['agents'].append(name)
            entry.delete(0, tk.END)
            if len(state['agents']) < state['agent_count']:
                label.config(text=f"Enter name for agent {len(state['agents']) + 1} of {state['agent_count']}:")
            else:
                state['step'] = 2
                label.config(text="Enter number of edges (goods):")
                button.config(command=step3_prep)

        def step3_prep():
            try:
                count = int(entry.get())
                if count <= 0:
                    raise ValueError
                max_edges = (state['agent_count'] * (state['agent_count'] - 1)) // 2
                if count > max_edges:
                    raise ValueError
                state['edge_count'] = count
                state['edge_index'] = 0
                entry.delete(0, tk.END)
                label.config(text=f"Enter edge 1 of {count} as A,B:")
                button.config(command=step3)
            except ValueError:
                messagebox.showerror("Invalid", f"Enter a positive integer ≤ {max_edges}")

        def step3():
            try:
                text = entry.get().strip()
                u, v = map(str.strip, text.split(","))
                edge = tuple(sorted((u, v)))
                if u == v or edge in state['goods'] or u not in state['agents'] or v not in state['agents']:
                    raise ValueError
                state['goods'].append(edge)
                state['valuations'][edge] = {}
                entry.delete(0, tk.END)
                label.config(
                    text=f"[Edge {state['edge_index'] + 1} of {state['edge_count']}] Value for agent {u} on {edge}:")
                state['current_agent'] = 0
                button.config(command=lambda: step4(0, edge))
            except:
                messagebox.showerror("Invalid", "Edge must be 'A,B' with distinct valid agent names.")

        def step4(agent_idx, edge):
            agent = edge[agent_idx]
            try:
                val = float(entry.get())
                state['valuations'][edge][agent] = val
                entry.delete(0, tk.END)
                if agent_idx == 0:
                    label.config(
                        text=f"[Edge {state['edge_index'] + 1} of {state['edge_count']}] Value for agent {edge[1]} on {edge}:")
                    button.config(command=lambda: step4(1, edge))
                else:
                    state['edge_index'] += 1
                    if state['edge_index'] < state['edge_count']:
                        label.config(text=f"Enter edge {state['edge_index'] + 1} of {state['edge_count']} as A,B:")
                        button.config(command=step3)
                    else:
                        step5()
            except ValueError:
                messagebox.showerror("Invalid", "Must be a number")

        def step5():
            self.agents = state['agents']
            self.goods = state['goods']
            self.valuations = {
                agent: {g: state['valuations'][g].get(agent, 0.0) for g in state['goods']}
                for agent in state['agents']
            }
            wizard.destroy()
            self.status_label.config(text="✅ Wizard input completed.")

        button = tk.Button(wizard, text="Next", command=step1)
        button.pack(pady=10)

    def clear_input(self):
        self.text_input.delete("1.0", tk.END)
        self.status_label.config(text="✏️ Input cleared.")

    def load_file(self):
        filepath = filedialog.askopenfilename(filetypes=[("Text files", "*.txt")])
        if filepath:
            agents, goods, valuations = get_input_from_file(filepath)
            if agents and goods:
                self.agents = agents
                self.goods = goods
                self.valuations = valuations
                self.status_label.config(text=f"📁 Loaded {len(goods)} goods from file among {len(agents)} agents.")
            else:
                messagebox.showerror("Error", "Failed to load valid data from file.")

    def run_allocation_gui(self):
        if self.input_method.get() == "Text":
            text = self.text_input.get("1.0", tk.END)
            with open("temp_input.txt", "w") as f:
                f.write(text)
            self.agents, self.goods, self.valuations = get_input_from_file("temp_input.txt")

        # Τρέχουμε allocation μία φορά μόνο!
        final_alloc, details, greedy_alloc, envy_reduced_alloc = run_allocation(
            self.agents, self.goods, self.valuations,
            show_details=self.show_details.get()
        )

        # Δημιουργία γραφημάτων
        graph_figures = []
        if self.show_graph_var.get():
            graph_figures.append(("Initial Graph", self.create_graph_figure(self.goods, None)))
            graph_figures.append(("Greedy Allocation", self.create_graph_figure(self.goods, greedy_alloc)))
            graph_figures.append(("After Reduce Envy", self.create_graph_figure(self.goods, envy_reduced_alloc)))
            graph_figures.append(("Final Allocation", self.create_graph_figure(self.goods, final_alloc)))

        # Πολλαπλά allocation tables
        tables = [
            ("Greedy Allocation", greedy_alloc),
            ("After Reduce Envy", envy_reduced_alloc),
            ("Final Allocation", final_alloc)
        ]

        self.show_results_window(tables, details, graph_figures)

    def copy_details_to_clipboard(self):
        try:
            text = self.details_text_widget.get("1.0", tk.END)
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            self.root.update()
        except:
            messagebox.showerror("Error", "Could not copy text to clipboard.")

    def show_results_window(self, stages, details_text, graph_figures):
        window = tk.Toplevel(self.root)
        window.title("Allocation Results")
        window.geometry("1000x700")

        notebook = ttk.Notebook(window)
        notebook.pack(expand=True, fill="both")

        for title, allocation in stages:
            frame = ttk.Frame(notebook)
            notebook.add(frame, text=f"📋 {title}")

            columns = ("Agent", "Allocated Goods", "Total Value", "EFX-safe")
            tree = ttk.Treeview(frame, columns=columns, show="headings")
            for col in columns:
                tree.heading(col, text=col)

            for agent, goods in allocation.items():
                if not isinstance(goods, set):
                    goods = {goods}
                goods_str = ", ".join(str(g) for g in goods)
                total_value = sum(self.valuations.get(agent, {}).get(g, 0) for g in goods)
                efx_safe = "No" if is_envied(agent, allocation, self.valuations) else "Yes"
                tag = "envied" if efx_safe == "No" else "non_envied"
                tree.insert("", tk.END, values=(agent, goods_str, total_value, efx_safe), tags=(tag,))

            tree.tag_configure("envied", background="#ffcccc")
            tree.tag_configure("non_envied", background="#ccffcc")
            tree.pack(expand=True, fill="both", padx=10, pady=10)

        # Details Tab
        # Details Tab (improved)
        details_frame = ttk.Frame(notebook)
        notebook.add(details_frame, text="📝 Details")

        # Wrapper frame
        frame = tk.Frame(details_frame)
        frame.pack(fill='both', expand=True)

        # Scrollbar
        scrollbar = tk.Scrollbar(frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Text widget with monospace font
        self.details_text_widget = tk.Text(frame, wrap="word", font=("Courier", 10), yscrollcommand=scrollbar.set)
        self.details_text_widget.insert(tk.END, details_text)
        self.details_text_widget.pack(side=tk.LEFT, fill="both", expand=True)
        scrollbar.config(command=self.details_text_widget.yview)

        # Optional: Tag formatting (bold or headers if needed in future)
        self.details_text_widget.tag_configure("title", font=("Courier", 10, "bold", "underline"))

        # Copy to clipboard button
        copy_btn = tk.Button(details_frame, text="📋 Copy to Clipboard", command=self.copy_details_to_clipboard)
        copy_btn.pack(pady=5)


        # --- Valuations Tab (3 σταθερές στήλες) ---
        valuations_frame = ttk.Frame(notebook)
        notebook.add(valuations_frame, text="🧮 Valuations")

        cols = ("Edge (u, v)", "u's valuation", "v's valuation")
        val_tree = ttk.Treeview(valuations_frame, columns=cols, show="headings", height=12)

        # Κεφαλίδες & πλάτη
        val_tree.heading("Edge (u, v)", text="Edge (u, v)")
        val_tree.heading("u's valuation", text="u's valuation")
        val_tree.heading("v's valuation", text="v's valuation")

        val_tree.column("Edge (u, v)", anchor="center", stretch=True, width=180)
        val_tree.column("u's valuation", anchor="center", stretch=True, width=160)
        val_tree.column("v's valuation", anchor="center", stretch=True, width=160)

        # Scrollbars
        vsb = ttk.Scrollbar(valuations_frame, orient="vertical", command=val_tree.yview)
        hsb = ttk.Scrollbar(valuations_frame, orient="horizontal", command=val_tree.xview)
        val_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        # Δεδομένα: μία γραμμή ανά ακμή
        edges_iter = list(self.goods)
        try:
            edges_iter = sorted(edges_iter)
        except Exception:
            pass

        # Zebra striping
        val_tree.tag_configure("odd", background="#f7f7f9")
        val_tree.tag_configure("even", background="#ffffff")

        for i, e in enumerate(edges_iter):
            if not (isinstance(e, (tuple, list)) and len(e) == 2):
                continue

            def _val_for(agent, edge):
                d = self.valuations.get(agent, {})

                if edge in d:
                    return d[edge]

                es = tuple(sorted(edge))
                if es in d:
                    return d[es]

                er = (edge[1], edge[0])
                if er in d:
                    return d[er]
                return 0

            u, v = e
            vu = _val_for(u, e)
            vv = _val_for(v, e)


            def _fmt(x):
                try:
                    return f"{int(x)}" if float(x).is_integer() else f"{x:.2f}"
                except Exception:
                    return str(x)

            row = (f"({u}, {v})", _fmt(vu), _fmt(vv))

            tag = "odd" if (i % 2) else "even"
            val_tree.insert("", "end", values=row, tags=(tag,))

        # Κουμπί εξαγωγής CSV
        def export_valuations_csv():
            import csv
            from tkinter import filedialog, messagebox
            path = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv")],
                title="Export valuations to CSV"
            )
            if not path:
                return
            try:
                with open(path, "w", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    writer.writerow(["Edge (u, v)", "u's valuation", "v's valuation"])
                    for item in val_tree.get_children(""):
                        writer.writerow(val_tree.item(item, "values"))
                messagebox.showinfo("Export", f"Valuations exported to:\n{path}")
            except Exception as ex:
                messagebox.showerror("Export failed", str(ex))

        # Layout
        top_bar = ttk.Frame(valuations_frame)
        top_bar.pack(side="top", fill="x", padx=10, pady=6)
        export_btn = ttk.Button(top_bar, text="Export CSV", command=export_valuations_csv)
        export_btn.pack(side="right")

        val_tree.pack(side="left", expand=True, fill="both", padx=(10, 0), pady=(0, 10))
        vsb.pack(side="left", fill="y", pady=(0, 10))
        hsb.pack(side="bottom", fill="x", padx=10, pady=(0, 10))

        # Graph Tabs
        for title, fig in graph_figures:
            graph_frame = ttk.Frame(notebook)
            notebook.add(graph_frame, text=f"🧩 {title}")
            canvas = FigureCanvasTkAgg(fig, master=graph_frame)
            canvas.draw()
            canvas.get_tk_widget().pack(expand=True, fill="both")

    def create_graph_figure(self, goods, allocation):


        fig, ax = plt.subplots(figsize=(10, 8))

        if allocation is None:
            # Αρχικός γράφος χωρίς allocation
            G = nx.Graph()
            G.add_nodes_from(self.agents)
            G.add_edges_from(goods)

            pos = nx.circular_layout(G)  # Κυκλική διάταξη για καθαρότητα

            nx.draw_networkx_nodes(G, pos, node_color="skyblue", node_size=1000, ax=ax)
            nx.draw_networkx_labels(G, pos, ax=ax, font_weight="bold", font_color="black")
            # --- Καμπυλωτές ακμές (χωρίς βέλη) ---
            nx.draw_networkx_edges(
                G, pos, ax=ax, width=2,
                arrows=True,
                arrowstyle='-',  # σκέτη γραμμή (όχι κεφαλή βέλους)
                connectionstyle="arc3,rad=0.22"
            )



            ax.set_title("Initial Graph (Before Allocation)", fontsize=14)
            ax.axis("off")
            return fig

        # Αν υπάρχει allocation, σχεδιάζουμε directed graph
        G = nx.DiGraph()
        G.add_nodes_from(self.agents)
        pos = nx.spring_layout(G, seed=42, k=0.7)

        needs_free = False
        pos_free = [0.0, 0.0]

        edges = []
        edge_colors = []
        edge_styles = []

        for agent, goods_allocated in allocation.items():
            if not isinstance(goods_allocated, set):
                goods_allocated = {goods_allocated}
            for good in goods_allocated:
                if agent in good:
                    neighbor = good[0] if good[1] == agent else good[1]
                    edges.append((neighbor, agent))
                    edge_colors.append("black")
                    edge_styles.append("solid")
                else:
                    needs_free = True
                    edges.append(("free", agent))
                    edge_colors.append("red")
                    edge_styles.append("dashed")

        if needs_free:
            G.add_node("free")
            pos["free"] = pos_free
        G.add_edges_from(edges)

        visible_nodes = [n for n in G.nodes if n != "free"]
        node_colors = ['red' if is_envied(n, allocation, self.valuations) else 'green' for n in visible_nodes]

        nx.draw_networkx_nodes(G, pos, nodelist=visible_nodes, node_color=node_colors, node_size=900, ax=ax)
        nx.draw_networkx_labels(G, pos, labels={n: n for n in visible_nodes}, font_weight="bold", font_color="white",
                                ax=ax)

        # Σχεδίαση ακμών με καμπύλη και μεγαλύτερα βέλη
        for (u, v), color, style in zip(edges, edge_colors, edge_styles):
            nx.draw_networkx_edges(
                G, pos, edgelist=[(u, v)], ax=ax,
                edge_color=color,
                style=style,
                connectionstyle='arc3,rad=0.2',
                arrows=True, arrowsize=25, width=2
            )

        # Valuations δίπλα στους agents
        for agent in self.agents:
            goods_allocated = allocation.get(agent, set())
            if not isinstance(goods_allocated, set):
                goods_allocated = {goods_allocated}
            lines = []
            for good in goods_allocated:
                val = self.valuations[agent].get(good, 0)
                lines.append(f"{good}: {val}")
            if lines:
                x, y = pos[agent]
                ax.text(x + 0.05, y - 0.05, "\n".join(lines), fontsize=8,
                        bbox=dict(facecolor='white', alpha=0.6, edgecolor='gray'))

        # Υπόμνημα
        legend = [
            mlines.Line2D([], [], color='green', marker='o', linestyle='None', label='Non-envied Agent', markersize=10),
            mlines.Line2D([], [], color='red', marker='o', linestyle='None', label='Envied Agent', markersize=10),
            mlines.Line2D([], [], color='red', linestyle='dashed', label='Assigned non-adjacent good')
        ]
        ax.legend(handles=legend, loc="lower left", bbox_to_anchor=(0, -0.1), ncol=1)


        ax.set_title("Allocation Graph", fontsize=14)
        ax.axis("off")
        return fig


if __name__ == "__main__":
    root = tk.Tk()
    app = EFXEdgeInputGUI(root)
    root.mainloop()


