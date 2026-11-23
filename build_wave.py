"""Cubo de voxels con ondas + slime (sin giro), render de secuencia PNG con alpha.
Uso: blender -b -P build_wave.py -- [frames] [res] [samples] [primer] [ultimo] [carpeta]
"""
import bpy, bmesh, math, os, sys
import numpy as np
from mathutils import Vector

args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
FRAMES  = int(args[0]) if len(args) > 0 else 120
RES     = int(args[1]) if len(args) > 1 else 900
SAMPLES = int(args[2]) if len(args) > 2 else 32
FIRST   = int(args[3]) if len(args) > 3 else 1
LAST    = int(args[4]) if len(args) > 4 else FRAMES
FOLDER  = args[5] if len(args) > 5 else "frames_wave"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), FOLDER)
os.makedirs(OUT, exist_ok=True)

rng = np.random.default_rng(11)
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene

# ---------------- voxels ----------------
N, SHELL, STEP = 12, 3, 0.2
half = (N - 1) / 2
cent, depth_l = [], []
for i in range(N):
    for j in range(N):
        for k in range(N):
            d = min(i, j, k, N - 1 - i, N - 1 - j, N - 1 - k)
            if d < SHELL:
                cent.append(((i - half) * STEP, (j - half) * STEP, (k - half) * STEP))
                depth_l.append(d)
C = np.array(cent)
depth = np.array(depth_l)
M0 = len(C)
ext = N * STEP / 2
U = C / ext                                     # -1..1
outer = 1.0 - depth / SHELL                      # 1 = capa exterior
axis = np.argmax(np.abs(U), axis=1)
sign = np.sign(U[np.arange(M0), axis])
normal = np.zeros_like(C); normal[np.arange(M0), axis] = sign

corner = np.array([1.0, 1.0, 1.0]) / math.sqrt(3)   # zona que mas se deshace (arriba/derecha/atras)
cw = np.clip(0.5 + 0.5 * (U @ corner) * 1.3, 0, 1)
rnd_c = rng.random(M0)

# particulas sueltas (cubitos flotando)
P = 90
dirs = rng.normal(size=(P, 3)); dirs /= np.linalg.norm(dirs, axis=1)[:, None]
dirs = dirs * 0.6 + corner * 0.5
dirs /= np.linalg.norm(dirs, axis=1)[:, None]
pc = dirs * rng.uniform(1.05, 1.7, size=(P, 1)) * ext
psz = rng.uniform(0.04, 0.15, size=P)
pph = rng.uniform(0, 2 * math.pi, size=P)
prnd = rng.random(P)

