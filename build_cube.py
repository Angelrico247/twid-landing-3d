"""Voxel cube hero (estilo REF.AI) -> .blend, .glb y render PNG transparente.
Uso: blender -b -P build_cube.py
"""
import bpy, bmesh, random, math, os
from mathutils import Vector

OUT = os.path.dirname(os.path.abspath(__file__))
random.seed(7)

# ---------- escena limpia ----------
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene

# ---------- geometria: cubo de cubitos con borde "disuelto" ----------
N = 10            # cubitos por lado
SHELL = 2         # capas exteriores que se generan
STEP = 0.2        # separacion entre centros
SIZE = STEP * 0.94

bm = bmesh.new()
rnd_vals = []
half = (N - 1) / 2

def add_cube(center, size, rnd):
    start = len(bm.faces)
    res = bmesh.ops.create_cube(bm, size=size)
    bmesh.ops.translate(bm, vec=center, verts=res["verts"])
    return rnd

cube_faces = []   # (face_start, face_end, rnd)
for i in range(N):
    for j in range(N):
        for k in range(N):
            depth = min(i, j, k, N - 1 - i, N - 1 - j, N - 1 - k)
            if depth >= SHELL:
                continue
            pos = Vector((i - half, j - half, k - half)) * STEP
            # direccion hacia la esquina que se "deshace"
            corner = Vector((1, -1, 1)).normalized()
            t = (pos.normalized().dot(corner) + 1) / 2 if pos.length else 0.5
            # probabilidad de quitar / encoger crece en la zona exterior y hacia la esquina
            outer = 1 - depth / SHELL
            p_remove = 0.05 + 0.45 * t * outer + 0.12 * (1 - outer)
            if random.random() < p_remove:
                continue
            s = SIZE * (random.uniform(0.35, 1.0) if random.random() < 0.55 * (0.3 + t) else 1.0)
            push = Vector((0, 0, 0))
            if random.random() < 0.35 * (0.3 + t):
                axis = max(range(3), key=lambda a: abs(pos[a]))
                push[axis] = math.copysign(random.uniform(0.02, 0.22), pos[axis])
            f0 = len(bm.faces)
            res = bmesh.ops.create_cube(bm, size=s)
            bmesh.ops.translate(bm, vec=pos + push, verts=res["verts"])
            cube_faces.append((f0, len(bm.faces), random.random()))

# cubitos sueltos flotando alrededor
for _ in range(70):
    d = Vector((random.uniform(-1, 1), random.uniform(-1, 1), random.uniform(-1, 1)))
    if d.length < 0.2:
        continue
    pos = d.normalized() * random.uniform(1.15, 1.55) * (N * STEP / 2)
    f0 = len(bm.faces)
    res = bmesh.ops.create_cube(bm, size=random.uniform(0.05, 0.16))
    bmesh.ops.translate(bm, vec=pos, verts=res["verts"])
    cube_faces.append((f0, len(bm.faces), random.random()))

bm.faces.ensure_lookup_table()
mesh = bpy.data.meshes.new("VoxelCube")
bm.to_mesh(mesh)
attr = mesh.attributes.new("rnd", 'FLOAT', 'FACE')
vals = [0.0] * len(mesh.polygons)
for a, b, r in cube_faces:
    for fi in range(a, b):
        vals[fi] = r
attr.data.foreach_set("value", vals)
bm.free()

obj = bpy.data.objects.new("VoxelCube", mesh)
scene.collection.objects.link(obj)
obj.rotation_euler = (math.radians(24), math.radians(-18), math.radians(32))
for p in mesh.polygons:
    p.use_smooth = False

# bevel para atrapar luz en los bordes
bev = obj.modifiers.new("Bevel", 'BEVEL')
bev.width = 0.006
bev.segments = 2
bev.limit_method = 'ANGLE'

# ---------- material violeta/indigo con variacion por cubo ----------
mat = bpy.data.materials.new("Violet")
mat.use_nodes = True
nt = mat.node_tree
nt.nodes.clear()
out = nt.nodes.new("ShaderNodeOutputMaterial")
bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
at = nt.nodes.new("ShaderNodeAttribute"); at.attribute_name = "rnd"; at.attribute_type = 'GEOMETRY'
ramp = nt.nodes.new("ShaderNodeValToRGB")
ramp.color_ramp.elements[0].position = 0.0
ramp.color_ramp.elements[0].color = (0.10, 0.04, 0.55, 1)   # indigo
ramp.color_ramp.elements[1].position = 1.0
ramp.color_ramp.elements[1].color = (0.52, 0.38, 0.98, 1)   # lavanda
mid = ramp.color_ramp.elements.new(0.55); mid.color = (0.28, 0.14, 0.85, 1)
nt.links.new(at.outputs["Fac"], ramp.inputs["Fac"])
nt.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
bsdf.inputs["Roughness"].default_value = 0.32
if "Specular IOR Level" in bsdf.inputs:
    bsdf.inputs["Specular IOR Level"].default_value = 0.6
if "Coat Weight" in bsdf.inputs:
    bsdf.inputs["Coat Weight"].default_value = 0.35
    bsdf.inputs["Coat Roughness"].default_value = 0.15
nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
obj.data.materials.append(mat)

# ---------- luces ----------
def area(name, loc, energy, color, size):
    d = bpy.data.lights.new(name, 'AREA'); d.energy = energy; d.color = color; d.size = size
    o = bpy.data.objects.new(name, d); scene.collection.objects.link(o)
    o.location = loc
    direction = Vector((0, 0, 0)) - Vector(loc)
    o.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()
    return o

area("Key",  (-3.2, -3.0, 4.2), 700, (1.0, 0.96, 1.0), 3.5)
area("Rim",  (3.8, 2.5, 1.5),   500, (0.45, 0.55, 1.0), 3.0)
area("Fill", (2.5, -4.0, -1.0), 180, (0.75, 0.65, 1.0), 4.0)

# mundo suave lavanda (solo iluminacion; el fondo se renderiza transparente)
w = bpy.data.worlds.new("W"); scene.world = w; w.use_nodes = True
w.node_tree.nodes["Background"].inputs["Color"].default_value = (0.55, 0.45, 0.95, 1)
w.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.55

# ---------- camara ----------
cam_d = bpy.data.cameras.new("Cam"); cam_d.lens = 70
cam = bpy.data.objects.new("Cam", cam_d); scene.collection.objects.link(cam)
cam.location = (0, -7.2, 0.6)
cam.rotation_euler = (math.radians(86), 0, 0)
scene.camera = cam

# ---------- render ----------
scene.render.engine = 'CYCLES'
scene.cycles.device = 'CPU'
scene.cycles.samples = 96
scene.cycles.use_denoising = True
scene.render.film_transparent = True
scene.render.resolution_x = 1600
scene.render.resolution_y = 1600
scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_mode = 'RGBA'
scene.render.filepath = os.path.join(OUT, "cube_hero.png")
bpy.ops.render.render(write_still=True)

# ---------- exportar ----------
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "cube_hero.blend"))
bpy.ops.object.select_all(action='DESELECT')
obj.select_set(True)
bpy.context.view_layer.objects.active = obj
try:
    bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, "cube_hero.glb"),
                              export_format='GLB', use_selection=True)
except Exception as e:
    print("GLB export fallo:", e)
print("LISTO", OUT)
