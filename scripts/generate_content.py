"""
Content Factory - Máquina 1: Generador de Guión
Usa OpenAI GPT-5.5 para crear narrativas inmersivas históricas.
"""
import os
import json
import sys
import io

# Fix Windows encoding for emoji output
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from datetime import datetime
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# ============================================================
# CONFIGURACIÓN
# ============================================================
BASE_DIR = Path(__file__).parent.parent
CONFIG_PATH = BASE_DIR / "config" / "settings.json"
PROMPTS_DIR = BASE_DIR / "prompts"
OUTPUT_DIR = BASE_DIR / "output" / "scripts"

# Crear directorio de output si no existe
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Cargar configuración
with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    config = json.load(f)

# Inicializar cliente OpenAI
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
MODEL = config["models"]["script_generation"]


def load_prompt(filename: str) -> str:
    """Carga un system prompt desde la carpeta prompts/"""
    prompt_path = PROMPTS_DIR / filename
    with open(prompt_path, "r", encoding="utf-8") as f:
        return f.read()


def generate_script(topic: str) -> dict:
    """
    Genera un guión narrativo completo usando GPT-5.5.
    
    Args:
        topic: El tema del video (ej: "La vida en Edo feudal 1700")
    
    Returns:
        dict con el guión, metadata y estadísticas
    """
    print(f"\n🧠 MÁQUINA 1: Generando guión para '{topic}'...")
    print(f"   Modelo: {MODEL}")
    
    # Cargar el prompt del AI Agent
    agent_prompt = load_prompt("agent_historico.md")
    
    # Llamada a GPT-5.5
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": agent_prompt
            },
            {
                "role": "user",
                "content": f"""Genera una narrativa inmersiva completa sobre el siguiente tema:

TEMA: {topic}

Requisitos:
- 8,000 a 9,000 caracteres de narrativa fluida
- 10 secciones que transicionen naturalmente
- Idioma: Español (Latinoamérica, acento neutro)
- Tono: Cinematográfico, inmersivo, educativo pero entretenido
- Incluye detalles históricos específicos (nombres, fechas, costumbres)
- NO uses viñetas ni encabezados — narrativa pura y fluida
- Cada sección debe fluir orgánicamente hacia la siguiente"""
            }
        ],
        max_completion_tokens=8192,
    )
    
    script_text = response.choices[0].message.content
    
    # Estadísticas
    char_count = len(script_text)
    word_count = len(script_text.split())
    estimated_minutes = word_count / 150  # ~150 palabras por minuto narradas
    
    # Metadata del guión
    result = {
        "topic": topic,
        "script": script_text,
        "metadata": {
            "model": MODEL,
            "characters": char_count,
            "words": word_count,
            "estimated_duration_minutes": round(estimated_minutes, 1),
            "generated_at": datetime.now().isoformat(),
            "tokens_used": {
                "prompt": response.usage.prompt_tokens,
                "completion": response.usage.completion_tokens,
                "total": response.usage.total_tokens
            }
        }
    }
    
    # Guardar
    safe_filename = topic.lower().replace(" ", "_")[:50]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = OUTPUT_DIR / f"{safe_filename}_{timestamp}.json"
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    # Reporte
    print(f"\n   ✅ Guión generado exitosamente!")
    print(f"   📝 Caracteres: {char_count:,}")
    print(f"   📊 Palabras: {word_count:,}")
    print(f"   ⏱️  Duración estimada: {estimated_minutes:.1f} minutos")
    print(f"   🪙 Tokens usados: {response.usage.total_tokens:,}")
    print(f"   💾 Guardado en: {output_path}")
    
    return result


def add_emotion_tags(script_text: str) -> str:
    """
    Máquina 1.5: Agrega etiquetas de emoción al guión para TTS.
    Divide por párrafos para manejar scripts largos.
    Incluye retry para respuestas vacías de GPT-5.5.
    """
    print("\n🎭 MÁQUINA 1.5: Agregando etiquetas de emoción...")

    emotion_prompt = load_prompt("emotion_tagger.md")

    # Dividir por párrafos para no exceder límites
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

    print(f"   📦 Dividido en {len(chunks)} chunks")

    tagged_chunks = []

    for i, chunk in enumerate(chunks):
        print(f"   🔄 Procesando chunk {i+1}/{len(chunks)}...")

        result = None
        for attempt in range(3):  # 3 intentos por chunk
            try:
                response = client.chat.completions.create(
                    model=MODEL,
                    messages=[
                        {
                            "role": "system",
                            "content": emotion_prompt
                        },
                        {
                            "role": "user",
                            "content": (
                                "Agrega etiquetas de emoción a este fragmento de guión. "
                                "Devuelve el texto COMPLETO con las etiquetas insertadas, "
                                "sin omitir ninguna parte del texto original:\n\n" + chunk
                            )
                        }
                    ],
                    max_completion_tokens=6000,
                )

                content = response.choices[0].message.content

                if content and len(content) > 50:
                    result = content
                    break
                else:
                    print(f"   ⚠️  Intento {attempt+1}: respuesta vacía, reintentando...")

            except Exception as e:
                print(f"   ⚠️  Intento {attempt+1}: error ({e}), reintentando...")

        if result:
            tag_count = result.count("[")
            tagged_chunks.append(result)
            print(f"   ✅ Chunk {i+1}: {tag_count} etiquetas insertadas")
        else:
            # Fallback: usar el chunk original sin etiquetas
            tagged_chunks.append(chunk)
            print(f"   ⚠️  Chunk {i+1}: sin respuesta, usando texto original")

    tagged_script = "\n\n".join(tagged_chunks)
    total_tags = tagged_script.count("[")
    print(f"   🎭 Total: {total_tags} etiquetas de emoción insertadas")

    return tagged_script


