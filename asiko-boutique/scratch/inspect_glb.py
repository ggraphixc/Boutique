# scratch/inspect_glb.py
import struct
import json

glb_path = "static/uploads/optimized/mesh_prod_f4bcceab-177e-46d9-8787-b8157d2b241b.glb"
print(f"Reading {glb_path}...")

with open(glb_path, "rb") as f:
    header = f.read(12)
    if len(header) < 12:
        print("Header too short!")
        sys.exit(1)
    magic, version, length = struct.unpack("<4sII", header)
    if magic != b"glTF":
        print(f"Invalid magic: {magic}")
        sys.exit(1)
    print(f"Version: {version}, Length: {length}")
    
    # Read first chunk (JSON)
    chunk_header = f.read(8)
    if len(chunk_header) < 8:
        print("Chunk header too short!")
        sys.exit(1)
    chunk_length, chunk_type = struct.unpack("<II", chunk_header)
    print(f"Chunk type: {chunk_type:08X} ({struct.pack('<I', chunk_type)}), Length: {chunk_length}")
    
    json_bytes = f.read(chunk_length)
    json_str = json_bytes.decode("utf-8", errors="ignore")
    gltf = json.loads(json_str)
    
    # Let's print summary info
    print("Meshes:")
    for i, mesh in enumerate(gltf.get("meshes", [])):
        print(f"  Mesh {i}: {mesh.get('name')}")
        for p in mesh.get("primitives", []):
            print(f"    Primitive: mode={p.get('mode', 4)}, attributes={list(p.get('attributes', {}).keys())}, material={p.get('material')}")
            
    print("Materials:")
    for i, mat in enumerate(gltf.get("materials", [])):
        print(f"  Material {i}: {mat.get('name')}, pbr={mat.get('pbrMetallicRoughness')}")
        
    print("Nodes:")
    for i, node in enumerate(gltf.get("nodes", [])):
        print(f"  Node {i}: {node.get('name')}, mesh={node.get('mesh')}, translation={node.get('translation')}, scale={node.get('scale')}")
