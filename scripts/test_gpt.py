"""Debug: Test video prompt generation with GPT-5.5"""
import os, json, io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from dotenv import load_dotenv
load_dotenv()
from openai import OpenAI

client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

# Mini test with a short script excerpt
test_script = """El aire de la madrugada entra frío por las rendijas de papel de los shōji. 
Huele a ceniza húmeda, a arroz lavado, a madera de ciprés que ha guardado la noche. 
Afuera, antes de que el sol toque los tejados de Edo, una campanilla suena en algún templo lejano."""

print("=== TEST 1: json_object format ===")
try:
    r = client.chat.completions.create(
        model='gpt-5.5',
        messages=[
            {"role": "system", "content": "You are a cinematography director. Convert narration into video scene prompts. Return a JSON object with a 'scenes' array."},
            {"role": "user", "content": f"Generate 3 video scene prompts (5 seconds each) for this narration. Return JSON with a 'scenes' array where each scene has 'scene_number', 'timestamp', and 'prompt' fields:\n\n{test_script}"}
        ],
        max_completion_tokens=2000,
        response_format={"type": "json_object"}
    )
    content = r.choices[0].message.content
    print(f"finish_reason: {r.choices[0].finish_reason}")
    print(f"content is None: {content is None}")
    print(f"content length: {len(content) if content else 0}")
    if content:
        print(f"content preview: {content[:500]}")
        parsed = json.loads(content)
        print(f"parsed keys: {list(parsed.keys())}")
        if 'scenes' in parsed:
            print(f"scenes count: {len(parsed['scenes'])}")
except Exception as e:
    print(f"ERROR: {e}")

print("\n=== TEST 2: no json_object format (plain) ===")
try:
    r2 = client.chat.completions.create(
        model='gpt-5.5',
        messages=[
            {"role": "system", "content": "You are a cinematography director. Convert narration into video scene prompts. Always respond with valid JSON only, no markdown."},
            {"role": "user", "content": f'Generate 3 video scene prompts (5 seconds each) for this narration. Respond ONLY with a JSON object like {{"scenes": [{{"scene_number": 1, "timestamp": "00:00-00:05", "prompt": "..."}}]}}:\n\n{test_script}'}
        ],
        max_completion_tokens=2000,
    )
    content2 = r2.choices[0].message.content
    print(f"finish_reason: {r2.choices[0].finish_reason}")
    print(f"content length: {len(content2) if content2 else 0}")
    if content2:
        print(f"content preview: {content2[:500]}")
        # Try to extract JSON
        clean = content2.strip()
        if clean.startswith("```"):
            clean = clean.split("```")[1]
            if clean.startswith("json"):
                clean = clean[4:]
        parsed2 = json.loads(clean)
        print(f"parsed keys: {list(parsed2.keys())}")
        if 'scenes' in parsed2:
            print(f"scenes count: {len(parsed2['scenes'])}")
            print(f"first scene: {json.dumps(parsed2['scenes'][0], indent=2)}")
except Exception as e:
    print(f"ERROR: {e}")
