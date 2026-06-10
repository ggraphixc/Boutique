# scratch/test_reduced_export.py
from gradio_client import Client, handle_file
import os, glob, struct, json

GRADIO_SPACE = "tencent/Hunyuan3D-2"
print(f"Connecting to {GRADIO_SPACE}...")
client = Client(GRADIO_SPACE)
print("Connected.")

# Find the latest white_mesh.glb
temp_dir = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Temp", "gradio")
glb_files = glob.glob(os.path.join(temp_dir, "**", "white_mesh.glb"), recursive=True)
glb_files.sort(key=os.path.getmtime)
latest_glb = glb_files[-1]
print(f"Using: {latest_glb}")

# Try with reduce_face=True and a much lower target face count
try:
    print("Calling /on_export_click with reduce_face=True, target_face_num=10000...")
    res = client.predict(
        file_out=handle_file(latest_glb),
        file_out2=handle_file(latest_glb),
        file_type="glb",
        reduce_face=True,
        export_texture=False,
        target_face_num=10000,
        api_name="/on_export_click",
    )
    print("Export succeeded!")
    # Extract the GLB path from the result
    html_out, download_info = res
    glb_path = download_info.get("value", "")
    if glb_path and os.path.exists(glb_path):
        file_size = os.path.getsize(glb_path)
        print(f"Exported GLB: {glb_path} ({file_size:,} bytes / {file_size/1024:.0f} KB)")
        
        # Quick inspect
        with open(glb_path, "rb") as f:
            header = f.read(12)
            magic, version, length = struct.unpack("<4sII", header)
            chunk_header = f.read(8)
            chunk_length, chunk_type = struct.unpack("<II", chunk_header)
            json_bytes = f.read(chunk_length)
            gltf = json.loads(json_bytes.decode("utf-8", errors="ignore"))
            
            for i, mesh in enumerate(gltf.get("meshes", [])):
                for p in mesh.get("primitives", []):
                    print(f"  Attributes: {list(p.get('attributes', {}).keys())}, material={p.get('material')}")
            print(f"  Materials: {len(gltf.get('materials', []))}")
            print(f"  Textures: {len(gltf.get('textures', []))}")
            for i, acc in enumerate(gltf.get("accessors", [])):
                print(f"  Accessor {i}: type={acc.get('type')}, count={acc.get('count')}")
    else:
        print(f"GLB path: {glb_path} (not found?)")
except Exception as e:
    print(f"Export failed: {e}")
