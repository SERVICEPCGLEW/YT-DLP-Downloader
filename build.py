import subprocess
import sys
import os
import shutil

def main():
    print("Iniciando compilación con PyInstaller...")
    
    # Asegurarnos de que estamos en el directorio correcto
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)

    # Comando de compilación
    # --noconsole: Evita abrir una ventana negra de comando detrás de la app GUI
    # --onefile: Empaqueta todo en un único .exe
    # --collect-all customtkinter: Copia todos los archivos de tema y assets de customtkinter
    cmd = [
        "pyinstaller",
        "--noconsole",
        "--onefile",
        "--clean",
        "--noconfirm",
        "--collect-all", "customtkinter", "--hidden-import", "pystray", "--hidden-import", "PIL",
        "--name=Yt-Dlp-GUI",
        "--icon=yt-dlp.exe",
        "app.py"
    ]

    print(f"Ejecutando: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, check=True)
        print("\n¡Compilación finalizada con éxito!")
        print("El archivo ejecutable (.exe) se encuentra en la carpeta 'dist/'")
        
        exe_path = os.path.join(script_dir, "dist", "YtDlpGUI.exe")
        if os.path.exists(exe_path):
            safe_path = exe_path.encode(sys.stdout.encoding or 'utf-8', errors='replace').decode(sys.stdout.encoding or 'utf-8')
            print(f"Ruta del ejecutable: {safe_path}")
            print(f"Tamaño: {os.path.getsize(exe_path) / (1024 * 1024):.2f} MB")
        
    except subprocess.CalledProcessError as e:
        print(f"\nError durante la compilación: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
