import bpy
import bpy_extras.image_utils
import io
import os.path
import struct

def loadImage(path):
    print("Loading image:", path)
    image = bpy_extras.image_utils.load_image(path)
    if image is not None:
        return image
    image = bpy_extras.image_utils.load_image(os.path.splitext(path)[0] + ".dds")
    return image

def readString(f):
    s = f.read(1)
    while s[-1] != 0x0a:
        s+= f.read(1)
    return s[0:-1].decode()

def readMesh(f, flags):
    name = readString(f)
    print("Mesh:", name)
    id = readUInt32(f)
    print("ID:", id)
    if flags == 0x1d:
        f.seek(50, 1)
    elif flags == 0x1c:
        f.seek(46, 1)
    xx = struct.unpack("<6f", f.read(6 * 4))
    print("float array:", xx)
    texIds = struct.unpack("<10l", f.read(10 * 4))
    print("tex ids:", texIds)
    return name, id, texIds

def readUInt32(f):
    return struct.unpack("<L", f.read(4))[0]

def readUInt16(f):
    return struct.unpack("<H", f.read(2))[0]

vtxs = []
idxs = []
nmls = []
uvs = []

triTab = {}
meshnames = {}
textures = {}
materials = {}

def load(filename):
    print("Loading:", filename)
    
    dirname = os.path.dirname(filename)
    print("Dirname:", dirname)

    with open(filename, "rb") as f:
        magic = readUInt16(f)
        assert(magic == 0x1000)

        s = readString(f)
        print("Serializer:", s)
        
        flags = readUInt16(f)
        assert(flags == 0x1d or flags == 0x1c)

        f.seek(0x67)
        mdlCnt = readUInt32(f)
        print("# of models: ", mdlCnt)
        texCnt = readUInt32(f)
        print("# of textures: ", texCnt)
        for i in range(texCnt):
            name = readString(f)
            id = readUInt32(f)
            image = loadImage(os.path.join(dirname, name))
            if image is not None:
                t = bpy.data.textures.new(str(name), "IMAGE")
                t.image = image
                textures[id] = t
        print("Textures:")
        print(textures)
        
        for i in range(mdlCnt):
            name, id, texIds = readMesh(f, flags)
            meshnames[id] = name
            mat = materials[id] = bpy.data.materials.new(name)
            for j in (0, 4, 5, 8):
                if(texIds[j] == -1):
                    continue
                mtex = mat.texture_slots.add()
                mtex.texture = textures[texIds[j]]
                mtex.texture_coords = "UV"
                mtex.use_map_color_diffuse = False
                mtex.texture.use_alpha = False
                if j == 0:
                    mtex.use_map_color_diffuse = True
                    mtex.texture.use_alpha = True
                elif j == 4:
                    mtex.use_map_emit = True
                elif j == 5:
                    mtex.use_map_normal = True
                    mtex.texture.use_normal_map = True
                elif j == 8:
                    mtex.use_map_specular = True
            
        print("Meshes:")
        print(meshnames)
        
        x = readUInt16(f)
        assert(x == 1)
        
        vtxCnt = readUInt32(f)
        vtxSize = 10 - texIds.count(-1)
        print("vtxCnt", vtxCnt)
        print("Size of texture block (# of floats):", vtxSize)
        
        for i in range(vtxCnt):
            vtxs.append(struct.unpack("fff", f.read(3 * 4)))
            if vtxCnt > 0:
                f.seek(10 * 4, 1)
                uvs.append(struct.unpack("ff", f.read(2 * 4)))
                
                u = uvs[-1][0]
                v = uvs[-1][1]
                uvs[-1] = (u, -v)
        
        triTabCnt = readUInt32(f)
        print("# of triangle tables:", triTabCnt)

        tris = []

        for i in range(triTabCnt):
            triCnt, id = struct.unpack("<LL", f.read(8))
            print("triCnt, id", triCnt, id)
            for j in range(triCnt):
                tris.append(struct.unpack("<HHH", f.read(2 * 3)))
            triTab[id] = tris[:]
            tris.clear()

    for id in triTab:
        tris = triTab[id]
        meshname = meshnames[id];
        
        me = bpy.data.meshes.new(meshname)
        me.from_pydata(vtxs, [], tris)
        me.materials.append(materials[id])
        me.update()

        me.uv_textures.new()

        print("# of UVs:", len(uvs))
        print("# of uv_layers[0] entries:", len(me.uv_layers[0].data))

        for l in range(len(me.loops)):
            me.uv_layers[0].data[l].uv = uvs[me.loops[l].vertex_index]

        scene = bpy.context.scene
        obj = bpy.data.objects.new(str(meshname), me)
        scene.objects.link(obj)
        scene.objects.active = obj
        obj.select = True

filename = "C:\\MEDIA\\SHIPS\\GREEL_DESTROYER\\DESTROYER.MDL"
load(filename)