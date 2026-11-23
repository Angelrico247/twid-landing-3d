"""Turntable en loop del cubo. Uso:
blender -b cube_hero.blend -P render_turntable.py -- [frames] [resolucion] [samples] [primer] [ultimo]
"""
import bpy, os, sys, math

args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
FRAMES = int(args[0]) if len(args) > 0 else 120
RES = int(args[1]) if len(args) > 1 else 900
SAMPLES = int(args[2]) if len(args) > 2 else 32
FIRST = int(args[3]) if len(args) > 3 else 1
LAST = int(args[4]) if len(args) > 4 else FRAMES

OUT = os.path.join(os.path.dirname(bpy.data.filepath), "frames")
os.makedirs(OUT, exist_ok=True)

scene = bpy.context.scene
obj = bpy.data.objects["VoxelCube"]
z0 = obj.rotation_euler[2]

# rotacion 360 grados sobre el eje Z global, lineal, sin duplicar el ultimo frame (loop perfecto)
scene.frame_start, scene.frame_end = 1, FRAMES

scene.cycles.samples = SAMPLES
scene.render.resolution_x = RES
scene.render.resolution_y = RES
scene.render.resolution_percentage = 100
scene.render.film_transparent = True
scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_mode = 'RGBA'

for f in range(FIRST, LAST + 1):
    path = os.path.join(OUT, f"f_{f:04d}.png")
    if os.path.exists(path):
        continue
    obj.rotation_euler[2] = z0 + math.radians(360) * (f - 1) / FRAMES
    scene.frame_set(f)
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
print("FRAMES LISTOS", FIRST, LAST)
