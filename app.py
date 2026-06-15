import os
import sys
import json
import re
import threading
import subprocess
import tempfile
import io
import requests
import traceback
from PIL import Image, ImageTk, ImageDraw
import pystray
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk

def log_debug(text):
    try:
        log_path = "debug.log"
        if getattr(sys, 'frozen', False):
            log_path = os.path.join(os.path.dirname(sys.executable), "debug.log")
        else:
            log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "debug.log")
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(text + "\n")
    except Exception:
        pass

# Configuración básica de CustomTkinter
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

CONFIG_FILE = "config.json"

class YtDlpGUI(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("yt-dlp GUI")
        self.geometry("600x480")
        self.minsize(300, 200)
        self.overrideredirect(True)
        self.is_pinned = False
        threading.Thread(target=self._run_tray_icon, daemon=True).start()

        # Limpiar log anterior para no dejar historial
        try:
            log_path = "debug.log"
            if getattr(sys, 'frozen', False):
                log_path = os.path.join(os.path.dirname(sys.executable), "debug.log")
            else:
                log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "debug.log")
            if os.path.exists(log_path):
                os.remove(log_path)
        except:
            pass

        log_debug("\n--- APLICACIÓN INICIADA ---")

        # Cargar configuración
        self.load_config()

        # Variables de estado
        self.fetching = False
        self.downloading = False
        self.video_metadata = None
        self.temp_thumbnail_path = None

        # Crear interfaz gráfica
        self.setup_ui()

    def load_config(self):
        default_dir = os.path.join(os.path.expanduser('~'), 'Downloads')
        if not os.path.exists(default_dir):
            default_dir = os.path.join(os.path.expanduser('~'), 'Desktop')

        self.config = {
            "ytdlp_path": r"C:\Users\Usuario\Desktop\yt-dlp (La herramienta definitiva)\yt-dlp.exe",
            "download_dir": default_dir
        }

        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    saved = json.load(f)
                    self.config.update(saved)
            except Exception as e:
                print(f"Error cargando config.json: {e}")

    def save_config(self):
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Error guardando config.json: {e}")

    def setup_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(4, weight=1)

        # --- Invisible Drag Area & Window Controls ---
        self.title_bar = ctk.CTkFrame(self, height=24, corner_radius=0, fg_color="transparent")
        self.title_bar.grid(row=0, column=0, sticky="ew", pady=(2, 0))
        self.title_bar.bind("<ButtonPress-1>", self.start_move)
        self.title_bar.bind("<B1-Motion>", self.do_move)
        
        self.title_label = ctk.CTkLabel(self.title_bar, text=" YT-DLP", font=ctk.CTkFont(size=10, weight="bold"), text_color="#555555")
        self.title_label.pack(side="left", padx=5)
        self.title_label.bind("<ButtonPress-1>", self.start_move)
        self.title_label.bind("<B1-Motion>", self.do_move)

        close_btn = ctk.CTkButton(self.title_bar, text="✕", width=24, height=24, font=ctk.CTkFont(size=10), fg_color="transparent", hover_color="#EF4444", command=self.quit_app)
        close_btn.pack(side="right", padx=2)

        min_btn = ctk.CTkButton(self.title_bar, text="🗕", width=24, height=24, font=ctk.CTkFont(size=10), fg_color="transparent", hover_color="#333333", command=self.minimize_to_tray)
        min_btn.pack(side="right", padx=2)

        self.pin_btn = ctk.CTkButton(self.title_bar, text="📌", width=24, height=24, font=ctk.CTkFont(size=10), text_color="#EF4444", fg_color="transparent", hover_color="#333333", command=self.toggle_pin)
        self.pin_btn.pack(side="right", padx=2)

        # --- Fila 1: Configuración de yt-dlp.exe ---
        ytdlp_frame = ctk.CTkFrame(self)
        ytdlp_frame.grid(row=1, column=0, padx=2, pady=1, sticky="ew")
        ytdlp_frame.grid_columnconfigure(1, weight=1)

        ytdlp_lbl = ctk.CTkLabel(ytdlp_frame, text="Ruta yt-dlp.exe:", font=ctk.CTkFont(size=10, weight="bold"))
        ytdlp_lbl.grid(row=0, column=0, padx=(5, 5), pady=2, sticky="w")

        self.ytdlp_entry = ctk.CTkEntry(ytdlp_frame, height=24, font=ctk.CTkFont(size=10))
        self.ytdlp_entry.insert(0, self.config["ytdlp_path"])
        self.ytdlp_entry.grid(row=0, column=1, padx=5, pady=2, sticky="ew")

        ytdlp_btn = ctk.CTkButton(ytdlp_frame, text="Buscar...", width=50, height=24, height=24, command=self.browse_ytdlp)
        ytdlp_btn.grid(row=0, column=2, padx=(5, 15), pady=2)

        # --- Fila 2: Entrada de Enlace (URL) ---
        url_frame = ctk.CTkFrame(self)
        url_frame.grid(row=2, column=0, padx=2, pady=1, sticky="ew")
        url_frame.grid_columnconfigure(1, weight=1)

        url_lbl = ctk.CTkLabel(url_frame, text="Enlace de Video:", font=ctk.CTkFont(size=10, weight="bold"))
        url_lbl.grid(row=0, column=0, padx=(5, 5), pady=1, sticky="w")

        self.url_entry = ctk.CTkEntry(url_frame, height=24, font=ctk.CTkFont(size=10), placeholder_text="Pega el link del video aquí (YouTube, Vimeo, etc.)...")
        self.url_entry.grid(row=0, column=1, padx=5, pady=1, sticky="ew")

        paste_btn = ctk.CTkButton(url_frame, text="Pegar", width=50, height=24, fg_color="#4B5563", hover_color="#374151", command=self.paste_url)
        paste_btn.grid(row=0, column=2, padx=5, pady=1)

        self.fetch_btn = ctk.CTkButton(url_frame, text="Obtener Info", width=80, height=24, fg_color="#2563EB", hover_color="#1D4ED8", command=self.start_fetch_metadata)
        self.fetch_btn.grid(row=0, column=3, padx=(5, 15), pady=1)

        # --- Fila 3: Tarjeta de Información del Video & Opciones ---
        self.main_info_frame = ctk.CTkFrame(self)
        self.main_info_frame.grid(row=3, column=0, padx=2, pady=1, sticky="nsew")
        self.main_info_frame.grid_columnconfigure(0, weight=1)
        self.main_info_frame.grid_rowconfigure(0, weight=1)

        # Sub-frame para cuando NO hay video cargado (Placeholder)
        self.placeholder_frame = ctk.CTkFrame(self.main_info_frame, fg_color="transparent")
        self.placeholder_frame.grid(row=0, column=0, padx=2, pady=30, sticky="nsew")
        
        self.placeholder_label = ctk.CTkLabel(
            self.placeholder_frame, 
            text="Introduce un enlace de video y haz clic en 'Obtener Info'\npara cargar las opciones de descarga.",
            font=ctk.CTkFont(size=10),
            text_color="gray"
        )
        self.placeholder_label.pack(expand=True)

        # Sub-frame para cuando SÍ hay video cargado
        self.video_details_frame = ctk.CTkFrame(self.main_info_frame, fg_color="transparent")
        # No se posiciona (grid) todavía, se mostrará dinámicamente

        # Configurar columnas de video_details_frame: izquierda Thumbnail, derecha Información y opciones
        self.video_details_frame.grid_columnconfigure(1, weight=1)

        # Miniatura
        self.thumbnail_label = ctk.CTkLabel(self.video_details_frame, text="[Sin Miniatura]", width=120, height=70, fg_color="#1F2937", corner_radius=8)
        self.thumbnail_label.grid(row=0, column=0, rowspan=4, padx=(5, 5), pady=1, sticky="nw")

        # Metadatos del video (Editable)
        self.vid_title_entry = ctk.CTkTextbox(self.video_details_frame, font=ctk.CTkFont(size=11, weight="bold"), width=300, height=80, wrap="word")
        self.vid_title_entry.insert("1.0", "Título del Video")
        self.vid_title_entry.grid(row=0, column=1, padx=(0, 5), pady=2, sticky="w")

        self.vid_duration_lbl = ctk.CTkLabel(self.video_details_frame, text="Duración: --:-- | Canal: --", font=ctk.CTkFont(size=10), text_color="gray")
        self.vid_duration_lbl.grid(row=1, column=1, padx=(0, 5), pady=2, sticky="w")

        # Fila de opciones de descarga
        options_panel = ctk.CTkFrame(self.video_details_frame, fg_color="transparent")
        options_panel.grid(row=2, column=1, padx=(0, 5), pady=2, sticky="ew")
        options_panel.grid_columnconfigure(1, weight=1)

        # Selector de Calidad
        qual_lbl = ctk.CTkLabel(options_panel, text="Calidad:", font=ctk.CTkFont(size=10, weight="bold"))
        qual_lbl.grid(row=0, column=0, padx=(0, 10), pady=1, sticky="w")

        self.quality_combo = ctk.CTkComboBox(options_panel, height=24, font=ctk.CTkFont(size=10), dropdown_font=ctk.CTkFont(size=10), values=[
            "Mejor Calidad Disponible (Video + Audio)",
            "1080p (Full HD)",
            "720p (HD)",
            "480p (SD)",
            "Solo Audio (MP3 - Alta Calidad)",
            "Solo Audio (M4A)"
        ], width=200)
        self.quality_combo.grid(row=0, column=1, padx=0, pady=1, sticky="w")

        # Selector de Carpeta Destino
        dest_lbl = ctk.CTkLabel(options_panel, text="Destino:", font=ctk.CTkFont(size=10, weight="bold"))
        dest_lbl.grid(row=1, column=0, padx=(0, 10), pady=1, sticky="w")

        self.dest_entry = ctk.CTkEntry(options_panel, height=24, font=ctk.CTkFont(size=10), width=200)
        self.dest_entry.insert(0, self.config["download_dir"])
        self.dest_entry.grid(row=1, column=1, padx=0, pady=1, sticky="w")

        dest_btn = ctk.CTkButton(options_panel, text="Elegir...", width=70, command=self.browse_dest)
        dest_btn.grid(row=1, column=2, padx=(10, 0), pady=1)

        # Botón de Descarga
        self.download_btn = ctk.CTkButton(self.video_details_frame, text="DESCARGAR VIDEO", font=ctk.CTkFont(size=10, weight="bold"), fg_color="#10B981", hover_color="#059669", height=35, command=self.start_download)
        self.download_btn.grid(row=3, column=1, padx=(0, 5), pady=(5, 15), sticky="w")

        # --- Fila 4: Progreso, Estado y Consola ---
        self.bottom_frame = ctk.CTkFrame(self)
        self.bottom_frame.grid(row=4, column=0, padx=2, pady=(5, 15), sticky="nsew")
        self.bottom_frame.grid_columnconfigure(0, weight=1)
        self.bottom_frame.grid_rowconfigure(3, weight=1)  # Fila del Log de consola

        # Estado del descarga
        self.status_lbl = ctk.CTkLabel(self.bottom_frame, text="Estado: Listo", font=ctk.CTkFont(size=10, weight="bold"))
        self.status_lbl.grid(row=0, column=0, padx=5, pady=(10, 2), sticky="w")

        # Barra de progreso
        self.progress_bar = ctk.CTkProgressBar(self.bottom_frame, height=10)
        self.progress_bar.set(0.0)
        self.progress_bar.grid(row=1, column=0, padx=5, pady=1, sticky="ew")

        # Estadísticas (Velocidad, ETA, Porcentaje)
        self.stats_lbl = ctk.CTkLabel(self.bottom_frame, text="Progreso: 0% | Velocidad: -- | ETA: --", font=ctk.CTkFont(size=10), text_color="gray")
        self.stats_lbl.grid(row=2, column=0, padx=5, pady=(2, 10), sticky="w")

        # Consola Colapsable
        console_header_frame = ctk.CTkFrame(self.bottom_frame, fg_color="transparent")
        console_header_frame.grid(row=3, column=0, padx=5, pady=(0, 5), sticky="ew")
        
        self.show_console_var = tk.BooleanVar(value=False)
        self.console_checkbox = ctk.CTkCheckBox(console_header_frame, text="Mostrar consola de depuración", variable=self.show_console_var, command=self.toggle_console, font=ctk.CTkFont(size=11))
        self.console_checkbox.pack(side="left")

        self.console_text = ctk.CTkTextbox(self.bottom_frame, font=ctk.CTkFont(family="Consolas", size=10), fg_color="#0F172A", text_color="#F8FAFC", state="disabled")
        # No se ubica inicialmente (está colapsada)

        # Botones extra abajo
        btn_frame = ctk.CTkFrame(self.bottom_frame, fg_color="transparent")
        btn_frame.grid(row=5, column=0, pady=(10, 0), sticky="e")

        donate_btn = ctk.CTkButton(btn_frame, text="💖 Donar a Matecito", width=120, fg_color="#F97316", hover_color="#EA580C", command=self.show_donate)
        donate_btn.pack(side="right", padx=5)

        about_btn = ctk.CTkButton(btn_frame, text="ℹ️ Acerca de", width=80, height=24, fg_color="#64748B", hover_color="#475569", command=self.show_about)
        about_btn.pack(side="right", padx=5)

        # SizeGrip para redimensionar
        self.grip = ctk.CTkLabel(self.bottom_frame, text=" ⤡ ", text_color="gray", cursor="size_nw_se", font=ctk.CTkFont(size=16))
        self.grip.grid(row=6, column=0, sticky="se")
        self.grip.bind("<ButtonPress-1>", self.start_resize)
        self.grip.bind("<B1-Motion>", self.do_resize)

    # --- Lógica de Ventana Minimalista ---
    def start_move(self, event):
        self.x = event.x
        self.y = event.y

    def do_move(self, event):
        deltax = event.x - self.x
        deltay = event.y - self.y
        x = self.winfo_x() + deltax
        y = self.winfo_y() + deltay
        self.geometry(f"+{x}+{y}")

    def start_resize(self, event):
        self.start_w = self.winfo_width()
        self.start_h = self.winfo_height()
        self.start_x = event.x_root
        self.start_y = event.y_root

    def do_resize(self, event):
        del_x = event.x_root - self.start_x
        del_y = event.y_root - self.start_y
        new_w = max(300, self.start_w + del_x)
        new_h = max(200, self.start_h + del_y)
        self.geometry(f"{new_w}x{new_h}")

    def toggle_pin(self):
        self.is_pinned = not self.is_pinned
        self.attributes("-topmost", self.is_pinned)
        self.pin_btn.configure(text_color="#FFFFFF" if self.is_pinned else "#EF4444")

    def minimize_to_tray(self):
        self.withdraw()

    def quit_app(self):
        if self.tray_icon:
            self.tray_icon.stop()
        self.quit()
        sys.exit(0)

    def _run_tray_icon(self):
        image = Image.new('RGB', (64, 64), color=(30, 30, 30))
        d = ImageDraw.Draw(image)
        d.rectangle([16, 16, 48, 48], fill=(255, 60, 60))
        
        def show_window(icon, item):
            self.after(0, self.deiconify)
        
        def quit_from_tray(icon, item):
            self.after(0, self.quit_app)

        menu = pystray.Menu(
            pystray.MenuItem("Mostrar YT-DLP GUI", show_window, default=True),
            pystray.MenuItem("Cerrar del todo", quit_from_tray)
        )
        self.tray_icon = pystray.Icon("ytdlpgui", image, "YT-DLP Downloader", menu)
        self.tray_icon.run()

    # --- Acciones de Configuración de Rutas ---
    def browse_ytdlp(self):
        file_path = filedialog.askopenfilename(
            title="Seleccionar yt-dlp.exe",
            filetypes=[("Archivos Ejecutables", "*.exe"), ("Todos los archivos", "*.*")]
        )
        if file_path:
            file_path = os.path.normpath(file_path)
            self.ytdlp_entry.delete(0, tk.END)
            self.ytdlp_entry.insert(0, file_path)
            self.config["ytdlp_path"] = file_path
            self.save_config()

    def browse_dest(self):
        dir_path = filedialog.askdirectory(title="Seleccionar Carpeta de Descarga")
        if dir_path:
            dir_path = os.path.normpath(dir_path)
            self.dest_entry.delete(0, tk.END)
            self.dest_entry.insert(0, dir_path)
            self.config["download_dir"] = dir_path
            self.save_config()

    def paste_url(self):
        try:
            clipboard = self.clipboard_get()
            self.url_entry.delete(0, tk.END)
            self.url_entry.insert(0, clipboard)
        except Exception:
            pass

    def toggle_console(self):
        if self.show_console_var.get():
            self.console_text.grid(row=4, column=0, padx=5, pady=(0, 10), sticky="nsew")
        else:
            self.console_text.grid_forget()

    def show_about(self):
        import webbrowser
        def open_link(url):
            webbrowser.open(url)
            
        about_window = ctk.CTkToplevel(self)
        about_window.title("Acerca de")
        about_window.geometry("450x250")
        about_window.attributes("-topmost", True)
        about_window.resizable(False, False)
        
        info_label = ctk.CTkLabel(about_window, text="YT-DLP GUI\nUna interfaz gráfica moderna para yt-dlp.\nDesarrollado con ♥ por servicepcglew.", font=ctk.CTkFont(size=10))
        info_label.pack(pady=2)
        
        links_frame = ctk.CTkFrame(about_window, fg_color="transparent")
        links_frame.pack(pady=2)
        
        ctk.CTkButton(links_frame, text="GitHub", width=90, fg_color="#333333", hover_color="#555555", command=lambda: open_link("https://github.com/servicepcglew")).grid(row=0, column=0, padx=5)
        ctk.CTkButton(links_frame, text="YouTube", width=90, fg_color="#EF4444", hover_color="#DC2626", command=lambda: open_link("https://youtube.com/@servicepcglew")).grid(row=0, column=1, padx=5)
        ctk.CTkButton(links_frame, text="Instagram", width=90, fg_color="#D946EF", hover_color="#C026D3", command=lambda: open_link("https://instagram.com/servicepcglew")).grid(row=0, column=2, padx=5)
        ctk.CTkButton(links_frame, text="Facebook", width=90, fg_color="#3B82F6", hover_color="#2563EB", command=lambda: open_link("https://facebook.com/servicepcglew")).grid(row=0, column=3, padx=5)

    def show_donate(self):
        import webbrowser
        webbrowser.open("https://matecito.co/servicepcglew")

    def log_to_console(self, text):
        self.after(0, lambda: self._log_to_console_main_thread(text))

    def _log_to_console_main_thread(self, text):
        self.console_text.configure(state="normal")
        self.console_text.insert(tk.END, text + "\n")
        self.console_text.see(tk.END)
        self.console_text.configure(state="disabled")

    # --- Lógica de Obtención de Metadatos ---
    def start_fetch_metadata(self):
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showwarning("Falta Enlace", "Por favor introduce un enlace de video.")
            return

        ytdlp_path = self.ytdlp_entry.get().strip()
        log_debug(f"start_fetch_metadata: URL={url} | Path={ytdlp_path}")
        if not os.path.exists(ytdlp_path):
            log_debug(f"Error: yt-dlp.exe no existe en {ytdlp_path}")
            messagebox.showerror("Error de Ruta", f"No se encontró el ejecutable yt-dlp.exe en:\n{ytdlp_path}\n\nPor favor, búscalo usando el botón 'Buscar...'")
            return

        # Bloquear botones
        self.fetching = True
        self.fetch_btn.configure(state="disabled", text="Cargando...")
        self.status_lbl.configure(text="Estado: Obteniendo información del video...")
        
        # Ocultar paneles anteriores
        self.video_details_frame.grid_forget()
        self.placeholder_frame.grid_forget()
        
        # Label temporal de carga
        self.loading_lbl = ctk.CTkLabel(self.main_info_frame, text="Cargando metadatos y miniatura...", font=ctk.CTkFont(size=10))
        self.loading_lbl.grid(row=0, column=0, padx=2, pady=30, sticky="nsew")

        # Limpiar log anterior
        self.console_text.configure(state="normal")
        self.console_text.delete("1.0", tk.END)
        self.console_text.configure(state="disabled")

        # Iniciar hilo de carga
        log_debug("Iniciando hilo _fetch_metadata_thread...")
        threading.Thread(target=self._fetch_metadata_thread, args=(url, ytdlp_path), daemon=True).start()

    def _fetch_metadata_thread(self, url, ytdlp_path):
        log_debug("Hilo _fetch_metadata_thread en ejecución...")
        try:
            self.log_to_console(f"Ejecutando yt-dlp para obtener metadatos de: {url}")
            
            # Comando yt-dlp para obtener info en formato JSON sin caché
            cmd = [ytdlp_path, "--no-cache-dir", "-j", "--no-playlist", url]
            log_debug(f"Ejecutando comando: {cmd}")
            
            process = subprocess.Popen(
                cmd,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                encoding='utf-8',
                errors='replace',
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            log_debug("Subproceso Popen creado.")
            
            stdout, stderr = process.communicate()
            log_debug(f"Proceso finalizado. Código de retorno: {process.returncode}")
            
            if process.returncode != 0:
                log_debug(f"Error devuelto por yt-dlp:\n{stderr}")
                self.log_to_console(f"Error devuelto por yt-dlp (Código {process.returncode}):\n{stderr}")
                self.after(0, lambda: self.on_fetch_error("Error al obtener información del video. Verifica el enlace y la consola."))
                return

            log_debug(f"Salida recibida (longitud={len(stdout)}). Cargando JSON...")
            try:
                metadata = json.loads(stdout)
                log_debug("JSON cargado con éxito.")
            except Exception as json_err:
                log_debug(f"Excepción al decodificar JSON: {json_err}\nSalida stdout truncada:\n{stdout[:1000]}")
                raise json_err

            self.video_metadata = metadata
            
            title = metadata.get("title", "Título desconocido")
            duration_secs = int(float(metadata.get("duration", 0) or 0))
            uploader = metadata.get("uploader", metadata.get("channel", "Canal desconocido"))
            thumbnail_url = metadata.get("thumbnail")
            
            log_debug(f"Metadatos: título='{title}', duración={duration_secs}, canal='{uploader}', miniatura='{thumbnail_url}'")
            
            # Dar formato a la duración
            duration_str = "Desconocida"
            if duration_secs:
                mins, secs = divmod(duration_secs, 60)
                hours, mins = divmod(mins, 60)
                if hours:
                    duration_str = f"{hours:02d}:{mins:02d}:{secs:02d}"
                else:
                    duration_str = f"{mins:02d}:{secs:02d}"

            self.log_to_console(f"Metadatos cargados con éxito:\nTítulo: {title}\nDuración: {duration_str}\nCanal: {uploader}")

            # Descargar miniatura en un hilo separado o procesarla
            img = None
            if thumbnail_url:
                try:
                    log_debug(f"Descargando miniatura desde: {thumbnail_url}")
                    response = requests.get(thumbnail_url, timeout=10)
                    log_debug(f"Respuesta de miniatura status={response.status_code}")
                    if response.status_code == 200:
                        img_data = response.content
                        img = Image.open(io.BytesIO(img_data))
                        # Redimensionar a 160x90 manteniendo calidad
                        img = img.resize((160, 90), Image.Resampling.LANCZOS)
                        log_debug("Miniatura redimensionada correctamente.")
                except Exception as img_err:
                    log_debug(f"Excepción descargando miniatura: {img_err}")
                    self.log_to_console(f"Error descargando miniatura: {img_err}")

            log_debug("Llamando a on_fetch_success...")
            self.after(0, lambda: self.on_fetch_success(title, duration_str, uploader, img))

        except Exception as e:
            tb = traceback.format_exc()
            log_debug(f"Excepción en _fetch_metadata_thread:\n{tb}")
            self.log_to_console(f"Excepción en el hilo de metadatos: {e}")
            self.after(0, lambda: self.on_fetch_error(f"Excepción: {str(e)}"))

    def on_fetch_success(self, title, duration, uploader, img):
        self.fetching = False
        self.fetch_btn.configure(state="normal", text="Obtener Info")
        self.status_lbl.configure(text="Estado: Metadatos cargados correctamente.")
        
        # Eliminar label de carga
        if hasattr(self, 'loading_lbl'):
            self.loading_lbl.grid_forget()

        # Mostrar miniatura si está disponible
        if img:
            self.ctk_image = ctk.CTkImage(light_image=img, dark_image=img, size=(160, 90))
            self.thumbnail_label.configure(image=self.ctk_image, text="")
        else:
            self.thumbnail_label.configure(image=None, text="[Sin Miniatura]")

        # Actualizar textos
        self.vid_title_entry.delete("1.0", tk.END)
        self.vid_title_entry.insert("1.0", title)
        self.vid_duration_lbl.configure(text=f"Duración: {duration} | Canal: {uploader}")
        
        # Mostrar panel de video
        self.video_details_frame.grid(row=0, column=0, padx=5, pady=1, sticky="nsew")

    def on_fetch_error(self, err_msg):
        self.fetching = False
        self.fetch_btn.configure(state="normal", text="Obtener Info")
        self.status_lbl.configure(text="Estado: Error al obtener información.")
        
        if hasattr(self, 'loading_lbl'):
            self.loading_lbl.grid_forget()
            
        self.placeholder_frame.grid(row=0, column=0, padx=2, pady=30, sticky="nsew")
        messagebox.showerror("Error", err_msg)


    def is_ffmpeg_available(self):
        import shutil
        if shutil.which("ffmpeg"):
            return True
        ytdlp_path = self.ytdlp_entry.get().strip()
        if os.path.exists(ytdlp_path):
            ytdlp_dir = os.path.dirname(ytdlp_path)
            if os.path.exists(os.path.join(ytdlp_dir, "ffmpeg.exe")):
                return True
        if getattr(sys, 'frozen', False):
            app_dir = os.path.dirname(sys.executable)
        else:
            app_dir = os.path.dirname(os.path.abspath(__file__))
        if os.path.exists(os.path.join(app_dir, "ffmpeg.exe")):
            return True
        if os.path.exists(os.path.join(os.path.dirname(app_dir), "ffmpeg.exe")):
            return True
        return False

    # --- Lógica de Descarga ---
    def start_download(self):
        if self.downloading:
            return

        url = self.url_entry.get().strip()
        ytdlp_path = self.ytdlp_entry.get().strip()
        download_dir = self.dest_entry.get().strip()

        # Validaciones de rutas
        if not os.path.exists(ytdlp_path):
            messagebox.showerror("Error de Ruta", "No se encontró el ejecutable yt-dlp.exe.")
            return

        if not os.path.exists(download_dir):
            try:
                os.makedirs(download_dir, exist_ok=True)
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo crear el directorio de destino:\n{e}")
                return

        # Guardar en config
        self.config["download_dir"] = download_dir
        self.config["ytdlp_path"] = ytdlp_path
        self.save_config()

        # Obtener calidad seleccionada
        quality = self.quality_combo.get()
        format_args = []
        
        ffmpeg_ok = self.is_ffmpeg_available()
        log_debug(f"start_download: Calidad seleccionada='{quality}' | FFmpeg disponible={ffmpeg_ok}")
        
        if not ffmpeg_ok:
            if "MP3" in quality:
                messagebox.showerror(
                    "Falta FFmpeg", 
                    "No se puede descargar en MP3 porque FFmpeg no está instalado.\n\n"
                    "Por favor, selecciona 'Solo Audio (M4A)' (que no requiere conversión) o instala FFmpeg."
                )
                return
            elif "M4A" in quality:
                format_args = ["-x", "--audio-format", "m4a"]
            else:
                # Avisar al usuario de que se descargará en calidad pre-fusionada (usualmente 720p)
                # para evitar que se bajen dos archivos separados.
                confirm = messagebox.askyesno(
                    "Falta FFmpeg",
                    "No se detectó FFmpeg en tu sistema.\n\n"
                    "Sin FFmpeg, las resoluciones altas (1080p+) se descargarán como archivos de video y audio separados.\n\n"
                    "¿Deseas descargar la mejor calidad pre-fusionada disponible (usualmente 720p en un solo archivo con audio)?"
                )
                if not confirm:
                    return
                
                # Usar formatos pre-fusionados
                if "1080p" in quality:
                    format_args = ["-f", "b[height<=1080]"]
                elif "720p" in quality:
                    format_args = ["-f", "b[height<=720]"]
                elif "480p" in quality:
                    format_args = ["-f", "b[height<=480]"]
                else:
                    format_args = ["-f", "b"]
        else:
            # FFmpeg disponible, usar la mejor calidad combinando pistas
            if "1080p" in quality:
                format_args = ["-f", "bv*[height<=1080]+ba/b[height<=1080]"]
            elif "720p" in quality:
                format_args = ["-f", "bv*[height<=720]+ba/b[height<=720]"]
            elif "480p" in quality:
                format_args = ["-f", "bv*[height<=480]+ba/b[height<=480]"]
            elif "MP3" in quality:
                format_args = ["-x", "--audio-format", "mp3", "--audio-quality", "0"]
            elif "M4A" in quality:
                format_args = ["-x", "--audio-format", "m4a"]
            else:
                format_args = ["-f", "bv*+ba/b"]

        # Obtener título editado y limpiarlo de caracteres inválidos en Windows
        edited_title = self.vid_title_entry.get("1.0", tk.END).strip()
        safe_title = re.sub(r'[\\/*?:"<>|\n\r]', "", edited_title)
        safe_title = safe_title.replace("%", "%%") # Escapar % para que yt-dlp no lo trate como variable
        if not safe_title:
            safe_title = "Video_Descargado"

        # Preparar comando
        output_template = os.path.join(download_dir, f"{safe_title}.%(ext)s")
        cmd = [
            ytdlp_path,
            "--no-cache-dir",
            *format_args,
            "--no-playlist",
            "--newline",
            "-o", output_template,
            url
        ]

        # Configurar UI para descarga
        self.downloading = True
        self.download_btn.configure(state="disabled", text="DESCARGANDO...")
        self.fetch_btn.configure(state="disabled")
        self.status_lbl.configure(text="Estado: Iniciando descarga...")
        self.progress_bar.set(0.0)
        self.stats_lbl.configure(text="Progreso: 0% | Velocidad: -- | ETA: --")

        # Iniciar hilo de descarga
        threading.Thread(target=self._download_thread, args=(cmd,), daemon=True).start()

    def _download_thread(self, cmd):
        self.log_to_console(f"Iniciando proceso de descarga con comando:\n{' '.join(cmd)}")
        
        # Patrones regex para parsear salida de yt-dlp
        # Ej: [download]  12.5% of  10.00MiB at  3.50MiB/s ETA 00:02
        progress_re = re.compile(r'\[download\]\s+([0-9.]+)%\s+of\s+([^\s]+)\s+at\s+([^\s]+)\s+ETA\s+([^\s]+)')
        # Ej: [download] Destination: C:\Users\...
        destination_re = re.compile(r'\[download\] Destination: (.+)')
        # Ej: [Merger] Merging formats into "..."
        merger_re = re.compile(r'\[Merger\] Merging formats')
        ffmpeg_re = re.compile(r'\[(ExtractAudio|ffmpeg)\]')

        try:
            process = subprocess.Popen(
                cmd,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                encoding='utf-8',
                errors='replace',
                bufsize=1,
                creationflags=subprocess.CREATE_NO_WINDOW
            )

            current_status = "Descargando..."

            # Leer la salida en tiempo real
            while True:
                line = process.stdout.readline()
                if not line:
                    break
                
                line_str = line.strip()
                if not line_str:
                    continue

                # Escribir en la consola
                self.log_to_console(line_str)

                # Intentar parsear progreso de descarga
                progress_match = progress_re.search(line_str)
                if progress_match:
                    percent_val = float(progress_match.group(1))
                    total_size = progress_match.group(2)
                    speed = progress_match.group(3)
                    eta = progress_match.group(4)
                    
                    # Programar actualización en el hilo principal
                    self.after(0, lambda p=percent_val, s=speed, e=eta, sz=total_size: self.update_progress(p, s, e, sz))
                    continue

                # Detectar fases de fusión o conversión
                if merger_re.search(line_str):
                    current_status = "Fusionando audio y video..."
                    self.after(0, lambda st=current_status: self.status_lbl.configure(text=f"Estado: {st}"))
                elif ffmpeg_re.search(line_str):
                    current_status = "Procesando audio con FFmpeg..."
                    self.after(0, lambda st=current_status: self.status_lbl.configure(text=f"Estado: {st}"))
                elif "Destination:" in line_str:
                    dest_match = destination_re.search(line_str)
                    if dest_match:
                        file_name = os.path.basename(dest_match.group(1))
                        self.after(0, lambda fn=file_name: self.status_lbl.configure(text=f"Estado: Descargando '{fn}'"))

            process.wait()
            self.after(0, lambda code=process.returncode: self.on_download_finished(code))

        except Exception as e:
            self.log_to_console(f"Excepción en el hilo de descarga: {e}")
            self.after(0, lambda: self.on_download_finished(-1, str(e)))

    def update_progress(self, percent, speed, eta, total_size):
        # tkinter progress bar espera valor de 0.0 a 1.0
        self.progress_bar.set(percent / 100.0)
        self.stats_lbl.configure(text=f"Progreso: {percent}% de {total_size} | Velocidad: {speed} | ETA: {eta}")

    def on_download_finished(self, returncode, err_msg=None):
        self.downloading = False
        self.download_btn.configure(state="normal", text="DESCARGAR VIDEO")
        self.fetch_btn.configure(state="normal")
        
        if returncode == 0:
            self.progress_bar.set(1.0)
            self.status_lbl.configure(text="Estado: Descarga completada con éxito.")
            self.stats_lbl.configure(text="Progreso: 100% | Descarga finalizada.")
            messagebox.showinfo("Completado", "¡La descarga se ha completado con éxito!")
        else:
            self.status_lbl.configure(text="Estado: Error en la descarga.")
            if err_msg:
                messagebox.showerror("Error", f"Error durante la descarga:\n{err_msg}\n\nRevisa la consola para más detalles.")
            else:
                # Comprobar si hay error común de ffmpeg (si es formato mp3/audio)
                console_content = self.console_text.get("1.0", tk.END)
                if "ffmpeg" in console_content.lower() and ("not found" in console_content.lower() or "no such file" in console_content.lower()):
                    messagebox.showerror(
                        "Falta FFmpeg", 
                        "Error: FFmpeg no está instalado o no se encuentra en el PATH.\n\n"
                        "Para descargar en MP3 se requiere FFmpeg. Por favor:\n"
                        "1. Instala FFmpeg en tu sistema, o\n"
                        "2. Descarga en formato 'Solo Audio (M4A)', el cual no requiere conversión externa."
                    )
                else:
                    messagebox.showerror("Error", "Ocurrió un error al descargar. Revisa el log de consola para más detalles.")

if __name__ == "__main__":
    app = YtDlpGUI()
    app.mainloop()
