# scratch/inspect_textured_glb.py
import struct
import json
import os
import glob

# Find the textured_mesh.glb from the export call
temp_dir = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Temp", "gradio")
glb_files = glob.glob(os.path.join(temp_dir, "**", "textured_mesh.glb"), recursive=True)

if not glb_files:
    print("No textured_mesh.glb found!")
    exit(1)

glb_files.sort(key=os.path.getmtime)
glb_path = glb_files[-1]
file_size = os.path.getsize(glb_path)
print(f"Reading {glb_path} ({file_size:,} bytes / {file_size/1024/1024:.1f} MB)...")

with open(glb_path, "rb") as f:
    header = f.read(12)
    magic, version, length = struct.unpack("<4sII", header)
    print(f"Version: {version}, Length: {length}")
    
    chunk_header = f.read(8)
    chunk_length, chunk_type = struct.unpack("<II", chunk_header)
    
    json_bytes = f.read(chunk_length)
    gltf = json.loads(json_bytes.decode("utf-8", errors="ignore"))
    
    print(f"\nMeshes ({len(gltf.get('meshes', []))}):")
    for i, mesh in enumerate(gltf.get("meshes", [])):
        print(f"  Mesh {i}: {mesh.get('name')}")
        for p in mesh.get("primitives", []):
            print(f"    Primitive: mode={p.get('mode', 4)}, attributes={list(p.get('attributes', {}).keys())}, material={p.get('material')}")
            
    print(f"\nMaterials ({len(gltf.get('materials', []))}):")
    for i, mat in enumerate(gltf.get("materials", [])):
        pbr = mat.get('pbrMetallicRoughness', {})
        tex_info = pbr.get('baseColorTexture')
        print(f"  Material {i}: {mat.get('name')}, baseColorTexture={tex_info}, roughness={pbr.get('roughnessFactor')}, metallic={pbr.get('metallicFactor')}")
        
    print(f"\nTextures ({len(gltf.get('textures', []))}):")
    for i, tex in enumerate(gltf.get("textures", [])):
        print(f"  Texture {i}: source={tex.get('source')}, sampler={tex.get('sampler')}")
        
    print(f"\nImages ({len(gltf.get('images', []))}):")
    for i, img in enumerate(gltf.get("images", [])):
        print(f"  Image {i}: mimeType={img.get('mimeType')}, name={img.get('name')}, bufferView={img.get('bufferView')}")

    print(f"\nAccessors ({len(gltf.get('accessors', []))}):")
    for i, acc in enumerate(gltf.get("accessors", [])):
        print(f"  Accessor {i}: type={acc.get('type')}, componentType={acc.get('componentType')}, count={acc.get('count')}")
