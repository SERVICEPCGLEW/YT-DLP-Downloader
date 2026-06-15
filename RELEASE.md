# 📦 Release Notes

## [v1.0.0] - Lanzamiento Inicial (Initial Release)
**Fecha:** Junio 2026

¡Bienvenidos al lanzamiento oficial de **YT-DLP GUI Downloader**! 🚀

Hemos trabajado arduamente para traer una interfaz amigable, moderna y completa al potente motor de `yt-dlp`. Esta versión 1.0.0 sienta las bases para una descarga de medios multimedia rápida, de máxima calidad y sin la fricción de la línea de comandos.

### ✨ Nuevas Características
*   **Interfaz Gráfica (GUI) Premium:** Construida completamente en Python con `CustomTkinter` implementando un modo oscuro elegante y responsivo.
*   **Obtención Rápida de Metadatos:** Analiza enlaces de YouTube y otras plataformas para extraer el título (con opción de edición ampliada), duración, miniatura y nombre del canal en segundos.
*   **Selector de Calidad Inteligente:** Posibilidad de descargar:
    *   Mejor Calidad Disponible (fusiona Video + Audio usando FFmpeg).
    *   1080p, 720p, 480p.
    *   Extraer directamente en audio MP3 de Alta Calidad o M4A.
*   **Barra de Progreso y Estadísticas:** Panel inferior para seguir en tiempo real el progreso de la descarga, velocidad, y tiempo estimado (ETA).
*   **Consola de Depuración:** Integración de un log desplegable para solucionar problemas y ver directamente la salida nativa de `yt-dlp` y `FFmpeg`.
*   **Social & Soporte:** Enlaces rápidos para visitar las redes de ServicePCGlew y apoyar el desarrollo vía Matecito directamente desde la App.

### 🛠️ Correcciones y Mejoras Técnicas (Under the Hood)
*   Compilación a un único archivo `.exe` para su fácil distribución (Standalone Portable App).
*   Sanitización automática de títulos para prevenir errores de caracteres prohibidos (`\ / * ? : " < > |`) en sistemas Windows.
*   Detección inteligente de la disponibilidad de `FFmpeg` en el sistema para evitar fallos durante la extracción de audio o fusión en 1080p.

<!-- REEMPLAZA LA SIGUIENTE LÍNEA CON LA RUTA A TU IMAGEN DE CAPTURA DE PANTALLA DE LA NUEVA VERSIÓN -->
> **[🖼️ INSERTA AQUÍ CAPTURA DEL FUNCIONAMIENTO]**
> `![Nueva versión v1.0.0](ruta/a/tu/imagen.png)`

---
*Gracias por descargar y apoyar el proyecto. ¡Disfrútalo!* 💖
