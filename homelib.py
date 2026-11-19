# HomeLibrary — восстановленный исходный код
#
# Оригинал: HomeLibrary.exe (PyInstaller, Python 3.12), модуль homelib.pyc
# Декомпиляция: pycdc (https://github.com/zrax/pycdc) с патчами под Python 3.12
# Битые места восстановлены вручную по байткоду (pycdas) и отформатированы black

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import os
import zipfile
import shutil
import threading
import json

try:
    from tkdnd import TkDnD

    HAS_TKND = True
except ImportError:
    HAS_TKND = False


class ProgressWindow:
    STAGES = [
        ("Сканирование папки с книгами", 15),
        ("Чтение INPX файла", 30),
        ("Обработка индексных файлов", 50),
        ("Связывание с файлами", 80),
        ("Обновление интерфейса", 100),
    ]

    def __init__(self, parent):
        self.window = tk.Toplevel(parent)
        self.window.title("Индексация коллекции")
        self.window.geometry("450x180")
        self.window.resizable(False, False)
        self.window.transient(parent)
        self.window.grab_set()
        self.current_stage = tk.StringVar(value=self.STAGES[0][0])
        self.progress_var = tk.DoubleVar(value=0)
        self.detail_var = tk.StringVar(value="")
        ttk.Label(
            self.window, text="Индексация коллекции", font=("TkDefaultFont", 12, "bold")
        ).pack(pady=(15, 10))
        ttk.Label(self.window, textvariable=self.current_stage).pack()
        self.progress = ttk.Progressbar(
            self.window, mode="determinate", variable=self.progress_var, maximum=100
        )
        self.progress.pack(fill=tk.X, padx=30, pady=15)
        ttk.Label(self.window, textvariable=self.detail_var, foreground="gray").pack()
        self.cancelled = False
        self.window.protocol("WM_DELETE_WINDOW", self.on_cancel)
        self._after_id = None

    def on_cancel(self):
        self.cancelled = True

    def set_stage(self, stage_idx, detail=""):
        if self.cancelled:
            return None
        if stage_idx < len(self.STAGES):
            self.current_stage.set(self.STAGES[stage_idx][0])
        if detail:
            self.detail_var.set(detail)
        self._refresh()

    def set_progress(self, percent):
        if self.cancelled:
            return None
        self.progress_var.set(percent)
        self._refresh()

    def _refresh(self):
        if self._after_id:
            self.window.after_cancel(self._after_id)
        self._after_id = self.window.after(10, self.window.update)

    def close(self):
        if self._after_id:
            self.window.after_cancel(self._after_id)
        self.window.destroy()


