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
import anthropic
import firebase_admin
from firebase_admin import credentials, firestore
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
_openai_key = os.getenv("OPENAI_API_KEY")
openai_client = OpenAI(api_key=_openai_key) if _openai_key else None
if not openai_client:
    print("⚠️ OPENAI_API_KEY no configurada — Motor OpenAI deshabilitado (usando Claude como fallback)")
GPT_MODEL = config["models"]["script_generation"]

# Anthropic (Claude)
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
claude_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY) if ANTHROPIC_API_KEY else None
CLAUDE_MODEL_SCRIPT = "claude-sonnet-4-6"

# Tavily (Web Research)
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")
tavily_client = None
if TAVILY_API_KEY:
    try:
        from tavily import TavilyClient
        tavily_client = TavilyClient(api_key=TAVILY_API_KEY)
        print("✅ Tavily Research Engine conectado.")
    except ImportError:
        print("⚠️ tavily-python no instalado — investigación web deshabilitada")
else:
    print("⚠️ TAVILY_API_KEY no configurada — guiones sin investigación web")
CLAUDE_MODEL_PROMPTS = "claude-opus-4-7"

# ============================================================
# FIREBASE ADMIN INIT
# ============================================================
firebase_db = None
try:
    if not firebase_admin._apps:
        firebase_cred_str = os.getenv("FIREBASE_SERVICE_ACCOUNT")
        if firebase_cred_str:
            cred_dict = json.loads(firebase_cred_str)
            cred = credentials.Certificate(cred_dict)
        else:
            cred = credentials.Certificate(str(BASE_DIR / "firebase-admin.json"))
        firebase_admin.initialize_app(cred)
    firebase_db = firestore.client()
    print("✅ Firebase Admin conectado correctamente.")
except Exception as e:
    print(f"⚠️ No se pudo inicializar Firebase Admin: {e}")

def update_progress(project_id: str, step_name: str, percent: int, extra_data: dict = None):
    if not firebase_db or not project_id:
        return
    try:
        doc_ref = firebase_db.collection("projects").document(project_id)
        update_data = {
            "progress.stepName": step_name,
            "progress.percent": percent,
        }
        if extra_data:
            update_data.update(extra_data)
        doc_ref.update(update_data)
    except Exception as e:
        print(f"⚠️ Error actualizando Firebase: {e}")


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
# MOTOR 0: INVESTIGACIÓN WEB (Tavily)
# ============================================================
def research_topic(topic: str, project_id: str = None) -> str:
    """
    Investiga un tema usando Tavily para obtener datos actuales y precisos.
    Retorna un resumen de investigación formateado para inyectar en el prompt.
    """
    if not tavily_client:
        print("   ⏭️ Tavily no disponible — generando sin investigación web")
        return ""
    
    print(f"\n🔍 MOTOR 0: Investigando '{topic}' en la web...")
    if project_id:
        update_progress(project_id, "🔍 Investigando tema en la web...", 3)
    
    try:
        # Búsqueda principal
        result = tavily_client.search(
            query=topic,
            search_depth="advanced",
            max_results=5,
            include_answer=True,
            include_raw_content=False,
        )
        
        # Construir contexto de investigación
        research_parts = []
        
        # Respuesta directa de Tavily
        if result.get("answer"):
            research_parts.append(f"RESUMEN: {result['answer']}")
        
        # Fuentes individuales
        for i, source in enumerate(result.get("results", [])[:5], 1):
            title = source.get("title", "")
            content = source.get("content", "")[:500]
            url = source.get("url", "")
            research_parts.append(f"FUENTE {i}: {title}\n{content}\n({url})")
        
        research_text = "\n\n".join(research_parts)
        
        word_count = len(research_text.split())
        source_count = len(result.get("results", []))
        print(f"   ✅ Investigación completada: {source_count} fuentes, {word_count} palabras")
        
        if project_id:
            update_progress(project_id, f"🔍 {source_count} fuentes encontradas", 5)
        
        return research_text
        
    except Exception as e:
        print(f"   ⚠️ Error en investigación Tavily: {e}")
        return ""


