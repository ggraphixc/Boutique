# scratch/test_generation_all.py
from gradio_client import Client, handle_file
import os, struct, json

GRADIO_SPACE = "tencent/Hunyuan3D-2"
print(f"Connecting to {GRADIO_SPACE}...")
client = Client(GRADIO_SPACE)
print("Connected.")

img_path = "static/uploads/prod_2823570d2a8a9d0c.jpg"
print(f"Using image: {img_path}")

try:
    print("Calling /generation_all (shape + texture in one call)...")
    result = client.predict(
        caption="A realistic piece of clothing on a plain background, studio lighting",
        image=handle_file(img_path),
        steps=30,
        guidance_scale=5.0,
        seed=1234,
        octree_resolution=256,
        check_box_rembg=True,
        num_chunks=8000,
        randomize_seed=False,
        api_name="/generation_all",
    )
    print("generation_all succeeded!")
    print(f"Result type: {type(result)}")
    print(f"Result length: {len(result) if isinstance(result, (list, tuple)) else 'N/A'}")
    
    # /generation_all returns: (file, file, output, mesh_stats, seed)
    # First file = untextured, second file = textured
    for i, item in enumerate(result):
        if isinstance(item, dict) and 'value' in item:
            path = item['value']
            if os.path.exists(path):
                size = os.path.getsize(path)
                print(f"  Result[{i}]: {path} ({size:,} bytes / {size/1024:.0f} KB)")
            else:
                print(f"  Result[{i}]: {path} (not found)")
        elif isinstance(item, str) and os.path.exists(item):
            size = os.path.getsize(item)
            print(f"  Result[{i}]: {item} ({size:,} bytes / {size/1024:.0f} KB)")
        elif isinstance(item, dict):
            keys = list(item.keys())[:5]
            print(f"  Result[{i}]: dict with keys {keys}")
        else:
            val = str(item)[:200]
            print(f"  Result[{i}]: {val}")

except Exception as e:
    print(f"generation_all FAILED: {e}")
    import traceback
    traceback.print_exc()
