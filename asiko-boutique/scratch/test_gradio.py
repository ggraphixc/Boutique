# scratch/test_gradio.py
import os
import sys
from gradio_client import Client, handle_file

GRADIO_SPACE = "tencent/Hunyuan3D-2"
print(f"Connecting to {GRADIO_SPACE}...")
try:
    client = Client(GRADIO_SPACE)
    print("Successfully connected!")
    
    # Let's check available API endpoints/names
    print("Checking API list...")
    client.view_api()
except Exception as e:
    print(f"Failed: {e}")