# ============================================================
# MOTOR 1: GUIÓN NARRATIVO (GPT-5.5)
# ============================================================
def generate_script(topic: str, agent_file: str = "agent_erotico_historico.md", project_id: str = None) -> dict:
    """
    Genera un guión narrativo completo usando GPT-5.5.
    Incluye investigación web via Tavily cuando está disponible.
    
    Args:
        topic: El tema del video (ej: "La vida en Edo feudal 1700")
        agent_file: Archivo del agente personalidad a usar
        project_id: ID del proyecto en Firebase para progreso
    
    Returns:
        dict con el guión, metadata y estadísticas
    """
    agent_name = agent_file.replace("agent_", "").replace(".md", "").replace("_", " ").title()
    print(f"\n🧠 MOTOR 1: Generando guión para '{topic}'...")
    print(f"   Modelo: {GPT_MODEL}")
    print(f"   Agente: {agent_name} ({agent_file})")
    
    # ── Paso 0: Investigación Web ──
    research_context = research_topic(topic, project_id)
    research_block = ""
    if research_context:
        research_block = f"""\n\n═══ INVESTIGACIÓN WEB ACTUAL ═══
Usa los siguientes datos reales y actuales como base factual para tu narrativa.
Incorpora nombres, fechas, cifras y hechos específicos de estas fuentes.
NO copies el texto directamente — reformula con tu estilo cinematográfico.

{research_context}
═══ FIN DE INVESTIGACIÓN ═══\n"""
    
    # Cargar el prompt del AI Agent seleccionado
    agent_prompt = load_prompt(agent_file)
    
    # Llamada a IA (Priorizando Claude Sonnet por tokens de OpenAI agotados)
    if claude_client:
        response = claude_client.messages.create(
            model=CLAUDE_MODEL_SCRIPT,
            max_tokens=8192,
            system=agent_prompt,
            messages=[
                {
                    "role": "user",
                    "content": f"""Genera una narrativa inmersiva completa sobre el siguiente tema:

TEMA: {topic}
{research_block}
Requisitos:
- 8,000 a 9,000 caracteres de narrativa fluida
- 10 secciones que transicionen naturalmente
- Idioma: Español (Latinoamérica, acento neutro)
- Tono: Cinematográfico, inmersivo, educativo pero entretenido
- Incluye detalles históricos específicos (nombres, fechas, costumbres)
- NO uses viñetas ni encabezados — narrativa pura y fluida
- Cada sección debe fluir orgánicamente hacia la siguiente
{"- IMPORTANTE: Incorpora datos y hechos de la investigación web proporcionada" if research_context else ""}"""
                }
            ],
        )
        script_text = response.content[0].text
        used_model = CLAUDE_MODEL_SCRIPT
    else:
        response = openai_client.chat.completions.create(
            model=GPT_MODEL,
            messages=[
                {"role": "system", "content": agent_prompt},
                {"role": "user", "content": f"TEMA: {topic}\n(Genera guión narrativa fluida sin viñetas)..."}
            ]
        )
        script_text = response.choices[0].message.content
        used_model = GPT_MODEL
    
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
            "model": used_model,
            "agent_personality": agent_file,
            "characters": char_count,
            "words": word_count,
            "estimated_duration_minutes": round(estimated_minutes, 1),
            "generated_at": datetime.now().isoformat(),
            "web_research": bool(research_context),
            "research_sources": len(research_context.split("FUENTE")) - 1 if research_context else 0,
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
                if claude_client:
                    resp = claude_client.messages.create(
                        model=CLAUDE_MODEL_SCRIPT,
                        max_tokens=6000,
                        system=emotion_prompt,
                        messages=[{"role": "user", "content": "Agrega etiquetas de emoción a este fragmento de guión. Devuelve el texto COMPLETO con las etiquetas insertadas:\n\n" + chunk}]
                    )
                    content = resp.content[0].text
                else:
                    resp = openai_client.chat.completions.create(
                        model=GPT_MODEL,
                        messages=[{"role": "system", "content": emotion_prompt}, {"role": "user", "content": chunk}]
                    )
                    content = resp.choices[0].message.content

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
                model=CLAUDE_MODEL_PROMPTS,
                max_tokens=16000,
                system=video_prompt_template,
                messages=[
                    {
                        "role": "user",
                        "content": (
                            f"Genera prompts de video para este fragmento de narrativa.\n"
                            f"Inicia la numeración de escenas desde {scene_counter + 1}.\n"
                            f"El timestamp de inicio es {start_mm:02d}:{start_ss:02d}.\n"
                            f"Cada escena = 5 segundos.\n\n"
                            f"IMPORTANTE: Debes cubrir TODO el texto del fragmento, "
                            f"desde la primera hasta la última oración. "
                            f"El campo narration_text debe contener el texto EXACTO del guión. "
                            f"No omitas ninguna parte del fragmento.\n\n"
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
                            f"IMPORTANTE: Debes cubrir TODO el texto del fragmento, "
                            f"desde la primera hasta la última oración. "
                            f"El campo narration_text debe contener el texto EXACTO del guión. "
                            f"No omitas ninguna parte del fragmento.\n\n"
                            f"Responde SOLO con un JSON valido con la estructura: "
                            f"{{\"scenes\": [...]}}\n\n"
                            f"FRAGMENTO DE NARRATIVA:\n\n{chunk}"
                        )
                    }
                ],
                max_completion_tokens=16000,
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
    engine_name = f"Claude Opus ({CLAUDE_MODEL_PROMPTS})" if use_claude else f"GPT-5.5 ({GPT_MODEL})"
    
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
    failed_chunks = []

    for i, chunk in enumerate(chunks):
        print(f"   🔄 Procesando chunk {i+1}/{len(chunks)}...")

        # Intentar con Claude primero, fallback a GPT
        chunk_scenes = None
        if use_claude:
            chunk_scenes = generate_video_prompts_claude(chunk, scene_counter)
            if chunk_scenes is None:
                print(f"   ⚠️  Claude falló en chunk {i+1}, usando GPT-5.5 como fallback...")
                if openai_client:
                    chunk_scenes = generate_video_prompts_gpt(chunk, scene_counter)
        else:
            chunk_scenes = generate_video_prompts_gpt(chunk, scene_counter)

        # SEGUNDO INTENTO: Si falló, intentar dividir el chunk en sub-chunks más pequeños
        if chunk_scenes is None:
            print(f"   🔄 Reintentando chunk {i+1} dividido en sub-chunks más pequeños...")
            sub_paragraphs = [p.strip() for p in chunk.split("\n\n") if p.strip()]
            sub_scenes = []
            sub_failed = False
            for j, sub_p in enumerate(sub_paragraphs):
                print(f"      Sub-chunk {j+1}/{len(sub_paragraphs)}...")
                sub_result = None
                if use_claude:
                    sub_result = generate_video_prompts_claude(sub_p, scene_counter + len(sub_scenes))
                if sub_result is None and openai_client:
                    sub_result = generate_video_prompts_gpt(sub_p, scene_counter + len(sub_scenes))
                if sub_result:
                    sub_scenes.extend(sub_result)
                else:
                    sub_failed = True
                    print(f"      ❌ Sub-chunk {j+1} también falló")
            if sub_scenes:
                chunk_scenes = sub_scenes
                if sub_failed:
                    print(f"   ⚠️  Chunk {i+1}: parcialmente recuperado ({len(sub_scenes)} escenas)")

        if chunk_scenes:
            all_scenes.extend(chunk_scenes)
            scene_counter += len(chunk_scenes)
            print(f"   ✅ Chunk {i+1}: {len(chunk_scenes)} escenas (total: {len(all_scenes)})")
        else:
            failed_chunks.append(i + 1)
            print(f"   🚨 ALERTA: Chunk {i+1}/{len(chunks)} perdido — el video estará incompleto")

    if failed_chunks:
        print(f"\n   🚨 ADVERTENCIA: {len(failed_chunks)} chunks fallaron: {failed_chunks}")
        print(f"   📊 Cobertura del guión: {((len(chunks) - len(failed_chunks)) / len(chunks) * 100):.0f}%")

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
    
    try:
        if claude_client:
            resp = claude_client.messages.create(
                model=CLAUDE_MODEL_SCRIPT,
                max_tokens=2000,
                system=seo_prompt,
                messages=[{"role": "user", "content": f"Genera metadata SEO para este video en JSON:\n\nTEMA: {topic}\nRESUMEN: {script_summary[:1000]}\n\nDevuelve SOLO un JSON valido con keys: title, description, tags."}]
            )
            content = resp.content[0].text
            clean = content.strip()
            if clean.startswith("```"):
                parts = clean.split("```")
                clean = parts[1] if len(parts) > 1 else parts[0]
                if clean.startswith("json"):
                    clean = clean[4:]
            metadata = json.loads(clean.strip())
        else:
            response = openai_client.chat.completions.create(
                model=GPT_MODEL,
                messages=[
                    {"role": "system", "content": seo_prompt},
                    {"role": "user", "content": f"Genera metadata SEO para este video:\nTEMA: {topic}\nRESUMEN: {script_summary[:1000]}"}
                ],
                response_format={"type": "json_object"}
            )
            metadata = json.loads(response.choices[0].message.content)
            
        print(f"   ✅ Título: {metadata.get('title', 'N/A')}")
        return metadata
    except Exception as e:
        print(f"   ⚠️  Error parseando SEO metadata: {e}")
        return {}