M = M0 + P
UNIT = np.array([[-1,-1,-1],[1,-1,-1],[1,1,-1],[-1,1,-1],[-1,-1,1],[1,-1,1],[1,1,1],[-1,1,1]], float) * 0.5
FACES = [(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]

faces = []
for m in range(M):
    b = m * 8
    for f in FACES:
        faces.append([b + v for v in f])
mesh = bpy.data.meshes.new("Voxels")
mesh.from_pydata([(0.0, 0.0, 0.0)] * (M * 8), [], faces)
mesh.update()

rv = np.concatenate([rnd_c, prnd])
attr = mesh.attributes.new("rnd", 'FLOAT', 'FACE')
attr.data.foreach_set("value", np.repeat(rv, 6).astype(np.float32))

def smooth(x):
    x = np.clip(x, 0, 1)
    return x * x * (3 - 2 * x)

def update(frame):
    ph = 2 * math.pi * ((frame - 1) % FRAMES) / FRAMES
    u = U
    # ondas que viajan (periodos enteros -> loop perfecto)
    w1 = np.sin(2 * math.pi * (u @ np.array([0.8, 0.25, 0.55])) * 0.9 - ph)
    w2 = np.sin(2 * math.pi * (u @ np.array([-0.3, 0.9, 0.4])) * 0.7 + 2 * ph + 1.3)
    # slime: lobulos suaves que se mueven y se funden
    w3 = (np.sin(2.9 * u[:, 0] + 1.1 + ph) * np.sin(2.4 * u[:, 1] - ph + 0.7) * np.sin(2.1 * u[:, 2] + 2 * ph))
    mix = np.clip(0.50 * w1 + 0.30 * w2 + 0.55 * w3, -1, 1)
    m = 0.5 + 0.5 * mix                               # 0..1
    amp = 0.18 + 0.75 * outer * (0.35 + 0.65 * cw)    # cuanto se encoge segun zona
    sf = 1.0 - amp * smooth(1.0 - m)
    sz = STEP * 0.95 * np.clip(sf, 0.12, 1.0)
    push = normal * (STEP * 2.2 * outer * (0.15 + cw) * smooth(1.0 - m))[:, None]
    # jelly: deformacion suave de todo el cuerpo
    jel = 0.07 * np.stack([
        np.sin(2.2 * u[:, 1] + ph),
        np.sin(2.0 * u[:, 2] - ph + 1.0),
        np.sin(2.4 * u[:, 0] + 2 * ph + 2.0)], axis=1)
    pos = C + push + jel

    # particulas: respiran y derivan un poco, siempre en loop
    pm = 0.5 + 0.5 * np.sin(ph + pph)
    ps = psz * (0.2 + 0.8 * pm)
    drift = dirs * (0.12 * np.sin(ph * 1 + pph))[:, None] * ext * 0.5
    ppos = pc + drift

    allpos = np.concatenate([pos, ppos])
    allsz = np.concatenate([sz, ps])
    verts = allpos[:, None, :] + UNIT[None, :, :] * allsz[:, None, None]
    mesh.vertices.foreach_set("co", verts.astype(np.float32).ravel())
    mesh.update()

update(1)

obj = bpy.data.objects.new("Voxels", mesh)
scene.collection.objects.link(obj)
obj.rotation_euler = (math.radians(22), math.radians(-14), math.radians(26))   # fijo, sin giro
bev = obj.modifiers.new("Bevel", 'BEVEL')
bev.width = 0.005; bev.segments = 2; bev.limit_method = 'ANGLE'

# ---------------- material ----------------
mat = bpy.data.materials.new("Violet"); mat.use_nodes = True
nt = mat.node_tree; nt.nodes.clear()
out = nt.nodes.new("ShaderNodeOutputMaterial")
bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
at = nt.nodes.new("ShaderNodeAttribute"); at.attribute_name = "rnd"
ramp = nt.nodes.new("ShaderNodeValToRGB")
e = ramp.color_ramp.elements
e[0].position = 0.0; e[0].color = (0.07, 0.02, 0.62, 1)
e[1].position = 1.0; e[1].color = (0.46, 0.34, 0.97, 1)
mid = e.new(0.5); mid.color = (0.20, 0.09, 0.85, 1)
nt.links.new(at.outputs["Fac"], ramp.inputs["Fac"])
nt.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
bsdf.inputs["Roughness"].default_value = 0.30
for n, v in (("Specular IOR Level", 0.6), ("Coat Weight", 0.3), ("Coat Roughness", 0.15)):
    if n in bsdf.inputs: bsdf.inputs[n].default_value = v
nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
obj.data.materials.append(mat)

# ---------------- suelo (solo sombra) ----------------
bpy.ops.mesh.primitive_plane_add(size=40, location=(0, 0, -2.45))
floor = bpy.context.object
floor.is_shadow_catcher = True

# ---------------- luces ----------------
def area(name, loc, energy, color, size):
    d = bpy.data.lights.new(name, 'AREA'); d.energy = energy; d.color = color; d.size = size
    o = bpy.data.objects.new(name, d); scene.collection.objects.link(o)
    o.location = loc
    o.rotation_euler = (Vector((0, 0, 0)) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
area("Key",  (-3.0, -2.5, 5.0), 750, (1.0, 0.96, 1.0), 3.5)
area("Rim",  (4.0, 2.0, 1.5),   450, (0.45, 0.55, 1.0), 3.0)
area("Fill", (2.5, -4.0, -0.5), 160, (0.75, 0.65, 1.0), 4.0)
w = bpy.data.worlds.new("W"); scene.world = w; w.use_nodes = True
w.node_tree.nodes["Background"].inputs["Color"].default_value = (0.5, 0.4, 0.95, 1)
w.node_tree.nodes["Background"].inputs["Strength"].default_value = 1.3

# ---------------- camara ----------------
cd = bpy.data.cameras.new("Cam"); cd.lens = 62
cam = bpy.data.objects.new("Cam", cd); scene.collection.objects.link(cam)
cam.location = (0, -8.4, 0.5)
cam.rotation_euler = (math.radians(87), 0, 0)
scene.camera = cam

# ---------------- render ----------------
scene.render.engine = 'CYCLES'
scene.cycles.device = 'CPU'
scene.cycles.samples = SAMPLES
scene.cycles.use_denoising = True
scene.render.film_transparent = True
scene.render.resolution_x = RES
scene.render.resolution_y = RES
scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_mode = 'RGBA'

for f in range(FIRST, LAST + 1):
    path = os.path.join(OUT, f"f_{f:04d}.png")
    if os.path.exists(path):
        continue
    update(f)
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(os.path.dirname(os.path.abspath(__file__)), "cube_wave.blend"))
print("FRAMES LISTOS", FIRST, LAST)
