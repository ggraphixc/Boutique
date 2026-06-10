# scratch/test_api_call.py
import os
import sys
from gradio_client import Client, handle_file

GRADIO_SPACE = "tencent/Hunyuan3D-2"
print(f"Connecting to {GRADIO_SPACE}...")
client = Client(GRADIO_SPACE)
print("Connected.")

img_path = "static/uploads/prod_2823570d2a8a9d0c.jpg"
print(f"Using image: {img_path}")

try:
    print("Calling predict...")
    # Let's try calling with keyword arguments as in pipeline_daemon.py
    result = client.predict(
        caption="A realistic piece of clothing on a plain background, studio lighting",
        image=handle_file(img_path),
        steps=50,
        guidance_scale=5.5,
        seed=1234,
        octree_resolution="256",
        check_box_rembg=True,
        api_name="/shape_generation",
    )
    print("Prediction succeeded with kwargs!")
    print(f"Result: {result}")
except Exception as e:
    print(f"Prediction failed with kwargs: {e}")
