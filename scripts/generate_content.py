"""
Content Factory - Pipeline de Generación de Contenido
Motor 1 (Guión): GPT-5.5 — narrativa creativa de alto nivel
Motor 2 (Prompts Visuales): Claude Opus — descripción cinematográfica superior
Motor 1.5 (Emociones): GPT-5.5
Motor SEO: GPT-5.5
"""
import os
import sys

# Fix Windows encoding for emoji/unicode output
if sys.platform == "win32":
    os.environ["PYTHONIOENCODING"] = "utf-8"
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
import json
import argparse
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

# ============================================================
# CLIENTES IA
# ============================================================
# Motor 1 (Guión) + Motor 1.5 (Emociones) + SEO → GPT-5.5
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
GPT_MODEL = config["models"]["script_generation"]

# Motor 2 (Prompts Visuales) → Claude Opus
# Si no hay API key de Anthropic, fallback a GPT-5.5
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
claude_client = None
CLAUDE_MODEL = "claude-opus-4-0-20250514"

if ANTHROPIC_API_KEY:
    try:
        import anthropic
        claude_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        print(f"✅ Claude Opus conectado para Motor 2 (Prompts Visuales)")
    except ImportError:
        print("⚠️  Módulo 'anthropic' no instalado. Instalando...")
        os.system(f"{sys.executable} -m pip install anthropic")
        import anthropic
        claude_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        print(f"✅ Claude Opus conectado para Motor 2 (Prompts Visuales)")
else:
    print("⚠️  ANTHROPIC_API_KEY no configurada. Motor 2 usará GPT-5.5 como fallback.")


# ============================================================
# CATÁLOGO DE AGENTES
# ============================================================
def list_agents():
    """Lista todos los agentes disponibles en la carpeta prompts/"""
    agents = sorted(PROMPTS_DIR.glob("agent_*.md"))
    print("\n🎭 AGENTES DISPONIBLES:")
    print("=" * 60)
    for i, agent_path in enumerate(agents, 1):
        name = agent_path.stem.replace("agent_", "").replace("_", " ").title()
        # Leer primera línea para obtener el título
        with open(agent_path, "r", encoding="utf-8") as f:
            title = f.readline().strip()
        print(f"  {i}. {agent_path.name}")
        print(f"     └─ {title}")
        print()
    print(f"  Total: {len(agents)} agentes disponibles")
    print(f"  Uso: python generate_content.py --agent {agents[0].name} \"Tu tema aquí\"")
    print("=" * 60)
    return agents


def load_prompt(filename: str) -> str:
    """Carga un system prompt desde la carpeta prompts/"""
    prompt_path = PROMPTS_DIR / filename
    if not prompt_path.exists():
        print(f"❌ ERROR: No se encontró el archivo de prompt: {prompt_path}")
        print(f"   Agentes disponibles:")
        for f in sorted(PROMPTS_DIR.glob("agent_*.md")):
            print(f"     - {f.name}")
        sys.exit(1)
    with open(prompt_path, "r", encoding="utf-8") as f:
        return f.read()