GENRE_MAP = {
    "sf": "Научная фантастика",
    "sf_fantasy": "Фэнтези",
    "sf_det": "Детективная фантастика",
    "sf_cyberpunk": "Киберпанк",
    "sf_humor": "Юмористическая фантастика",
    "sf_history": "Альтернативная история",
    "sf_space": "Космическая фантастика",
    "det_classic": "Классический детектив",
    "det_police": "Полицейский детектив",
    "det_irony": "Иронический детектив",
    "det_crime": "Криминальный детектив",
    "det_horror": "Детектив-триллер",
    "det_action": "Боевик",
    "det_history": "Исторический детектив",
    "thriller": "Триллер",
    "horror": "Ужасы",
    "horror_cm": "Мистика",
    "prose_contemporary": "Современная проза",
    "prose_classic": "Классическая проза",
    "prose_history": "Историческая проза",
    "prose_military": "Военная проза",
    "prose": "Проза",
    "prose_short": "Малая проза",
    "love_contemporary": "Современные любовные романы",
    "love_history": "Исторические любовные романы",
    "love_short": "Короткие любовные романы",
    "love": "Романтика",
    "child_tale": "Сказка",
    "child_prose": "Детская проза",
    "child_verse": "Детские стихи",
    "child_sf": "Детская фантастика",
    "child": "Детская литература",
    "adv_western": "Вестерн",
    "adv_geo": "Путешествия",
    "adv_maritime": "Морские приключения",
    "adv_history": "Исторические приключения",
    "adventure": "Приключения",
    "fantasy": "Фэнтези",
    "fantasy_modern": "Современное фэнтези",
    "classics": "Классика",
    "sci_history": "История",
    "sci_philosophy": "Философия",
    "sci_psychology": "Психология",
    "sci_politics": "Политология",
    "sci_economy": "Экономика",
    "sci": "Наука",
    "poetry": "Поэзия",
    "humor": "Юмор",
    "nonfiction": "Документальное",
    "comp": "Компьютеры",
    "games": "Игры",
    "home": "Дом",
    "music": "Музыка",
    "religion": "Религия",
    "religion_rel": "Религия",
    "religion_esoterics": "Эзотерика",
    "religion_self": "Самопознание",
    "sci_juris": "Юриспруденция",
    "sci_medicine": "Медицина",
    "sci_tech": "Техника",
    "foreign": "Зарубежная литература",
    "foreign_prose": "Зарубежная проза",
    "foreignFantasy": "Зарубежное фэнтези",
    "foreign_sf": "Зарубежная фантастика",
    "antique": "Античная литература",
    "antique_ant": "Античность",
    "antique_east": "Восток",
    "fairy_tale": "Сказка",
    "child_expert": "Детская познавательная литература",
    "child_education": "Детская образовательная",
    "sf_etc": "Фантастика прочее",
    "sf_social": "Социальная фантастика",
    "sf_postapocalyptic": "Постапокалиптика",
    "sf_heroic": "Героическая фантастика",
    "sf_litrpg": "ЛитРПГ",
    "dramaturgy": "Драматургия",
    "foreign_antique": "Зарубежная классика",
    "design": "Искусство и дизайн",
    "arch_style": "Стиль и архитектура",
    "economy_management": "Менеджмент",
    "economy_marketing": "Маркетинг",
    "journals": "Журналы",
    "gadgets": "Гаджеты",
    "languages": "Иностранные языки",
}
GENRE_CATEGORIES = {
    "Фантастика": [
        "sf",
        "sf_fantasy",
        "sf_det",
        "sf_cyberpunk",
        "sf_humor",
        "sf_history",
        "sf_space",
        "sf_etc",
        "sf_social",
        "sf_postapocalyptic",
        "sf_heroic",
        "sf_litrpg",
    ],
    "Детективы": [
        "det_classic",
        "det_police",
        "det_irony",
        "det_crime",
        "det_horror",
        "det_action",
        "det_history",
        "thriller",
        "horror",
    ],
    "Проза": [
        "prose_contemporary",
        "prose_classic",
        "prose_history",
        "prose_military",
        "prose",
        "prose_short",
    ],
    "Любовные романы": ["love_contemporary", "love_history", "love_short", "love"],
    "Детское": [
        "child_tale",
        "child_prose",
        "child_verse",
        "child_sf",
        "child",
        "child_expert",
        "child_education",
    ],
    "Приключения": ["adv_western", "adv_geo", "adv_maritime", "adv_history", "adventure"],
    "Фэнтези": ["fantasy", "fantasy_modern"],
    "Наука и история": [
        "sci_history",
        "sci_philosophy",
        "sci_psychology",
        "sci_politics",
        "sci_economy",
        "sci",
        "sci_juris",
        "sci_medicine",
        "sci_tech",
    ],
    "Поэзия": ["poetry"],
    "Юмор": ["humor"],
    "Документальное": ["nonfiction"],
    "Компьютеры": ["comp"],
    "Игры": ["games"],
    "Дом": ["home"],
    "Музыка": ["music"],
    "Религия": ["religion", "religion_rel", "religion_esoterics", "religion_self"],
    "Классика": ["classics"],
    "Сказки": ["fairy_tale"],
    "Зарубежное": ["foreign", "foreign_prose", "foreignFantasy", "foreign_sf", "foreign_antique"],
    "Античное": ["antique", "antique_ant", "antique_east"],
    "Драматургия": ["dramaturgy"],
    "Искусство": ["design", "arch_style"],
    "Бизнес": ["economy_management", "economy_marketing"],
}


def get_genre_name(code):
    if not code:
        return ""
    codes = code.split(":")
    names = [GENRE_MAP.get(c.strip(), c.strip()) for c in codes if c.strip()]
    if names:
        return ", ".join(names)
    return code


