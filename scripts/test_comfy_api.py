import os
import json
import httpx
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("COMFYUI_API_KEY")
URL = "https://cloud.comfy.org/api/prompt"

# Un workflow ultra-básico de Text-To-Image para probar la conexión
workflow = {
  "3": {
    "class_type": "KSampler",
    "inputs": {
      "seed": 12345,
      "steps": 20,
      "cfg": 8,
      "sampler_name": "euler",
      "scheduler": "normal",
      "denoise": 1,
      "model": [ "4", 0 ],
      "positive": [ "6", 0 ],
      "negative": [ "7", 0 ],
      "latent_image": [ "5", 0 ]
    }
  },
  "4": {
    "class_type": "CheckpointLoaderSimple",
    "inputs": {
      "ckpt_name": "v1-5-pruned-emaonly.ckpt"
    }
  },
  "5": {
    "class_type": "EmptyLatentImage",
    "inputs": {
      "batch_size": 1,
      "height": 512,
      "width": 512
    }
  },
  "6": {
    "class_type": "CLIPTextEncode",
    "inputs": {
      "text": "masterpiece, best quality, cinematic lighting, a samurai walking in edo at dawn",
      "clip": [ "4", 1 ]
    }
  },
  "7": {
    "class_type": "CLIPTextEncode",
    "inputs": {
      "text": "bad hands, text, watermark",
      "clip": [ "4", 1 ]
    }
  },
  "8": {
    "class_type": "VAEDecode",
    "inputs": {
      "samples": [ "3", 0 ],
      "vae": [ "4", 2 ]
    }
  },
  "9": {
    "class_type": "SaveImage",
    "inputs": {
      "filename_prefix": "ComfyUI_Test",
      "images": [ "8", 0 ]
    }
  }
}

headers = {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json"
}

print("Enviando petición a ComfyUI Cloud API...")
try:
    response = httpx.post(URL, headers=headers, json={"prompt": workflow})
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"Error: {e}")
