# scratch/test_export_call.py
from gradio_client import Client, handle_file
import os

GRADIO_SPACE = "tencent/Hunyuan3D-2"
print(f"Connecting to {GRADIO_SPACE}...")
client = Client(GRADIO_SPACE)
print("Connected.")

# Replace with the path to the white_mesh.glb generated in our previous run
# Let's search Temp directory for recent white_mesh.glb files first!
import glob
temp_dir = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Temp", "gradio")
glb_files = glob.glob(os.path.join(temp_dir, "**", "white_mesh.glb"), recursive=True)

if not glb_files:
    print("No white_mesh.glb found in Temp/gradio!")
    sys.exit(1)

# Get the most recent one
glb_files.sort(key=os.path.getmtime)
latest_glb = glb_files[-1]
print(f"Using latest glb: {latest_glb}")

try:
    print("Calling /on_export_click...")
    # Parameters for `/on_export_click`:
    # predict(file_out, file_out2, file_type, reduce_face, export_texture, target_face_num, api_name="/on_export_click")
    res = client.predict(
        file_out=handle_file(latest_glb),
        file_out2=handle_file(latest_glb), # passing same file as dummy for file_out2
        file_type="glb",
        reduce_face=False,
        export_texture=True,
        target_face_num=10000,
        api_name="/on_export_click",
    )
    print("Export succeeded!")
    print(res)
except Exception as e:
    print(f"Export failed: {e}")