def generate_video_prompts(script_text: str) -> list:
    """
    Máquina 3: Genera prompts de video cinematográficos.
    Divide el guión en chunks por párrafos para evitar límites de tokens.
    """
    print("\n🎬 MÁQUINA 3: Generando prompts de video...")

    video_prompt_template = load_prompt("video_prompt_generator.md")

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
                response = client.chat.completions.create(
                    model=MODEL,
                    messages=[
                        {
                            "role": "system",
                            "content": video_prompt_template
                        },
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
                    ],
                    max_completion_tokens=8000,
                    response_format={"type": "json_object"}
                )

                content = response.choices[0].message.content

                if not content:
                    print(f"   ⚠️  Chunk {i+1} intento {attempt+1}: respuesta vacía, reintentando...")
                    continue

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

    print(f"   🎬 Total: {len(all_scenes)} escenas de video generadas")

    return all_scenes


def generate_seo_metadata(topic: str, script_summary: str) -> dict:
    """
    Genera metadata SEO optimizada para YouTube.
    """
    print(f"\n📈 Generando metadata SEO...")
    
    seo_prompt = load_prompt("seo_optimizer.md")
    
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": seo_prompt
            },
            {
                "role": "user",
                "content": f"""Genera metadata SEO para este video:

TEMA: {topic}
RESUMEN DEL SCRIPT: {script_summary[:1000]}

El canal se llama "Tu Dosis Diaria" y se enfoca en reconstrucciones
históricas inmersivas con IA. Contenido en español."""
            }
        ],
        max_completion_tokens=2000,
        response_format={"type": "json_object"}
    )
    
    try:
        metadata = json.loads(response.choices[0].message.content)
        print(f"   ✅ Título: {metadata.get('title', 'N/A')}")
        return metadata
    except json.JSONDecodeError:
        print("   ⚠️  Error parseando SEO metadata")
        return {}


# ============================================================
# PIPELINE PRINCIPAL
# ============================================================
def run_full_pipeline(topic: str):
    """
    Ejecuta el pipeline completo de generación de contenido textual.
    Máquinas 1 + 1.5 + 3 + SEO
    """
    print("=" * 60)
    print("🏭 CONTENT FACTORY — Tu Dosis Diaria")
    print("=" * 60)
    print(f"📌 Tema: {topic}")
    print(f"⏰ Inicio: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # PASO 1: Generar guión
    result = generate_script(topic)
    script = result["script"]
    
    # PASO 2: Agregar etiquetas de emoción
    tagged_script = add_emotion_tags(script)
    
    # PASO 3: Generar prompts de video
    video_scenes = generate_video_prompts(script)
    
    # PASO 4: Generar SEO metadata
    seo = generate_seo_metadata(topic, script[:500])
    
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
            "model": MODEL
        }
    }
    
    output_path = OUTPUT_DIR / f"FULL_{safe_name}_{timestamp}.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(full_result, f, ensure_ascii=False, indent=2)
    
    print("\n" + "=" * 60)
    print("✅ PIPELINE TEXTUAL COMPLETO")
    print("=" * 60)
    print(f"📄 Guión: {len(script):,} caracteres")
    print(f"🎭 Etiquetas: {tagged_script.count('['):,} emociones")
    print(f"🎬 Escenas: {len(video_scenes)} clips de 5 seg")
    print(f"📈 SEO: {seo.get('title', 'N/A')}")
    print(f"💾 Guardado: {output_path}")
    print(f"⏰ Fin: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    return full_result


# ============================================================
# EJECUCIÓN
# ============================================================
if __name__ == "__main__":
    if len(sys.argv) > 1:
        topic = " ".join(sys.argv[1:])
    else:
        topic = "La vida cotidiana en una casa de samurái en Edo, Japón, año 1700"
    
    run_full_pipeline(topic)
