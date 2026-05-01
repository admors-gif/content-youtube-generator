"""Debug: Analiza por qué el guión se truncó en la generación de escenas."""
import json, glob, os

# Encontrar el archivo más reciente del narcisista
files = sorted(
    glob.glob(r"C:\Users\admor\Downloads\Content You tube Generator\output\scripts\*narcisista*"),
    key=os.path.getmtime, reverse=True
)

if not files:
    # Buscar FULL_* recientes
    files = sorted(
        glob.glob(r"C:\Users\admor\Downloads\Content You tube Generator\output\scripts\FULL_*.json"),
        key=os.path.getmtime, reverse=True
    )

print(f"Archivo: {files[0] if files else 'NO ENCONTRADO'}")

if files:
    with open(files[0], encoding="utf-8") as f:
        data = json.load(f)
    
    script = data.get("script_plain", data.get("script", ""))
    paragraphs = [p.strip() for p in script.split("\n\n") if p.strip()]
    
    print(f"\n=== SCRIPT STATS ===")
    print(f"Total chars: {len(script)}")
    print(f"Total words: {len(script.split())}")
    print(f"Total paragraphs: {len(paragraphs)}")
    
    # Simular chunking
    chunks = []
    current = ""
    for p in paragraphs:
        if len(current) + len(p) > 3000 and current:
            chunks.append(current)
            current = p
        else:
            current = (current + "\n\n" + p) if current else p
    if current:
        chunks.append(current)
    
    print(f"\n=== CHUNKING (3000 char limit) ===")
    print(f"Total chunks: {len(chunks)}")
    for i, c in enumerate(chunks):
        last_50 = c[-60:].replace("\n", " ")
        print(f"  Chunk {i+1}: {len(c)} chars | ends: ...{last_50}")
    
    # Scenes analysis
    scenes = data.get("video_scenes", [])
    print(f"\n=== SCENES ===")
    print(f"Total scenes: {len(scenes)}")
    
    if scenes:
        last_scene = scenes[-1]
        narration = last_scene.get("narration_text", "")
        print(f"Last scene #{last_scene.get('scene_number')}")
        print(f"Last narration: {narration[:150]}...")
        
        # Calcular qué tan lejos llegaron las escenas
        all_narration = " ".join(s.get("narration_text", "") for s in scenes)
        
        # Encontrar dónde termina en el script
        last_words = narration[-50:] if narration else ""
        pos = script.find(last_words)
        if pos > 0:
            pct = (pos + len(last_words)) / len(script) * 100
            print(f"\nScript coverage: {pct:.1f}%")
            remaining = script[pos + len(last_words):]
            print(f"Remaining chars: {len(remaining)}")
            print(f"Remaining text preview: {remaining[:200]}...")