# ============================================================
# PIPELINE PRINCIPAL
# ============================================================
def run_full_pipeline(topic: str, agent_file: str = "agent_erotico_historico.md", project_id: str = None):
    """
    Ejecuta el pipeline completo de generación de contenido textual.
    Incluye error-handling global para reportar fallos a Firebase.
    """
    use_claude = claude_client is not None

    print("=" * 60)
    print("🏭 CONTENT FACTORY — Tu Dosis Diaria")
    print("=" * 60)
    print(f"📌 Tema: {topic}")
    print(f"🎭 Agente: {agent_file}")
    print(f"🗂️  Proyecto: {project_id}")

    # Validar que al menos un motor de IA esté disponible
    if not claude_client and not openai_client:
        error_msg = "No hay motor de IA disponible. Configura ANTHROPIC_API_KEY o OPENAI_API_KEY."
        print(f"❌ FATAL: {error_msg}")
        update_progress(project_id, f"Error: {error_msg}", 0, {"status": "error"})
        return None

    try:
        update_progress(project_id, "Iniciando generación de guión narrativo (Claude 3.5)...", 10)
        
        # PASO 1: Generar guión
        result = generate_script(topic, agent_file)
        script = result["script"]
        
        update_progress(project_id, "Agregando etiquetas de emoción y director...", 35)
        
        # PASO 2: Agregar etiquetas de emoción
        tagged_script = add_emotion_tags(script)
        
        update_progress(project_id, "Creando escenas y prompts visuales (Claude Opus)...", 60)
        
        # PASO 3: Generar prompts de video
        video_scenes = generate_video_prompts(script)
        
        update_progress(project_id, "Optimizando metadata SEO para YouTube...", 85)
        
        # PASO 4: Generar SEO metadata
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
                "script_characters": len(script)
            }
        }
        
        output_path = OUTPUT_DIR / f"FULL_{safe_name}_{timestamp}.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(full_result, f, ensure_ascii=False, indent=2)
            
        # GUARDAR EN FIREBASE
        if project_id:
            try:
                words = len(script.split())
                update_progress(project_id, "¡Generación completada!", 100, {
                    "status": "script_ready",
                    "script.plain": script,
                    "script.tagged": tagged_script,
                    "script.wordCount": words,
                    "script.estimatedMinutes": round(words / 150, 1),
                    "scenes": video_scenes,
                    "seo": seo,
                    "completedAt": firestore.SERVER_TIMESTAMP
                })
                print(f"✅ Firebase actualizado para proyecto {project_id}")
            except Exception as e:
                print(f"⚠️ Fallo al guardar en Firebase: {e}")
        
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

    except Exception as e:
        error_msg = f"Error en pipeline: {type(e).__name__}: {str(e)[:200]}"
        print(f"\n❌ FATAL: {error_msg}")
        import traceback
        traceback.print_exc()
        # Reportar el error a Firebase para que la UI muestre el fallo
        update_progress(project_id, f"Error: {str(e)[:150]}", 0, {"status": "error"})
        return None


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
        "--project-id", "-p",
        default=None,
        help="ID del proyecto de Firebase (opcional)"
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
    run_full_pipeline(args.topic, args.agent, args.project_id)
