import json
import os
from pathlib import Path
import sys
from anthropic import Anthropic
from dotenv import load_dotenv

# Import functions from generate_content
from generate_content import generate_seo_metadata, OUTPUT_DIR, MODEL, load_prompt
from datetime import datetime

load_dotenv()

def generate_video_prompts_claude(script_text: str) -> list:
    """
    Máquina 3: Genera prompts de video cinematográficos usando Claude 3.5 Sonnet.
    """
    print("\n🎬 MÁQUINA 3: Generando prompts de video con CLAUDE...")

    video_prompt_template = load_prompt("video_prompt_generator.md")
    
    anthropic_client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    # Dividir el guión en chunks de ~3000 chars por párrafos
    paragraphs = [p.strip() for p in script_text.split("\n\n") if p.strip()]
    chunks = []
    current_chunk = ""

    for para in paragraphs:
        if len(current_chunk) + len(para) > 3000 and current_chunk:
            chunks.append(current_chunk)
            current_chunk = para
        else:
            current_chunk = (current_chunk + "\n\n" + para) if current_chunk else para
    if current_chunk:
        chunks.append(current_chunk)

    print(f"   📦 Dividido en {len(chunks)} chunks para procesamiento")

    all_scenes = []
    scene_counter = 0

    for i, chunk in enumerate(chunks):
        print(f"   🔄 Procesando chunk {i+1}/{len(chunks)}...")

        start_seconds = scene_counter * 5
        start_mm = start_seconds // 60
        start_ss = start_seconds % 60

        chunk_scenes = None
        for attempt in range(3):
            try:
                response = anthropic_client.messages.create(
                    model="claude-sonnet-4-5-20250929",
                    max_tokens=8000,
                    system=video_prompt_template,
                    messages=[
                        {
                            "role": "user",
                            "content": (
                                f"Genera prompts de video para este fragmento de narrativa.\n"
                                f"Inicia la numeración de escenas desde {scene_counter + 1}.\n"
                                f"El timestamp de inicio es {start_mm:02d}:{start_ss:02d}.\n"
                                f"Cada escena = 5 segundos.\n\n"
                                f"Responde SOLO con un JSON valido con la estructura: "
                                f"{{\"scenes\": [...]}}\n\n"
                                f"FRAGMENTO DE NARRATIVA:\n\n{chunk}"
                            )
                        }
                    ]
                )

                content = response.content[0].text

                if not content or len(content) < 10:
                    print(f"   🚨 ALERTA DE SEGURIDAD: Respuesta vacía de Claude.")
                    print(f"   🛑 ABORTANDO EJECUCIÓN.")
                    sys.exit(1)

                clean = content.strip()
                if clean.startswith("```"):
                    parts = clean.split("```")
                    clean = parts[1] if len(parts) > 1 else parts[0]
                    if clean.startswith("json"):
                        clean = clean[4:]

                result = json.loads(clean)
                scenes = result.get("scenes", result.get("prompts", []))
                if isinstance(result, list):
                    scenes = result

                if scenes:
                    chunk_scenes = scenes
                    break
                else:
                    print(f"   ⚠️  Chunk {i+1} intento {attempt+1}: 0 escenas, reintentando...")

            except json.JSONDecodeError as e:
                print(f"   ⚠️  Chunk {i+1} intento {attempt+1}: error JSON ({e}), reintentando...")
            except Exception as e:
                print(f"   ⚠️  Chunk {i+1} intento {attempt+1}: error ({e}), reintentando...")

        if chunk_scenes:
            all_scenes.extend(chunk_scenes)
            scene_counter += len(chunk_scenes)
            print(f"   ✅ Chunk {i+1}: {len(chunk_scenes)} escenas (total: {len(all_scenes)})")
        else:
            print(f"   ❌ Chunk {i+1}: falló después de 3 intentos, saltando...")

    print(f"   🎬 Total: {len(all_scenes)} escenas de video generadas con Claude")

    return all_scenes

def resume_pipeline(json_path: str):
    print("=" * 60)
    print("🏭 CONTENT FACTORY — RETOMANDO PIPELINE (MÁQUINA 3 - CLAUDE)")
    print("=" * 60)
    
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    topic = data["topic"]
    script = data.get("script_plain") or data.get("script")
    tagged_script = data.get("script_tagged") or script
    
    print(f"📌 Tema: {topic}")
    print("✅ Guion y emociones cargados correctamente. Saltando Máquina 1 y 1.5...")
    
    # PASO 3: Generar prompts de video usando CLAUDE
    video_scenes = generate_video_prompts_claude(script)
    
    # PASO 4: Generar SEO metadata (con OpenAI o como esté configurado)
    # Como el usuario no tiene saldo en OpenAI, vamos a omitir el SEO por ahora
    # seo = generate_seo_metadata(topic, script[:500])
    seo = {"title": "Pasión y traición en el Antiguo Egipto (Generado con Claude)", "description": "Historia inmersiva."}
    
    # Guardar resultado completo
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = topic.lower().replace(" ", "_")[:50]
    
    full_result = {
        "topic": topic,
        "script_plain": script,
        "script_tagged": tagged_script,
        "video_scenes": video_scenes,
        "seo_metadata": seo,
        "pipeline_metadata": {
            "generated_at": datetime.now().isoformat(),
            "total_scenes": len(video_scenes),
            "script_characters": len(script),
            "model": "claude-3-5-sonnet"
        }
    }
    
    output_path = OUTPUT_DIR / f"FULL_RESUMED_{safe_name}_{timestamp}.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(full_result, f, ensure_ascii=False, indent=2)
        
    print("\n✅ PIPELINE COMPLETADO EXITOSAMENTE CON CLAUDE")
    print(f"💾 Guardado: {output_path}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python resume_content.py <ruta_al_json_incompleto>")
        sys.exit(1)
    resume_pipeline(sys.argv[1])