class HomeLibrary:

    def __init__(self, root):
        self.root = root
        self.root.title("HomeLibrary")
        self.root.geometry("1400x800")
        self.books = []
        self.filtered_books = []
        self.inpx_path = ""
        self.books_path = ""
        self.zip_archives = {}
        self.authors = {}
        self.select_all_var = tk.BooleanVar(value=False)
        self.default_export_folder = ""
        self.saved_collections = {}
        self.data_dir = os.path.join(os.path.expanduser("~"), "HomeLibrary_data")
        os.makedirs(self.data_dir, exist_ok=True)
        self.config_file = os.path.join(self.data_dir, "config.json")
        self.load_config()
        self.setup_ui()
        if self.saved_collections:
            first_key = next(iter(self.saved_collections.keys()))
            self.root.after(200, lambda: self.load_collection(first_key, silent=True))
            return None

    def setup_ui(self):
        toolbar = ttk.Frame(self.root)
        toolbar.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        ttk.Button(toolbar, text="Загрузить библиотеку", command=self.load_library, padding=8).pack(
            side=tk.LEFT, padx=2
        )
        ttk.Button(toolbar, text="Экспорт FB2", command=self.export_selected, padding=8).pack(
            side=tk.LEFT, padx=2
        )
        settings_btn = ttk.Button(toolbar, text="⚙", width=3, command=self.show_settings_menu)
        settings_btn.pack(side=tk.LEFT, padx=2)
        status_frame = ttk.Frame(toolbar)
        status_frame.pack(side=tk.LEFT, padx=20)
        self.lbl_inpx = ttk.Label(status_frame, text="INPX: не выбран", foreground="gray")
        self.lbl_inpx.pack(anchor=tk.W)
        self.lbl_books = ttk.Label(status_frame, text="Папка книг: не выбрана", foreground="gray")
        self.lbl_books.pack(anchor=tk.W)
        self.settings_menu = tk.Menu(self.root, tearoff=0)
        self.settings_menu.add_command(
            label="Папка экспорта по умолчанию", command=self.set_default_export_folder
        )
        self.settings_menu.add_separator()
        self.settings_menu.add_command(label="Сохранить коллекцию", command=self.save_collection)
        self.setup_dnd()
        main_paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_paned.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=5, pady=5)
        left_frame = ttk.Frame(main_paned, width=300)
        main_paned.add(left_frame, weight=1)
        self.notebook = ttk.Notebook(left_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        search_frame = ttk.Frame(self.notebook)
        self.notebook.add(search_frame, text="Поиск")
        self.setup_search_tab(search_frame)
        genre_frame = ttk.Frame(self.notebook)
        self.notebook.add(genre_frame, text="Жанры")
        self.setup_genre_tab(genre_frame)
        author_frame = ttk.Frame(self.notebook)
        self.notebook.add(author_frame, text="Авторы")
        self.setup_author_tab(author_frame)
        right_frame = ttk.Frame(main_paned)
        main_paned.add(right_frame, weight=4)
        self.setup_book_list(right_frame)
        self.status_label = ttk.Label(self.root, text="Книг: 0", relief=tk.SUNKEN, anchor=tk.W)
        self.status_label.pack(side=tk.BOTTOM, fill=tk.X)
        if HAS_TKND:
            self.setup_drop_target(right_frame)
            return None

    def setup_dnd(self):
        pass

    def setup_drop_target(self, target):
        target.drop_target_register("DND_Files")
        target.dnd_bind("<<Drop>>", self.on_drop)
        lbl_drop = ttk.Label(
            target,
            text="Перетащите сюда INPX или папку с книгами",
            background="#e0e0e0",
            relief=tk.SUNKEN,
            padding=10,
        )
        lbl_drop.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
        self.lbl_drop = lbl_drop

    def on_drop(self, event):
        paths = self.root.tk.splitlist(event.data)
        for path in paths:
            path = path.strip("{}")
            if os.path.isfile(path) and path.endswith(".inpx"):
                print(f"""[DnD] INPX: {path}""")
                messagebox.showinfo("INPX", "Добавьте путь к папке с книгами для индексации")
                continue
            if os.path.isdir(path):
                print(f"""[DnD] Папка: {path}""")
                self.add_books_folder(path)
                continue
            print(f"""[DnD] Неизвестный тип: {path}""")

    def add_books_folder(self, folder):
        if not os.path.exists(folder):
            messagebox.showwarning("Ошибка", "Папка не существует")
            return None
        new_archives = {}
        new_fb2 = {}
        for f in os.listdir(folder):
            full_path = os.path.join(folder, f)
            if f.endswith(".zip"):
                new_archives[f] = full_path
                continue
            if not f.lower().endswith(".fb2"):
                continue
            new_fb2[f] = full_path
        added_archives = sum(1 for k, v in new_archives.items() if k not in self.zip_archives)
        added_fb2 = sum(1 for k, v in new_fb2.items() if k not in self.fb2_files)
        self.zip_archives.update(new_archives)
        self.fb2_files.update(new_fb2)
        if added_archives > 0 or added_fb2 > 0:
            self.match_books_with_files()
            self.update_tree()
            messagebox.showinfo(
                "Готово", f"""Добавлено: {added_archives} архивов, {added_fb2} fb2"""
            )
            print(f"""[DnD] Добавлено архивов: {added_archives}, fb2: {added_fb2}""")
            return None
        messagebox.showinfo("Информация", "Новых файлов не найдено")

    def setup_search_tab(self, parent):
        ttk.Label(parent, text="Автор:").pack(anchor=tk.W, padx=5, pady=(10, 0))
        self.ed_fullname = ttk.Entry(parent)
        self.ed_fullname.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(parent, text="Название:").pack(anchor=tk.W, padx=5, pady=(5, 0))
        self.ed_title = ttk.Entry(parent)
        self.ed_title.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(parent, text="Серия:").pack(anchor=tk.W, padx=5, pady=(5, 0))
        self.ed_series = ttk.Entry(parent)
        self.ed_series.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(parent, text="Жанр:").pack(anchor=tk.W, padx=5, pady=(5, 0))
        self.ed_genre = ttk.Combobox(
            parent, values=[""] + list(GENRE_MAP.values()), state="readonly"
        )
        self.ed_genre.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(parent, text="Аннотация:").pack(anchor=tk.W, padx=5, pady=(5, 0))
        self.ed_annotation = ttk.Entry(parent)
        self.ed_annotation.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(parent, text="Ключевые слова:").pack(anchor=tk.W, padx=5, pady=(5, 0))
        self.ed_keywords = ttk.Entry(parent)
        self.ed_keywords.pack(fill=tk.X, padx=5, pady=2)
        btn_frame = ttk.Frame(parent)
        btn_frame.pack(fill=tk.X, padx=5, pady=10)
        ttk.Button(btn_frame, text="Найти", command=self.do_search, padding=8).pack(
            side=tk.LEFT, expand=True, fill=tk.X, padx=2
        )
        ttk.Button(btn_frame, text="Очистить", command=self.clear_search, padding=8).pack(
            side=tk.LEFT, expand=True, fill=tk.X, padx=2
        )
        book_img_path = os.path.join(os.path.dirname(__file__), "book.png")
        if os.path.exists(book_img_path):
            self.book_img = tk.PhotoImage(file=book_img_path)
            scaled = self.book_img.subsample(6, 6)
            lbl = ttk.Label(parent, image=scaled)
            lbl.image = scaled
            lbl.pack(pady=5)
            return None

    def setup_genre_tab(self, parent):
        ttk.Label(parent, text="Выберите жанр:").pack(anchor=tk.W, padx=5, pady=5)
        self.genre_tree = ttk.Treeview(parent, show="tree", selectmode="browse")
        self.genre_tree.pack(fill=tk.BOTH, expand=True, padx=5)
        for cat, codes in GENRE_CATEGORIES.items():
            parent_node = self.genre_tree.insert("", tk.END, text=cat, open=False)
            for code in codes:
                name = GENRE_MAP.get(code, code)
                self.genre_tree.insert(parent_node, tk.END, text=name, tags=(code,))
        self.genre_tree.bind("<<TreeviewSelect>>", self.on_genre_select)
        self.genre_tree.bind("<Double-1>", self.on_genre_double_click)
        ttk.Button(
            parent, text="Показать книги жанра", command=self.show_genre_books, padding=5
        ).pack(pady=5)

    def setup_author_tab(self, parent):
        ttk.Label(parent, text="Поиск автора:").pack(anchor=tk.W, padx=5, pady=5)
        self.author_search = ttk.Entry(parent)
        self.author_search.pack(fill=tk.X, padx=5, pady=2)
        self.author_search.bind("<KeyRelease>", self.filter_authors)
        self.author_tree = ttk.Treeview(parent, show="tree", selectmode="browse")
        self.author_tree.pack(fill=tk.BOTH, expand=True, padx=5)
        self.author_tree.bind("<<TreeviewSelect>>", self.on_author_select)
        self.author_tree.bind("<Double-1>", self.on_author_double_click)
        ttk.Button(
            parent, text="Показать книги автора", command=self.show_author_books, padding=5
        ).pack(pady=5)

    def setup_book_list(self, parent):
        tree_frame = ttk.Frame(parent)
        tree_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=5)
        header_frame = ttk.Frame(tree_frame)
        header_frame.pack(side=tk.TOP, fill=tk.X, pady=(0, 2))
        self.select_all_check = ttk.Checkbutton(
            header_frame,
            text="Выбрать все",
            variable=self.select_all_var,
            command=self.toggle_select_all,
        )
        self.select_all_check.pack(side=tk.LEFT, pady=(0, 10))
        columns = ("#", "author", "title", "series", "genre", "size")
        self.tree = ttk.Treeview(
            tree_frame, columns=columns, show="headings", selectmode="extended"
        )
        self.tree.heading("#", text="#")
        self.tree.column("#", width=40)
        self.tree.heading("author", text="Автор")
        self.tree.column("author", width=200)
        self.tree.heading("title", text="Название")
        self.tree.column("title", width=350)
        self.tree.heading("series", text="Серия")
        self.tree.column("series", width=150)
        self.tree.heading("genre", text="Жанр")
        self.tree.column("genre", width=200)
        self.tree.heading("size", text="Размер")
        self.tree.column("size", width=80)
        for col in columns:
            self.tree.heading(col, command=lambda c=col: self.sort_tree(c))
        self.context_menu = tk.Menu(self.tree, tearoff=0)
        self.context_menu.add_command(label="Экспорт FB2", command=self.export_selected)
        self.tree.bind("<Button-3>", self.show_context_menu)
        vsb = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        hsb.pack(side=tk.BOTTOM, fill=tk.X)
        self.tree.bind("<Double-1>", lambda e=None: self.export_selected())
        self.sort_column = None
        self.sort_reverse = False

    def toggle_select_all(self):
        if self.select_all_var.get():
            self.tree.selection_add(*self.tree.get_children())
            return None
        self.tree.selection_remove(*self.tree.selection())

    def sort_tree(self, col):
        def get_sort_key(book):
            if col == "#":
                return self.filtered_books.index(book)
            if col == "author":
                return book.get("author", "").lower()
            if col == "title":
                return book.get("title", "").lower()
            if col == "series":
                return book.get("series", "").lower()
            if col == "genre":
                return book.get("genre", "").lower()
            if col == "size":
                size_str = book.get("size", "0 B")
                try:
                    parts = size_str.split()
                    if len(parts) == 2:
                        return float(parts[0]) * 1024 ** ["B", "KB", "MB", "GB"].index(parts[1])
                    return 0
                except:
                    return 0
            return ""

        if self.sort_column == col:
            self.sort_reverse = not self.sort_reverse
        else:
            self.sort_reverse = False
            self.sort_column = col
        self.filtered_books.sort(key=get_sort_key, reverse=self.sort_reverse)
        self.update_tree()

    def show_context_menu(self, event):
        if self.tree.selection():
            self.context_menu.post(event.x_root, event.y_root)
            return None

    def set_default_export_folder(self):
        folder = filedialog.askdirectory(title="Выберите папку для экспорта по умолчанию")
        if folder:
            self.default_export_folder = folder
            self.save_config()
            messagebox.showinfo("Сохранено", f"""Папка экспорта: {folder}""")
            return None

    def save_collection(self):
        name = simpledialog.askstring("Сохранить коллекцию", "Введите название коллекции:")
        if name:
            self.saved_collections[name] = {
                "inpx_path": self.inpx_path,
                "books_path": self.books_path,
                "default_export": self.default_export_folder,
            }
            self.save_config()
            self.update_collections_menu()
            messagebox.showinfo("Сохранено", f"""Коллекция \'{name}\' сохранена""")
            return None

    def load_config(self):
        self.active_collection = ""
        if os.path.exists(self.config_file):
            with open(self.config_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.default_export_folder = data.get("default_export_folder", "")
                self.saved_collections = data.get("saved_collections", {})
                if self.saved_collections:
                    self.active_collection = next(iter(self.saved_collections.keys()))

    def save_config(self):
        data = {
            "default_export_folder": self.default_export_folder,
            "saved_collections": self.saved_collections,
        }
        with open(self.config_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def show_settings_menu(self):
        x = self.root.winfo_x() + 10
        y = self.root.winfo_y() + 50
        self.settings_menu.post(x, y)

    def update_collections_menu(self):
        for i in range(self.settings_menu.index(tk.END), 3, -1):
            self.settings_menu.delete(i)
        if self.saved_collections:
            self.settings_menu.add_separator()
            for name in list(self.saved_collections.keys()):
                indicator = "✓ " if name == self.active_collection else "  "
                self.settings_menu.add_command(
                    label=f"{indicator}{name}", command=lambda n=name: self.load_collection(n)
                )
            self.settings_menu.add_separator()
            self.settings_menu.add_command(
                label="✕ Удалить коллекцию", command=self.delete_selected_collection
            )

    def delete_selected_collection(self):
        if not self.saved_collections:
            messagebox.showinfo("Информация", "Нет сохранённых коллекций")
            return None
        names = list(self.saved_collections.keys())
        if len(names) == 1:
            name = names[0]
            if messagebox.askyesno("Подтверждение", f"""Удалить коллекцию \'{name}\'?"""):
                del self.saved_collections[name]
                self.active_collection = ""
                self.save_config()
                self.update_collections_menu()
                messagebox.showinfo("Готово", f"""Коллекция \'{name}\' удалена""")
                return None
            return None
        msg = "Введите номер коллекции для удаления:\n\n"
        for i, name in enumerate(names, 1):
            msg += f"""{i}. {name}\n"""
        choice = simpledialog.askstring("Удалить коллекцию", msg)
        if choice:
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(names):
                    name = names[idx]
                    if messagebox.askyesno("Подтверждение", f"Удалить коллекцию '{name}'?"):
                        del self.saved_collections[name]
                        if name == self.active_collection:
                            self.active_collection = ""
                        self.save_config()
                        self.update_collections_menu()
                        messagebox.showinfo("Готово", f"Коллекция '{name}' удалена")
                        return None
                    return None
                return None
            except:
                return None

    def load_collection(self, name, silent=False):
        if name in self.saved_collections:
            self.active_collection = name
            data = self.saved_collections[name]
            self.inpx_path = data.get("inpx_path", "")
            self.books_path = data.get("books_path", "")
            self.default_export_folder = data.get("default_export", "")
            if self.inpx_path and os.path.exists(self.inpx_path):
                self.lbl_inpx.config(
                    text=f"""INPX: {os.path.basename(self.inpx_path)}""", foreground="black"
                )
            if self.books_path and os.path.exists(self.books_path):
                self.lbl_books.config(
                    text=f"""Папка книг: {os.path.basename(self.books_path)}""", foreground="black"
                )
            self.save_config()
            self.update_collections_menu()
            if silent:
                self._load_library_silent()
                return None
            self.load_library()
            return None

    def _load_library_internal(self):
        if not self.inpx_path or not self.books_path:
            return None
        if not os.path.exists(self.inpx_path) or not os.path.exists(self.books_path):
            messagebox.showwarning(
                "Внимание", "Файлы коллекции не найдены. Удалите коллекцию или выберите новую."
            )
            return None
        self.progress_window = ProgressWindow(self.root)

        def background_work():
            try:
                self._scan_books_background()
                self._parse_inpx_background()
            except Exception as e:
                self.root.after(0, lambda: self._on_index_error(str(e)))

        threading.Thread(target=background_work, daemon=True).start()

    def _load_library_silent(self):
        if not self.inpx_path or not self.books_path:
            return None
        if not os.path.exists(self.inpx_path) or not os.path.exists(self.books_path):
            return None

        def background_work():
            self._scan_books_background()
            self._parse_inpx_background_silent()

        threading.Thread(target=background_work, daemon=True).start()

    def _parse_inpx_background_silent(self):
        self.books = []
        self.authors = {}
        self.filtered_books = []

        try:
            with zipfile.ZipFile(self.inpx_path, "r") as zf:
                temp_dir = os.path.join(os.path.dirname(self.inpx_path), "_tmp_inpx")
                os.makedirs(temp_dir, exist_ok=True)
                zf.extractall(temp_dir)
                inp_files = []
                for root_dir, dirs, files in os.walk(temp_dir):
                    for fname in files:
                        if not fname.endswith(".inp"):
                            continue
                        inp_files.append(os.path.join(root_dir, fname))
                for fpath in inp_files:
                    with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                        self.parse_inp_content(f.read(), os.path.basename(fpath))
                shutil.rmtree(temp_dir, ignore_errors=True)
            self.match_books_with_files()
            self.filtered_books = self.books
            self.root.after(0, self.update_authors_list)
            self.root.after(0, self.update_tree)
        except Exception as e:
            print(f"Ошибка загрузки: {e}")

    def load_library(self):
        messagebox.showinfo("Шаг 1", "Выберите INPX-файл")
        inpx_file = filedialog.askopenfilename(
            title="Выберите INPX файл", filetypes=[("INPX файлы", "*.inpx"), ("Все файлы", "*.*")]
        )
        if not inpx_file:
            return None
        self.inpx_path = inpx_file
        self.lbl_inpx.config(text=f"""INPX: {os.path.basename(inpx_file)}""", foreground="black")
        messagebox.showinfo("Шаг 2", "Выберите путь к библиотеке на диске")
        books_folder = filedialog.askdirectory(title="Выберите папку с книгами (архивы или fb2)")
        if not books_folder:
            return None
        self.books_path = books_folder
        self.lbl_books.config(
            text=f"""Папка книг: {os.path.basename(books_folder)}""", foreground="black"
        )
        self.progress_window = ProgressWindow(self.root)

        def background_work():
            try:
                self._scan_books_background()
                self._parse_inpx_background()
            except Exception as e:
                self.root.after(0, lambda: self._on_index_error(str(e)))

        threading.Thread(target=background_work, daemon=True).start()

    def _scan_books_background(self):
        if hasattr(self, "progress_window"):
            self.root.after(0, lambda: self.progress_window.set_stage(0, "Сканирование папки..."))
        self.zip_archives = {}
        self.fb2_files = {}
        for f in os.listdir(self.books_path):
            if hasattr(self, "progress_window") and self.progress_window.cancelled:
                return None
            full_path = os.path.join(self.books_path, f)
            if f.endswith(".zip"):
                self.zip_archives[f] = full_path
                continue
            if not f.lower().endswith(".fb2"):
                continue
            self.fb2_files[f] = full_path
        if hasattr(self, "progress_window"):
            self.root.after(0, lambda: self.progress_window.set_progress(15))

    def _parse_inpx_background(self):
        self.books = []
        self.authors = {}
        self.filtered_books = []
        has_progress = hasattr(self, "progress_window")
        if has_progress:
            self.root.after(0, lambda: self.progress_window.set_stage(1, "Открытие INPX файла..."))
            self.root.after(0, lambda: self.progress_window.set_progress(20))
        try:
            with zipfile.ZipFile(self.inpx_path, "r") as zf:
                temp_dir = os.path.join(os.path.dirname(self.inpx_path), "_tmp_inpx")
                os.makedirs(temp_dir, exist_ok=True)
                zf.extractall(temp_dir)
                inp_files = []
                for root_dir, dirs, files in os.walk(temp_dir):
                    for fname in files:
                        if not fname.endswith(".inp"):
                            continue
                        inp_files.append(os.path.join(root_dir, fname))
                if has_progress:
                    self.root.after(
                        0,
                        lambda: self.progress_window.set_stage(
                            2, f"Найдено {len(inp_files)} файлов..."
                        ),
                    )
                total_files = len(inp_files)
                for idx, fpath in enumerate(inp_files):
                    if has_progress and self.progress_window.cancelled:
                        shutil.rmtree(temp_dir, ignore_errors=True)
                        self.root.after(
                            0,
                            lambda: (
                                self.progress_window.close(),
                                messagebox.showinfo("Отменено", "Индексация была отменена"),
                            ),
                        )
                        return None
                    with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                        self.parse_inp_content(f.read(), os.path.basename(fpath))
                    if has_progress:
                        progress = 20 + int((idx + 1) * 30 / total_files)
                        self.root.after(
                            0,
                            lambda p=progress: self.progress_window.set_progress(p)
                            or self.progress_window.set_stage(2, f"Книг: {len(self.books)}"),
                        )
                shutil.rmtree(temp_dir, ignore_errors=True)
            if has_progress:
                self.root.after(
                    0, lambda: self.progress_window.set_stage(3, "Связывание с файлами...")
                )
                self.root.after(0, lambda: self.progress_window.set_progress(80))
            if has_progress and self.progress_window.cancelled:
                return None
            self.match_books_with_files()
            self.filtered_books = self.books
            if has_progress:
                self.root.after(
                    0, lambda: self.progress_window.set_stage(4, "Обновление списка...")
                )
                self.root.after(0, lambda: self.progress_window.set_progress(90))

                def finish_load():
                    self.update_authors_list()
                    self.update_tree()
                    self.progress_window.set_progress(100)
                    self.progress_window.close()
                    messagebox.showinfo("Индексация завершена", f"Загружено {len(self.books)} книг")

                self.root.after(0, finish_load)
                return None
            self.update_authors_list()
            self.update_tree()
        except Exception as e:
            print(f"Ошибка: {e}")
            self.root.after(0, lambda: messagebox.showerror("Ошибка", str(e)))

    def _on_index_error(self, error):
        try:
            self.progress_window.close()
        except Exception:
            pass
        messagebox.showerror("Ошибка", f"Не удалось прочитать INPX:\n{error}")

    def parse_inp_content(self, content, inp_filename=""):
        delim = "\x04"
        first_book = len(self.books) == 0
        for line in content.split("\n"):
            line = line.strip()
            if not line:
                continue
            parts = line.split(delim)
            if not len(parts) >= 14:
                continue
            author_raw = parts[0].strip().rstrip(":")
            if author_raw:
                author_parts = author_raw.split(",")
                if len(author_parts) >= 3:
                    author = f"{author_parts[0].strip()} {author_parts[1].strip()} {author_parts[2].strip()}"
                elif len(author_parts) == 2:
                    author = f"{author_parts[0].strip()} {author_parts[1].strip()}"
                else:
                    author = author_parts[0].strip()
            else:
                author = "Неизвестный"
            genre_code = parts[1].strip().rstrip(":")
            title = parts[2].strip() or "Без названия"
            series = parts[3].strip()
            series_no = parts[4].strip()
            file_id = parts[5].strip()
            size = parts[6].strip()
            inside_no = int(parts[7].strip()) if parts[7].strip().isdigit() else 0
            deleted = parts[8].strip()
            ext = parts[9].strip()
            date = parts[10].strip()
            lang = parts[11].strip()
            lib_rate = parts[12].strip() if len(parts) > 12 else ""
            keywords = parts[13].strip() if len(parts) > 13 else ""
            genre_name = get_genre_name(genre_code)
            if series and series_no:
                series_display = f"""{series} #{series_no}"""
            elif series:
                series_display = series
            else:
                series_display = ""
            book = {
                "title": title,
                "author": author,
                "genre_code": genre_code,
                "genre": genre_name,
                "series": series_display,
                "filename": file_id,
                "archive": None,
                "size": self.format_size(int(size) if size.isdigit() else 0),
                "date": date,
                "lang": lang,
                "lib_rate": lib_rate,
                "keywords": keywords,
                "deleted": deleted == "1",
            }
            self.books.append(book)
            if author != "Неизвестный":
                self.authors[author] = self.authors.get(author, 0) + 1
            if not first_book:
                continue
            print(
                f"""[PARSE] Автор: \'{author}\', Жанр: \'{genre_code}\' -> \'{genre_name}\', Название: \'{title}\'"""
            )
            first_book = False

    def match_books_with_files(self):
        archive_index = {}
        for arc_name in self.zip_archives.keys():
            prefix = arc_name[:15].lower()
            if prefix not in archive_index:
                archive_index[prefix] = self.zip_archives[arc_name]
        fb2_index = {}
        for fb2_name in self.fb2_files.keys():
            fb2_base = os.path.splitext(fb2_name)[0].lower()
            fb2_index[fb2_base[:20]] = self.fb2_files[fb2_name]
        matched_count = 0
        for book in self.books:
            filename = book.get("filename", "")
            if not filename:
                continue
            name_lower = filename.lower()
            prefix = name_lower[:15]
            if prefix in archive_index:
                book["archive"] = archive_index[prefix]
                matched_count += 1
                continue
            fb2_prefix = name_lower[:20]
            if fb2_prefix in fb2_index:
                book["archive"] = fb2_index[fb2_prefix]
                matched_count += 1
        print(f"Связано с файлами: {matched_count}")

    def update_authors_list(self):
        self.author_tree.delete(*self.author_tree.get_children())
        for author in sorted(self.authors.keys()):
            self.author_tree.insert("", tk.END, text=author, tags=(author,))

    def update_tree(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        for idx, book in enumerate(self.filtered_books, 1):
            self.tree.insert(
                "",
                tk.END,
                values=(
                    idx,
                    book.get("author", ""),
                    book.get("title", ""),
                    book.get("series", ""),
                    book.get("genre", ""),
                    book.get("size", ""),
                ),
                tags=(book.get("archive") or "",),
            )
        self.status_label.config(text=f"Книг: {len(self.filtered_books)}")
        if self.filtered_books:
            self.select_all_check.state(["!disabled"])
            return None
        self.select_all_check.state(["disabled"])
        self.select_all_var.set(False)

    def on_genre_select(self, event):
        sel = self.genre_tree.selection()
        if sel:
            item = self.genre_tree.item(sel[0])
            tags = item["tags"]
            if tags:
                self.selected_genre_code = tags[0]
                self.selected_genre_name = item["text"]
                return None
            self.selected_genre_code = None
            self.selected_genre_name = item["text"]
            return None

    def show_genre_books(self):
        genre_code = getattr(self, "selected_genre_code", None)
        genre_name = getattr(self, "selected_genre_name", None)
        if genre_code:
            self.filtered_books = [b for b in self.books if genre_code in b.get("genre_code", "")]
        elif genre_name and genre_name in GENRE_CATEGORIES:
            codes = GENRE_CATEGORIES[genre_name]
            self.filtered_books = [
                b for b in self.books if any(c in b.get("genre_code", "") for c in codes)
            ]
        else:
            self.filtered_books = self.books
        self.update_tree()

    def on_genre_double_click(self, event):
        sel = self.genre_tree.selection()
        if sel:
            item = self.genre_tree.item(sel[0])
            tags = item["tags"]
            if tags:
                genre_code = tags[0]
                genre_name = item["text"]
                self.ed_genre.set(genre_name)
            else:
                genre_name = item["text"]
                self.ed_genre.set(genre_name)
            self.notebook.select(0)
            self.do_search()
            return None

    def on_author_select(self, event):
        sel = self.author_tree.selection()
        if sel:
            self.selected_author = self.author_tree.item(sel[0])["text"]
            return None
        self.selected_author = None

    def on_author_double_click(self, event):
        sel = self.author_tree.selection()
        if sel:
            author = self.author_tree.item(sel[0])["text"]
            self.ed_fullname.delete(0, tk.END)
            self.ed_fullname.insert(0, author)
            self.notebook.select(0)
            self.do_search()
            return None

    def filter_authors(self, event=None):
        query = self.author_search.get().upper()
        self.author_tree.delete(*self.author_tree.get_children())
        for author in sorted(self.authors.keys()):
            if not query in author.upper():
                continue
            self.author_tree.insert("", tk.END, text=author, tags=(author,))

    def show_author_books(self):
        author = getattr(self, "selected_author", None)
        if author:
            self.filtered_books = [
                b for b in self.books if author.lower() in b.get("author", "").lower()
            ]
        else:
            self.filtered_books = self.books
        self.update_tree()

    def do_search(self):
        query_author = self.ed_fullname.get().strip()
        query_title = self.ed_title.get().strip()
        query_series = self.ed_series.get().strip()
        query_genre = self.ed_genre.get().strip()
        query_annotation = self.ed_annotation.get().strip()
        query_keywords = self.ed_keywords.get().strip()
        genre_code = ""
        if query_genre:
            for code, name in GENRE_MAP.items():
                if not name == query_genre:
                    continue
                genre_code = code
        results = []
        for book in self.books:
            author = book.get("author", "")
            title = book.get("title", "")
            series = book.get("series", "")
            genre_code_book = book.get("genre_code", "")
            annotation = book.get("annotation", "").lower()
            keywords = book.get("keywords", "").lower()
            if query_author and query_author.upper() not in author.upper():
                continue
            if query_title and query_title.upper() not in title.upper():
                continue
            if query_series and query_series.upper() not in series.upper():
                continue
            if genre_code and genre_code not in genre_code_book:
                continue
            if query_annotation and query_annotation.lower() not in annotation:
                continue
            if query_keywords and query_keywords.lower() not in keywords:
                continue
            results.append(book)
        self.filtered_books = results
        self.update_tree()

    def clear_search(self):
        self.ed_fullname.delete(0, tk.END)
        self.ed_title.delete(0, tk.END)
        self.ed_series.delete(0, tk.END)
        self.ed_genre.set("")
        self.ed_annotation.delete(0, tk.END)
        self.ed_keywords.delete(0, tk.END)
        self.filtered_books = self.books
        self.update_tree()

    def format_size(self, size):
        for unit in ("B", "KB", "MB", "GB"):
            if size < 1024:
                return f"{size:.0f} {unit}"
            size /= 1024
        return f"{size:.1f} GB"

    def export_selected(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Внимание", "Выберите книгу")
            return None
        folder = filedialog.askdirectory(title="Папка для сохранения")
        if not folder:
            return None
        saved = 0
        errors = 0
        for item in selection:
            tags = self.tree.item(item, "tags")
            if not tags or not tags[0]:
                errors += 1
                continue
            archive = tags[0]
            if not os.path.exists(archive):
                errors += 1
                continue
            try:
                title = self.tree.set(item, "title")
                author = self.tree.set(item, "author")
                series = self.tree.set(item, "series")
                safe_title = "".join(c if c.isalnum() or c in " -_.," else "_" for c in title[:100])
                safe_author = "".join(c if c.isalnum() or c in " -_." else "_" for c in author[:50])
                if series:
                    new_name = f"{safe_author} - [{series}] {safe_title}.fb2"
                else:
                    new_name = f"{safe_author} - {safe_title}.fb2"
                new_path = os.path.join(folder, new_name)
                if archive.endswith(".zip") and zipfile.is_zipfile(archive):
                    with zipfile.ZipFile(archive, "r") as zf:
                        for n in zf.namelist():
                            if not n.endswith(".fb2"):
                                continue
                            zf.extract(n, folder)
                            original = os.path.join(folder, n)
                            if original != new_path and os.path.exists(new_path):
                                os.remove(new_path)
                            if original != new_path:
                                os.rename(original, new_path)
                            saved += 1
                elif archive.endswith(".fb2"):
                    import shutil as sh

                    sh.copy2(archive, new_path)
                    saved += 1
                else:
                    errors += 1
            except Exception as e:
                print(f"[EXPORT] Ошибка: {e}")
                errors += 1
                continue
        messagebox.showinfo("Готово", f"Сохранено: {saved}, Ошибок: {errors}")


def main():
    if HAS_TKND:
        root = TkDnD.Tk()
    else:
        root = tk.Tk()
    app = HomeLibrary(root)
    root.mainloop()


if __name__ == "__main__":
    main()
