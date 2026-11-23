# TWID - Landing 3D interactiva

Landing con cubo 3D (three.js) que reacciona al mouse, al click y al scroll.

- `landing_3d.html` - landing principal (three.js desde CDN, scroll suave, paleta TWID)
- `landing_puffy.html` - variante con esfera de pinchos de goma
- `index.html` - version simple con el cubo en video (`cube_wave.webm/.mp4`)
- `build_wave.py`, `build_cube.py`, `render_turntable.py` - scripts de Blender 5.x para generar los renders

Para verla: `python -m http.server` en esta carpeta y abrir `landing_3d.html`.
