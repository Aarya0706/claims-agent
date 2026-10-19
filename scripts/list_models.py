#!/usr/bin/env python
"""Lists Gemini models your free key can call with tool support. Pick a 'flash'/'flash-lite' one for GEMINI_MODEL.
Free-tier limits are per model: check https://aistudio.google.com/rate-limit"""
import os, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dotenv import load_dotenv
load_dotenv()
from google import genai
c = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
for m in c.models.list():
    if "generateContent" in (m.supported_actions or []):
        print(m.name.removeprefix("models/"))
