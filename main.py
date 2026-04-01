import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from exif_reader import extract_metadata, format_metadata_for_display, load_keywords
from injector import inject_keywords_into_image, process_folder
from renamer import rename_images


APP_TITLE = "SEO Image EXIF Optimizer"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_KEYWORD_FILE = os.path.join(BASE_DIR, "keywords.txt")


class SeoExifApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(APP_TITLE)
        self.root.geometry("980x640")
        self.root.minsize(860, 560)
        self.root.configure(bg="#f4efe8")

        self.image_path = None
        self.selected_folder = None
        self.keyword_file = DEFAULT_KEYWORD_FILE

        self._configure_styles()
        self._build_layout()
        self._load_default_keywords_into_ui()

    def _configure_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("App.TFrame", background="#f4efe8")
        style.configure("Card.TFrame", background="#fffaf3")
        style.configure("Title.TLabel", background="#f4efe8", foreground="#3b2f2f", font=("Segoe UI Semibold", 18))
        style.configure("Subtitle.TLabel", background="#f4efe8", foreground="#6e5b4f", font=("Segoe UI", 10))
        style.configure("Section.TLabel", background="#fffaf3", foreground="#3b2f2f", font=("Segoe UI Semibold", 11))
        style.configure("Action.TButton", font=("Segoe UI Semibold", 10), padding=8)
        style.map("Action.TButton", background=[("active", "#d9822b")])

    def _build_layout(self):
        container = ttk.Frame(self.root, padding=18, style="App.TFrame")
        container.pack(fill="both", expand=True)

        header = ttk.Frame(container, style="App.TFrame")
        header.pack(fill="x", pady=(0, 12))
        ttk.Label(header, text=APP_TITLE, style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            header,
            text="Upload an image, inspect metadata, inject SEO keywords, rename files, or process an entire folder.",
            style="Subtitle.TLabel",
        ).pack(anchor="w", pady=(4, 0))

        body = ttk.Frame(container, style="App.TFrame")
        body.pack(fill="both", expand=True)
        body.columnconfigure(0, weight=1)
        body.columnconfigure(1, weight=2)
        body.rowconfigure(0, weight=1)

        controls = ttk.Frame(body, padding=16, style="Card.TFrame")
        controls.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        viewer = ttk.Frame(body, padding=16, style="Card.TFrame")
        viewer.grid(row=0, column=1, sticky="nsew")
        viewer.rowconfigure(1, weight=1)
        viewer.columnconfigure(0, weight=1)

        ttk.Label(controls, text="Controls", style="Section.TLabel").pack(anchor="w")

        ttk.Button(controls, text="Upload Image", style="Action.TButton", command=self.select_image).pack(fill="x", pady=(12, 8))
        ttk.Button(controls, text="Choose Folder", style="Action.TButton", command=self.select_folder).pack(fill="x", pady=8)
        ttk.Button(controls, text="Inject Into Selected Image", style="Action.TButton", command=self.inject_keywords_for_selected_image).pack(fill="x", pady=8)
        ttk.Button(controls, text="Inject Into All Photos", style="Action.TButton", command=self.process_selected_folder).pack(fill="x", pady=8)
        ttk.Button(controls, text="Rename Images", style="Action.TButton", command=self.rename_selected_folder_images).pack(fill="x", pady=8)
        ttk.Button(controls, text="Reload Keywords File", style="Action.TButton", command=self.reload_keywords_preview).pack(fill="x", pady=8)

        ttk.Label(controls, text="Current image", style="Section.TLabel").pack(anchor="w", pady=(18, 6))
        self.image_label = tk.Label(controls, text="No image selected", bg="#fffaf3", fg="#6e5b4f", wraplength=260, justify="left", anchor="w")
        self.image_label.pack(fill="x")

        ttk.Label(controls, text="Current folder", style="Section.TLabel").pack(anchor="w", pady=(18, 6))
        self.folder_label = tk.Label(controls, text=BASE_DIR, bg="#fffaf3", fg="#6e5b4f", wraplength=260, justify="left", anchor="w")
        self.folder_label.pack(fill="x")

        ttk.Label(controls, text="Main keyword for renaming", style="Section.TLabel").pack(anchor="w", pady=(18, 6))
        self.main_keyword_var = tk.StringVar()
        keyword_entry = ttk.Entry(controls, textvariable=self.main_keyword_var)
        keyword_entry.pack(fill="x")
        tk.Label(
            controls,
            text="Used for names like keyword.jpg, keyword-2.jpg",
            bg="#fffaf3",
            fg="#8a7669",
            justify="left",
            anchor="w",
            wraplength=260,
        ).pack(fill="x", pady=(4, 0))

        ttk.Label(controls, text="Keywords to inject", style="Section.TLabel").pack(anchor="w", pady=(18, 6))
        self.manual_keywords_text = tk.Text(
            controls,
            height=7,
            wrap="word",
            font=("Consolas", 10),
            bg="#fffdf9",
            fg="#2f2722",
            relief="flat",
            padx=10,
            pady=10,
        )
        self.manual_keywords_text.pack(fill="both", pady=(0, 6))
        tk.Label(
            controls,
            text="Type one keyword per line, or leave this filled from keywords.txt.",
            bg="#fffaf3",
            fg="#8a7669",
            justify="left",
            anchor="w",
            wraplength=260,
        ).pack(fill="x")

        ttk.Label(controls, text="Keyword source (.txt)", style="Section.TLabel").pack(anchor="w", pady=(18, 6))
        self.keyword_file_label = tk.Label(controls, text=self.keyword_file, bg="#fffaf3", fg="#6e5b4f", wraplength=260, justify="left", anchor="w")
        self.keyword_file_label.pack(fill="x")

        ttk.Label(viewer, text="EXIF / Metadata Viewer", style="Section.TLabel").grid(row=0, column=0, sticky="w")
        self.metadata_text = tk.Text(viewer, wrap="word", font=("Consolas", 10), bg="#fffdf9", fg="#2f2722", relief="flat", padx=12, pady=12)
        self.metadata_text.grid(row=1, column=0, sticky="nsew", pady=(12, 0))
        viewer_scroll = ttk.Scrollbar(viewer, orient="vertical", command=self.metadata_text.yview)
        viewer_scroll.grid(row=1, column=1, sticky="ns", pady=(12, 0))
        self.metadata_text.configure(yscrollcommand=viewer_scroll.set)

        ttk.Label(viewer, text="Loaded keywords preview", style="Section.TLabel").grid(row=2, column=0, sticky="w", pady=(18, 0))
        self.keywords_preview = tk.Text(viewer, height=8, wrap="word", font=("Consolas", 10), bg="#fffdf9", fg="#2f2722", relief="flat", padx=12, pady=12)
        self.keywords_preview.grid(row=3, column=0, sticky="ew", pady=(12, 0))
        self.keywords_preview.configure(state="disabled")

    def _set_metadata_text(self, value: str):
        self.metadata_text.delete("1.0", tk.END)
        self.metadata_text.insert(tk.END, value)

    def _set_keywords_preview(self, lines):
        self.keywords_preview.configure(state="normal")
        self.keywords_preview.delete("1.0", tk.END)
        self.keywords_preview.insert(tk.END, "\n".join(lines))
        self.keywords_preview.configure(state="disabled")
        self.manual_keywords_text.delete("1.0", tk.END)
        self.manual_keywords_text.insert(tk.END, "\n".join(lines))
        if lines and not self.main_keyword_var.get().strip():
            self.main_keyword_var.set(lines[0])

    def _load_default_keywords_into_ui(self):
        try:
            keywords = load_keywords(self.keyword_file)
            self._set_keywords_preview(keywords)
        except Exception as exc:
            self._set_keywords_preview([f"Unable to load keywords: {exc}"])

    def reload_keywords_preview(self):
        self._load_default_keywords_into_ui()
        messagebox.showinfo(APP_TITLE, f"Keywords loaded from:\n{self.keyword_file}")

    def select_image(self):
        file_path = filedialog.askopenfilename(
            title="Select an image",
            filetypes=[("Images", "*.jpg *.jpeg *.png")],
        )
        if not file_path:
            return

        self.image_path = file_path
        self.selected_folder = os.path.dirname(file_path)
        self.image_label.configure(text=file_path)
        self.folder_label.configure(text=self.selected_folder)
        self._refresh_metadata_view(file_path)

    def select_folder(self):
        folder_path = filedialog.askdirectory(title="Select a folder with images")
        if not folder_path:
            return
        self.selected_folder = folder_path
        self.folder_label.configure(text=folder_path)
        messagebox.showinfo(APP_TITLE, f"Folder selected:\n{folder_path}")

    def _refresh_metadata_view(self, file_path: str):
        try:
            metadata = extract_metadata(file_path)
            self._set_metadata_text(format_metadata_for_display(metadata))
        except Exception as exc:
            self._set_metadata_text(f"Unable to read metadata.\n\n{exc}")
            messagebox.showerror(APP_TITLE, str(exc))

    def _load_keywords(self):
        typed_keywords = [
            line.strip()
            for line in self.manual_keywords_text.get("1.0", tk.END).splitlines()
            if line.strip()
        ]
        if typed_keywords:
            return typed_keywords
        return load_keywords(self.keyword_file)

    def _resolve_folder_path(self):
        folder_path = self.selected_folder or (os.path.dirname(self.image_path) if self.image_path else None)
        if folder_path and os.path.isdir(folder_path):
            return folder_path

        folder_path = filedialog.askdirectory(title="Select a folder with images")
        if folder_path:
            self.selected_folder = folder_path
            self.folder_label.configure(text=folder_path)
        return folder_path

    def inject_keywords_for_selected_image(self):
        if not self.image_path:
            messagebox.showwarning(APP_TITLE, "Please upload an image first.")
            return

        try:
            keywords = self._load_keywords()
            inject_keywords_into_image(self.image_path, keywords)
            self._refresh_metadata_view(self.image_path)
            messagebox.showinfo(APP_TITLE, "Keywords injected successfully into the selected image.")
        except Exception as exc:
            messagebox.showerror(APP_TITLE, f"Injection failed:\n{exc}")

    def rename_selected_folder_images(self):
        folder_path = self._resolve_folder_path()
        if not folder_path:
            messagebox.showwarning(APP_TITLE, "Please choose a folder or upload an image first.")
            return

        main_keyword = self.main_keyword_var.get().strip()
        if not main_keyword:
            try:
                main_keyword = self._load_keywords()[0]
                self.main_keyword_var.set(main_keyword)
            except Exception:
                main_keyword = ""
        if not main_keyword:
            messagebox.showwarning(APP_TITLE, "Please type a main keyword, or add at least one keyword in the keywords box.")
            return

        try:
            renamed = rename_images(folder_path, main_keyword)
            if self.image_path:
                current_name = os.path.basename(self.image_path)
                for old_name, new_name in renamed:
                    if old_name == current_name:
                        self.image_path = os.path.join(folder_path, new_name)
                        self.image_label.configure(text=self.image_path)
                        break
            summary = "\n".join(f"{old} -> {new}" for old, new in renamed[:10])
            if len(renamed) > 10:
                summary += f"\n... and {len(renamed) - 10} more file(s)."
            messagebox.showinfo(APP_TITLE, f"Renamed {len(renamed)} image(s).\n\n{summary}")
            if self.image_path:
                self._refresh_metadata_view(self.image_path)
        except Exception as exc:
            messagebox.showerror(APP_TITLE, f"Rename failed:\n{exc}")

    def process_selected_folder(self):
        folder_path = self._resolve_folder_path()
        if not folder_path:
            messagebox.showwarning(APP_TITLE, "Please choose a folder or upload an image first.")
            return

        try:
            keywords = self._load_keywords()
            processed, failures = process_folder(folder_path, keywords)
            if processed == 0 and not failures:
                messagebox.showwarning(APP_TITLE, "No supported images were found in the selected folder.")
                return

            if self.image_path and os.path.dirname(self.image_path) == folder_path:
                self._refresh_metadata_view(self.image_path)

            if failures:
                failure_text = "\n".join(failures[:10])
                if len(failures) > 10:
                    failure_text += f"\n... and {len(failures) - 10} more error(s)."
                messagebox.showwarning(
                    APP_TITLE,
                    f"Processed {processed} image(s) with {len(failures)} issue(s).\n\n{failure_text}",
                )
            else:
                messagebox.showinfo(APP_TITLE, f"Processed {processed} image(s) successfully.")
        except Exception as exc:
            messagebox.showerror(APP_TITLE, f"Folder processing failed:\n{exc}")


def run_app():
    root = tk.Tk()
    SeoExifApp(root)
    root.mainloop()


if __name__ == "__main__":
    run_app()