# ============================================================
# MOTOR 1: GUIÓN NARRATIVO (GPT-5.5)
# ============================================================
def generate_script(topic: str, agent_file: str = "agent_erotico_historico.md") -> dict:
    """
    Genera un guión narrativo completo usando GPT-5.5.
    
    Args:
        topic: El tema del video (ej: "La vida en Edo feudal 1700")
        agent_file: Archivo del agente personalidad a usar
    
    Returns:
        dict con el guión, metadata y estadísticas
    """
    agent_name = agent_file.replace("agent_", "").replace(".md", "").replace("_", " ").title()
    print(f"\n🧠 MOTOR 1: Generando guión para '{topic}'...")
    print(f"   Modelo: {GPT_MODEL}")
    print(f"   Agente: {agent_name} ({agent_file})")
    
    # Cargar el prompt del AI Agent seleccionado
    agent_prompt = load_prompt(agent_file)
    
    # Llamada a GPT-5.5
    response = openai_client.chat.completions.create(
        model=GPT_MODEL,
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
        "agent": agent_file,
        "script": script_text,
        "metadata": {
            "model": GPT_MODEL,
            "agent_personality": agent_file,
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


# ============================================================
# MOTOR 1.5: ETIQUETAS DE EMOCIÓN (GPT-5.5)
# ============================================================
def add_emotion_tags(script_text: str) -> str:
    """
    Máquina 1.5: Agrega etiquetas de emoción al guión para TTS.
    Divide por párrafos para manejar scripts largos.
    Incluye retry para respuestas vacías de GPT-5.5.
    """
    print("\n🎭 MOTOR 1.5: Agregando etiquetas de emoción...")

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
                response = openai_client.chat.completions.create(
                    model=GPT_MODEL,
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
                    print(f"   🚨 ALERTA DE SEGURIDAD: Respuesta vacía de OpenAI al procesar emociones.")
                    print(f"   🛑 ABORTANDO EJECUCIÓN para evitar fuga de tokens en el bucle.")
                    sys.exit(1)

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


# ============================================================
# MOTOR 2: PROMPTS VISUALES (CLAUDE OPUS — con fallback GPT-5.5)
# ============================================================
def generate_video_prompts_claude(chunk: str, scene_counter: int) -> list:
    """
    Genera prompts de video usando Claude Opus.
    Claude es superior en descripción visual y cinematográfica.
    """
    video_prompt_template = load_prompt("video_prompt_generator.md")

    start_seconds = scene_counter * 5
    start_mm = start_seconds // 60
    start_ss = start_seconds % 60

    for attempt in range(3):
        try:
            response = claude_client.messages.create(
                model=CLAUDE_MODEL,
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
                ],
            )

            content = response.content[0].text

            if not content or len(content) < 10:
                print(f"   🚨 ALERTA: Respuesta vacía de Claude.")
                print(f"   🛑 ABORTANDO para evitar gasto innecesario.")
                sys.exit(1)

            clean = content.strip()
            # Extraer JSON si viene envuelto en markdown code block
            if clean.startswith("```"):
                parts = clean.split("```")
                clean = parts[1] if len(parts) > 1 else parts[0]
                if clean.startswith("json"):
                    clean = clean[4:]
                clean = clean.strip()

            result = json.loads(clean)
            scenes = result.get("scenes", result.get("prompts", []))
            if isinstance(result, list):
                scenes = result

            if scenes:
                return scenes
            else:
                print(f"   ⚠️  Intento {attempt+1}: 0 escenas de Claude, reintentando...")

        except json.JSONDecodeError as e:
            print(f"   ⚠️  Intento {attempt+1}: error JSON de Claude ({e}), reintentando...")
        except Exception as e:
            print(f"   ⚠️  Intento {attempt+1}: error Claude ({e}), reintentando...")

    return None


def generate_video_prompts_gpt(chunk: str, scene_counter: int) -> list:
    """
    Genera prompts de video usando GPT-5.5 (fallback).
    """
    video_prompt_template = load_prompt("video_prompt_generator.md")

    start_seconds = scene_counter * 5
    start_mm = start_seconds // 60
    start_ss = start_seconds % 60

    for attempt in range(3):
        try:
            response = openai_client.chat.completions.create(
                model=GPT_MODEL,
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

            if not content or len(content) < 10:
                print(f"   🚨 ALERTA DE SEGURIDAD: Respuesta vacía de OpenAI (Posible filtro NSFW).")
                print(f"   🛑 ABORTANDO EJECUCIÓN para evitar gasto de tokens innecesario.")
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
                return scenes
            else:
                print(f"   ⚠️  Intento {attempt+1}: 0 escenas, reintentando...")

        except json.JSONDecodeError as e:
            print(f"   ⚠️  Intento {attempt+1}: error JSON ({e}), reintentando...")
        except Exception as e:
            if "insufficient_quota" in str(e):
                print(f"   🚨 ERROR FATAL: Te has quedado sin saldo en OpenAI (insufficient_quota).")
                print(f"   🛑 ABORTANDO EJECUCIÓN INMEDIATAMENTE.")
                sys.exit(1)
            print(f"   ⚠️  Intento {attempt+1}: error ({e}), reintentando...")

    return None


def generate_video_prompts(script_text: str) -> list:
    """
    Motor 2: Genera prompts de video cinematográficos.
    Usa Claude Opus como motor principal, GPT-5.5 como fallback.
    Divide el guión en chunks por párrafos para evitar límites de tokens.
    """
    use_claude = claude_client is not None
    engine_name = f"Claude Opus ({CLAUDE_MODEL})" if use_claude else f"GPT-5.5 ({GPT_MODEL})"
    
    print(f"\n🎬 MOTOR 2: Generando prompts de video...")
    print(f"   Motor visual: {engine_name}")

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

        # Intentar con Claude primero, fallback a GPT
        chunk_scenes = None
        if use_claude:
            chunk_scenes = generate_video_prompts_claude(chunk, scene_counter)
            if chunk_scenes is None:
                print(f"   ⚠️  Claude falló en chunk {i+1}, usando GPT-5.5 como fallback...")
                chunk_scenes = generate_video_prompts_gpt(chunk, scene_counter)
        else:
            chunk_scenes = generate_video_prompts_gpt(chunk, scene_counter)

        if chunk_scenes:
            all_scenes.extend(chunk_scenes)
            scene_counter += len(chunk_scenes)
            print(f"   ✅ Chunk {i+1}: {len(chunk_scenes)} escenas (total: {len(all_scenes)})")
        else:
            print(f"   ❌ Chunk {i+1}: falló después de todos los intentos, saltando...")

    print(f"   🎬 Total: {len(all_scenes)} escenas de video generadas")

    return all_scenes


# ============================================================
# MOTOR SEO (GPT-5.5)
# ============================================================
def generate_seo_metadata(topic: str, script_summary: str) -> dict:
    """
    Genera metadata SEO optimizada para YouTube.
    """
    print(f"\n📈 Generando metadata SEO...")
    
    seo_prompt = load_prompt("seo_optimizer.md")
    
    response = openai_client.chat.completions.create(
        model=GPT_MODEL,
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
def run_full_pipeline(topic: str, agent_file: str = "agent_erotico_historico.md"):
    """
    Ejecuta el pipeline completo de generación de contenido textual.
    Motor 1 (GPT-5.5) + Motor 1.5 (GPT-5.5) + Motor 2 (Claude Opus) + SEO (GPT-5.5)
    """
    use_claude = claude_client is not None

    print("=" * 60)
    print("🏭 CONTENT FACTORY — Tu Dosis Diaria")
    print("=" * 60)
    print(f"📌 Tema: {topic}")
    print(f"🎭 Agente: {agent_file}")
    print(f"🧠 Motor 1 (Guión): GPT-5.5")
    print(f"🎬 Motor 2 (Visual): {'Claude Opus' if use_claude else 'GPT-5.5 (fallback)'}")
    print(f"⏰ Inicio: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # PASO 1: Generar guión (GPT-5.5)
    result = generate_script(topic, agent_file)
    script = result["script"]
    
    # PASO 2: Agregar etiquetas de emoción (GPT-5.5)
    tagged_script = add_emotion_tags(script)
    
    # PASO 3: Generar prompts de video (Claude Opus / GPT-5.5 fallback)
    video_scenes = generate_video_prompts(script)
    
    # PASO 4: Generar SEO metadata (GPT-5.5)
    seo = generate_seo_metadata(topic, script[:500])
    
    # Guardar resultado completo
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = topic.lower().replace(" ", "_")[:50]
    
    full_result = {
        "topic": topic,
        "agent": agent_file,
        "script_plain": script,
        "script_tagged": tagged_script,
        "video_scenes": video_scenes,
        "seo_metadata": seo,
        "pipeline_metadata": {
            "generated_at": datetime.now().isoformat(),
            "total_scenes": len(video_scenes),
            "script_characters": len(script),
            "script_model": GPT_MODEL,
            "visual_model": CLAUDE_MODEL if use_claude else GPT_MODEL,
            "agent_personality": agent_file
        }
    }
    
    output_path = OUTPUT_DIR / f"FULL_{safe_name}_{timestamp}.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(full_result, f, ensure_ascii=False, indent=2)
    
    print("\n" + "=" * 60)
    print("✅ PIPELINE TEXTUAL COMPLETO")
    print("=" * 60)
    print(f"🎭 Agente: {agent_file}")
    print(f"📄 Guión: {len(script):,} caracteres")
    print(f"🎭 Etiquetas: {tagged_script.count('['):,} emociones")
    print(f"🎬 Escenas: {len(video_scenes)} clips de 5 seg")
    print(f"📈 SEO: {seo.get('title', 'N/A')}")
    print(f"💾 Guardado: {output_path}")
    print(f"⏰ Fin: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    return full_result


# ============================================================
# ARGUMENTOS DE LÍNEA DE COMANDO
# ============================================================
def parse_args():
    """Parsea argumentos de línea de comando."""
    parser = argparse.ArgumentParser(
        description="🏭 Content Factory — Generador de Documentales con IA",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos de uso:
  python generate_content.py "La caída del Imperio Romano"
  python generate_content.py --agent agent_horror.md "La Peste Negra de 1347"
  python generate_content.py --agent agent_misterios.md "La desaparición de la colonia Roanoke"
  python generate_content.py --agent agent_filosofia.md "Marco Aurelio y la muerte"
  python generate_content.py --agent agent_ciencia.md "Qué hay dentro de un agujero negro"
  python generate_content.py --agent agent_finanzas.md "El colapso de FTX y Sam Bankman-Fried"
  python generate_content.py --agent agent_biografias.md "La vida secreta de Nikola Tesla"
  python generate_content.py --agent agent_civilizaciones.md "Los Mayas y su misteriosa desaparición"
  python generate_content.py --agent agent_psicologia_oscura.md "La mente de un dictador: Stalin"
  python generate_content.py --list-agents
        """
    )
    
    parser.add_argument(
        "topic",
        nargs="?",
        default=None,
        help="Tema del video documental"
    )
    
    parser.add_argument(
        "--agent", "-a",
        default="agent_erotico_historico.md",
        help="Archivo del agente personalidad a usar (default: agent_erotico_historico.md)"
    )
    
    parser.add_argument(
        "--list-agents", "-l",
        action="store_true",
        help="Listar todos los agentes disponibles"
    )
    
    parser.add_argument(
        "--skip-emotions",
        action="store_true",
        help="Saltar el etiquetado de emociones (más rápido y barato)"
    )
    
    parser.add_argument(
        "--skip-seo",
        action="store_true",
        help="Saltar la generación de metadata SEO"
    )
    
    parser.add_argument(
        "--force-gpt",
        action="store_true",
        help="Forzar uso de GPT-5.5 para Motor 2 (en lugar de Claude)"
    )
    
    return parser.parse_args()


# ============================================================
# EJECUCIÓN
# ============================================================
if __name__ == "__main__":
    args = parse_args()
    
    # Listar agentes
    if args.list_agents:
        list_agents()
        sys.exit(0)
    
    # Verificar que hay un tema
    if not args.topic:
        print("❌ ERROR: Debes proporcionar un tema.")
        print("   Ejemplo: python generate_content.py --agent agent_horror.md \"La Peste Negra\"")
        print("   Usa --list-agents para ver los agentes disponibles.")
        sys.exit(1)
    
    # Forzar GPT si se pidió
    if args.force_gpt:
        claude_client = None
        print("⚠️  Modo --force-gpt: Motor 2 usará GPT-5.5 en lugar de Claude Opus")
    
    # Ejecutar pipeline
    run_full_pipeline(args.topic, args.agent)
