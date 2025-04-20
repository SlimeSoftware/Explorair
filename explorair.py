import os
import shutil
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
from PIL import Image, ImageTk  # pip install pillow

class FileExplorer(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Explorair")
        self.geometry("1100x700")

        self.clipboard_path = None  # Pour copier/coller
        self.history = {}  # Historique pour chaque onglet
        self.favorites = []  # Liste des favoris

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        self.menu_bar = tk.Menu(self)
        file_menu = tk.Menu(self.menu_bar, tearoff=0)
        file_menu.add_command(label="Nouveau dossier", command=self.create_folder)
        file_menu.add_command(label="Ouvrir un dossier", command=self.add_tab)
        file_menu.add_command(label="Quitter", command=self.quit)
        self.menu_bar.add_cascade(label="Fichier", menu=file_menu)

        fav_menu = tk.Menu(self.menu_bar, tearoff=0)
        fav_menu.add_command(label="Ajouter aux favoris", command=self.add_to_favorites)
        self.fav_menu = fav_menu
        self.menu_bar.add_cascade(label="Favoris", menu=fav_menu)

        self.config(menu=self.menu_bar)

        self.add_tab()

    def add_tab(self, path=None):
        tab = tk.Frame(self.notebook)
        self.notebook.add(tab, text="Onglet")

        top_frame = tk.Frame(tab)
        top_frame.pack(fill=tk.X, padx=5, pady=5)

        path_var = tk.StringVar()
        path_entry = tk.Entry(top_frame, textvariable=path_var, state='readonly', font=('Arial', 12))
        path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        back_btn = tk.Button(top_frame, text="⏪", command=lambda: self.go_back(tab))
        back_btn.pack(side=tk.RIGHT)

        search_frame = tk.Frame(tab)
        search_frame.pack(fill=tk.X, padx=5)

        search_var = tk.StringVar()
        search_var.trace_add("write", lambda *_: self.update_filter(tab))
        tk.Label(search_frame, text="🔍 Rechercher :").pack(side=tk.LEFT)
        search_entry = tk.Entry(search_frame, textvariable=search_var)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        tree = ttk.Treeview(tab, columns=("fullpath", "size"))
        tree.heading("#0", text="Nom", anchor='w')
        tree.heading("size", text="Taille", anchor='w')
        tree.column("size", width=100, anchor='w')
        tree.pack(fill=tk.BOTH, expand=True)
        tree.bind("<Double-1>", lambda e: self.on_double_click(tab))
        tree.bind("<Button-3>", lambda e: self.on_right_click(e, tab))

        ysb = ttk.Scrollbar(tab, orient="vertical", command=tree.yview)
        tree.configure(yscroll=ysb.set)
        ysb.pack(side="right", fill="y")

        context_menu = self.create_context_menu(tab)

        tab_data = {
            "frame": tab,
            "path_var": path_var,
            "search_var": search_var,
            "tree": tree,
            "history": [],
            "context_menu": context_menu
        }
        tab.tab_data = tab_data
        self.history[tab] = tab_data

        if not path:
            path = filedialog.askdirectory()
        if path:
            self.load_directory(tab, path)

    def create_context_menu(self, tab):
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="📂 Ouvrir", command=lambda: self.context_open(tab))
        menu.add_command(label="✏️ Modifier (txt)", command=lambda: self.context_edit(tab))
        menu.add_command(label="🖼️ Voir image", command=lambda: self.context_view_image(tab))
        menu.add_separator()
        menu.add_command(label="🗂️ Nouveau dossier", command=lambda: self.create_folder(tab))
        menu.add_command(label="📋 Copier", command=lambda: self.context_copy(tab))
        menu.add_command(label="📥 Coller", command=lambda: self.context_paste(tab))
        menu.add_command(label="⭐ Ajouter aux favoris", command=lambda: self.add_to_favorites(tab))
        menu.add_command(label="✏️ Renommer", command=lambda: self.context_rename(tab))
        menu.add_command(label="🗑️ Supprimer", command=lambda: self.context_delete(tab))
        return menu

    def on_right_click(self, event, tab):
        # Gestion du clic droit pour MacOS (Control+Click ou clic droit standard)
        item = self.get_tab_data(tab)["tree"].identify_row(event.y)
        if item:
            self.get_tab_data(tab)["tree"].selection_set(item)
            if event.num == 2 or event.num == 3 or (event.state & 0x4 != 0 and event.num == 1):
                self.get_tab_data(tab)["context_menu"].tk_popup(event.x_root, event.y_root)

    def get_tab_data(self, tab=None):
        tab = tab or self.notebook.nametowidget(self.notebook.select())
        return self.history[tab]

    def load_directory(self, tab, path):
        data = self.get_tab_data(tab)
        tree = data["tree"]
        tree.delete(*tree.get_children())
        data["path_var"].set(path)
        data["history"].append(path)

        try:
            for name in sorted(os.listdir(path)):
                full = os.path.join(path, name)
                size = os.path.getsize(full) if os.path.isfile(full) else "<DIR>"
                tree.insert('', 'end', text=name, values=[full, size])
        except Exception as e:
            messagebox.showerror("Erreur", str(e))

    def go_back(self, tab):
        data = self.get_tab_data(tab)
        if len(data["history"]) > 1:
            data["history"].pop()
            self.load_directory(tab, data["history"][-1])

    def on_double_click(self, tab):
        data = self.get_tab_data(tab)
        selected = data["tree"].selection()
        if not selected:
            return
        path = data["tree"].item(selected[0])['values'][0]
        self.open_selected(tab, path)

    def open_selected(self, tab, path):
        if os.path.isdir(path):
            self.load_directory(tab, path)
        elif path.lower().endswith(".txt"):
            self.open_text_file(path, editable=False)
        elif path.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif')):
            self.view_image(path)

    def open_text_file(self, path, editable=False):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            messagebox.showerror("Erreur", str(e))
            return

        win = tk.Toplevel(self)
        win.title(os.path.basename(path))
        text = tk.Text(win, wrap='word')
        text.insert('1.0', content)
        text.pack(fill=tk.BOTH, expand=True)

        if editable:
            def save():
                try:
                    with open(path, 'w', encoding='utf-8') as f:
                        f.write(text.get("1.0", tk.END))
                    win.destroy()
                except Exception as e:
                    messagebox.showerror("Erreur", str(e))
            tk.Button(win, text="💾 Enregistrer", command=save).pack()
        else:
            text.config(state='disabled')

    def view_image(self, path):
        try:
            img = Image.open(path)
            win = tk.Toplevel(self)
            win.title(os.path.basename(path))
            img.thumbnail((800, 600))
            tk_img = ImageTk.PhotoImage(img)
            label = tk.Label(win, image=tk_img)
            label.image = tk_img
            label.pack()
        except Exception as e:
            messagebox.showerror("Erreur", str(e))

    def update_filter(self, tab):
        data = self.get_tab_data(tab)
        query = data["search_var"].get().lower()
        path = data["path_var"].get()
        tree = data["tree"]
        tree.delete(*tree.get_children())
        try:
            for name in sorted(os.listdir(path)):
                if query in name.lower():
                    full = os.path.join(path, name)
                    size = os.path.getsize(full) if os.path.isfile(full) else "<DIR>"
                    tree.insert('', 'end', text=name, values=[full, size])
        except Exception:
            pass

    def get_selected_path(self, tab):
        data = self.get_tab_data(tab)
        selected = data["tree"].selection()
        if selected:
            return data["tree"].item(selected[0])['values'][0]
        return None

    def context_open(self, tab):
        path = self.get_selected_path(tab)
        if path:
            self.open_selected(tab, path)

    def context_edit(self, tab):
        path = self.get_selected_path(tab)
        if path and path.endswith(".txt"):
            self.open_text_file(path, editable=True)

    def context_view_image(self, tab):
        path = self.get_selected_path(tab)
        if path and path.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif')):
            self.view_image(path)

    def context_rename(self, tab):
        path = self.get_selected_path(tab)
        if path:
            new_name = simpledialog.askstring("Renommer", "Nouveau nom :", initialvalue=os.path.basename(path))
            if new_name:
                new_path = os.path.join(os.path.dirname(path), new_name)
                try:
                    os.rename(path, new_path)
                    self.load_directory(tab, os.path.dirname(path))
                except Exception as e:
                    messagebox.showerror("Erreur", str(e))

    def context_delete(self, tab):
        path = self.get_selected_path(tab)
        if path and messagebox.askyesno("Supprimer", f"Supprimer {path} ?"):
            try:
                if os.path.isdir(path):
                    shutil.rmtree(path)
                else:
                    os.remove(path)
                self.load_directory(tab, os.path.dirname(path))
            except Exception as e:
                messagebox.showerror("Erreur", str(e))

    def context_copy(self, tab):
        self.clipboard_path = self.get_selected_path(tab)

    def context_paste(self, tab):
        if self.clipboard_path:
            dest = self.get_tab_data(tab)["path_var"].get()
            try:
                base = os.path.basename(self.clipboard_path)
                dest_path = os.path.join(dest, base)
                if os.path.isdir(self.clipboard_path):
                    shutil.copytree(self.clipboard_path, dest_path)
                else:
                    shutil.copy2(self.clipboard_path, dest_path)
                self.load_directory(tab, dest)
            except Exception as e:
                messagebox.showerror("Erreur", str(e))

    def create_folder(self, tab=None):
        if not tab:
            tab = self.notebook.nametowidget(self.notebook.select())
        path = self.get_tab_data(tab)["path_var"].get()
        name = simpledialog.askstring("Nouveau dossier", "Nom du dossier :")
        if name:
            try:
                os.mkdir(os.path.join(path, name))
                self.load_directory(tab, path)
            except Exception as e:
                messagebox.showerror("Erreur", str(e))

    def add_to_favorites(self, tab=None):
        path = self.get_tab_data(tab)["path_var"].get()
        if path not in self.favorites:
            self.favorites.append(path)
            self.fav_menu.add_command(label=path, command=lambda p=path: self.add_tab(p))

if __name__ == "__main__":
    app = FileExplorer()
    app.mainloop()
