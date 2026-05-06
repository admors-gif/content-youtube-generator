"""
Content Factory - Pipeline de Generación de Contenido
Motor 1 (Guion): Claude Sonnet primario, OpenAI fallback
Motor 2 (Prompts Visuales): Claude Opus primario, OpenAI fallback
Motor 1.5 (Emociones): Claude Sonnet primario, OpenAI fallback
Motor SEO: Claude Sonnet primario, OpenAI fallback
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
AI_MODELS = config.get("models", {})


def _configured_model(key: str, default: str, provider_prefix: str | None = None) -> str:
    value = str(AI_MODELS.get(key, "") or "").strip()
    if provider_prefix and value and not value.startswith(provider_prefix):
        return default
    return value or default


def _configured_openai_fallback(default: str = "gpt-5.5") -> str:
    for key in ("openai_fallback", "script_generation_fallback", "script_generation"):
        value = str(AI_MODELS.get(key, "") or "").strip()
        if value.startswith("gpt-"):
            return value
    return default


_openai_key = os.getenv("OPENAI_API_KEY")
openai_client = OpenAI(api_key=_openai_key) if _openai_key else None
if not openai_client:
    print("⚠️ OPENAI_API_KEY no configurada — fallback OpenAI deshabilitado")
GPT_MODEL = _configured_openai_fallback()

# Anthropic (Claude)
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
claude_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY) if ANTHROPIC_API_KEY else None
CLAUDE_MODEL_SCRIPT = _configured_model("script_generation", "claude-sonnet-4-6", "claude-")

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
CLAUDE_MODEL_PROMPTS = _configured_model("video_prompts", "claude-opus-4-7", "claude-")

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
        update_progress(project_id, "🔍 Investigando el tema...", 3, {"status": "researching"})
    
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
            update_progress(project_id, f"🔍 {source_count} fuentes seleccionadas", 5, {"status": "researching"})
        
        return research_text
        
    except Exception as e:
        print(f"   ⚠️ Error en investigación Tavily: {e}")
        return ""


# ============================================================
# MOTOR 1: GUIÓN NARRATIVO
# ============================================================
def generate_script(topic: str, agent_file: str = "agent_erotico_historico.md", project_id: str = None) -> dict:
    """
    Genera un guión narrativo completo.
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
    print(f"   Modelo: {CLAUDE_MODEL_SCRIPT if claude_client else GPT_MODEL}")
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
    
    # Llamada a IA: motor primario configurado con fallback OpenAI.
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
# MOTOR 1.5: ETIQUETAS DE EMOCIÓN
# ============================================================
def add_emotion_tags(script_text: str, prompt_file: str = "emotion_tagger.md") -> str:
    """
    Máquina 1.5: Agrega etiquetas de emoción al guión para TTS.
    Divide por párrafos para manejar scripts largos.
    Incluye retry para respuestas vacías del proveedor configurado.

    `prompt_file` permite usar un tagger especializado (ej. emotion_tagger_podcast.md
    para diálogos con dos hosts y reglas de densidad por speaker).
    """
    print(f"\n🎭 MOTOR 1.5: Agregando etiquetas de emoción ({prompt_file})...")

    emotion_prompt = load_prompt(prompt_file)

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
# MOTOR 2: PROMPTS VISUALES
# ============================================================
def generate_video_prompts_claude(chunk: str, scene_counter: int, prompt_file: str = "video_prompt_generator.md") -> list:
    """
    Genera prompts de video usando el motor visual configurado.

    `prompt_file` permite usar un generador especializado (ej.
    video_prompt_generator_podcast.md para estética de divulgación).
    """
    video_prompt_template = load_prompt(prompt_file)

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


def generate_video_prompts_gpt(chunk: str, scene_counter: int, prompt_file: str = "video_prompt_generator.md") -> list:
    """
    Genera prompts de video usando el fallback OpenAI configurado.

    `prompt_file` igual que en la versión Claude, permite estética alterna.
    """
    video_prompt_template = load_prompt(prompt_file)

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


def generate_video_prompts(script_text: str, prompt_file: str = "video_prompt_generator.md") -> list:
    """
    Motor 2: Genera prompts de video cinematográficos.
    Usa el motor visual primario configurado y fallback OpenAI.
    Divide el guión en chunks por párrafos para evitar límites de tokens.

    `prompt_file` permite cambiar la estética visual (ej.
    video_prompt_generator_podcast.md para divulgación contemporánea
    en lugar de cinematográfica dramática).
    """
    use_claude = claude_client is not None
    engine_name = "motor visual primario" if use_claude else "fallback visual"

    print(f"\n🎬 MOTOR 2: Generando prompts de video ({prompt_file})...")
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
            chunk_scenes = generate_video_prompts_claude(chunk, scene_counter, prompt_file=prompt_file)
            if chunk_scenes is None:
                print(f"   ⚠️  Motor visual primario falló en chunk {i+1}, usando fallback...")
                if openai_client:
                    chunk_scenes = generate_video_prompts_gpt(chunk, scene_counter, prompt_file=prompt_file)
        else:
            chunk_scenes = generate_video_prompts_gpt(chunk, scene_counter, prompt_file=prompt_file)

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
                    sub_result = generate_video_prompts_claude(sub_p, scene_counter + len(sub_scenes), prompt_file=prompt_file)
                if sub_result is None and openai_client:
                    sub_result = generate_video_prompts_gpt(sub_p, scene_counter + len(sub_scenes), prompt_file=prompt_file)
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
# MOTOR SEO
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
# PODCAST: Generación de guion conversacional con 2 voces
# ============================================================
import re as _re

# Mapeo de "nombre visible en guion" → speaker code (A o B)
PODCAST_SPEAKER_NAMES = {
    "MATEO": "A",
    "LUCÍA": "B",
    "LUCIA": "B",        # tolerar versión sin acento
    "HOST_A": "A",
    "HOST_B": "B",
}

PODCAST_TARGET_VISUAL_SCENES = 12
PODCAST_MAX_VISUAL_SCENES = 15

PODCAST_VISUAL_TEMPLATES = [
    (
        "Object macro",
        "Editorial macro photography of a symbolic object related to {topic}, warm amber studio light, shallow depth of field, minimalist composition, object-only frame, clean surface, magazine cover quality, photorealistic, 4k",
        ["object", "warm", "editorial"],
    ),
    (
        "Atmospheric place",
        "Empty contemporary studio corner suggesting a deep conversation about {topic}, warm practical lamps, deep teal shadows, calm cinematic atmosphere, empty room with two chairs, editorial style, 8k",
        ["studio", "atmosphere", "conversation"],
    ),
    (
        "Conceptual abstract",
        "Abstract visualization of emotional patterns connected to {topic}, flowing amber and deep teal particles, organic data shapes, clean dark background, conceptual editorial style, cinematic, 8k",
        ["abstract", "emotion", "data"],
    ),
    (
        "Anonymous silhouette",
        "Anonymous faceless silhouette seen from behind in a warm studio environment about {topic}, hands outside the frame, soft window light, thoughtful editorial photography, calm premium podcast mood, magazine quality, 4k",
        ["silhouette", "podcast", "intimate"],
    ),
    (
        "Symbolic still life",
        "Symbolic still life for {topic}: ceramic cup, closed notebook, soft shadows, amber highlights, deep teal background, minimalist editorial composition, clean blank surfaces, photorealistic, 4k",
        ["still-life", "symbolic", "warm"],
    ),
]


AUTOHYPNOSIS_TARGET_VISUAL_SCENES = 12
AUTOHYPNOSIS_MIN_VISUAL_SCENES = 8
AUTOHYPNOSIS_MAX_VISUAL_SCENES = 14
AUTOHYPNOSIS_ESTIMATED_WPM = 155
AUTOHYPNOSIS_DURATION_PROFILES = {
    "short": {"label": "corta", "target_minutes": 8, "characters": "6,500 a 8,000"},
    "standard": {"label": "estandar", "target_minutes": 15, "characters": "10,500 a 13,000"},
    "deep": {"label": "profunda", "target_minutes": 25, "characters": "17,000 a 21,000"},
}

LONG_MEDITATION_FORMAT = "meditacion_larga"
LONG_MEDITATION_ESTIMATED_WPM = 125
LONG_MEDITATION_DURATION_PROFILES = {
    "30m": {
        "label": "30 min",
        "target_minutes": 30,
        "speech_minutes": 12,
        "characters": "8,500 a 10,500",
        "visual_scenes": 12,
        "affirmation_spacing_minutes": 1.5,
    },
    "60m": {
        "label": "1 h",
        "target_minutes": 60,
        "speech_minutes": 20,
        "characters": "14,000 a 17,000",
        "visual_scenes": 18,
        "affirmation_spacing_minutes": 2.5,
    },
    "180m": {
        "label": "3 h",
        "target_minutes": 180,
        "speech_minutes": 36,
        "characters": "25,000 a 31,000",
        "visual_scenes": 30,
        "affirmation_spacing_minutes": 5,
    },
}

AUTOHYPNOSIS_VISUAL_TEMPLATES = [
    (
        "Breath field",
        "A serene abstract field of slow breathing light related to {topic}, soft violet and midnight blue gradients, warm gold particles moving like calm inhales and exhales, minimal premium wellness composition, no readable text, cinematic, 4k",
        ["breath", "calm", "abstract"],
    ),
    (
        "Safe room",
        "A quiet elegant room at night prepared for deep relaxation about {topic}, soft lamp glow, linen textures, closed curtains, a glass of water on a clean bedside table, peaceful cinematic wellness photography, no readable text, 4k",
        ["room", "night", "safe"],
    ),
    (
        "Inner landscape",
        "A dreamlike inner landscape symbolizing {topic}, still lake reflecting a violet dawn, gentle mist, distant warm light, slow cinematic serenity, premium meditation visual, no people, no readable text, 8k",
        ["landscape", "visualization", "peace"],
    ),
    (
        "Identity mirror",
        "A symbolic mirror scene for {topic}, soft golden light touching a clean mirror surface, blurred calm silhouette from behind only, hands outside frame, face not visible, elegant self-transformation mood, no readable text, 4k",
        ["identity", "mirror", "change"],
    ),
    (
        "Neural calm",
        "Abstract neural pathways transforming into soft golden threads connected to {topic}, smooth organic shapes, slow flowing light, deep blue background, scientific but gentle wellness aesthetic, no readable text, no logos, 8k",
        ["mind", "neural", "transformation"],
    ),
]

LONG_MEDITATION_VISUAL_TEMPLATES = [
    (
        "Night lake",
        "A nearly still moonlit lake for a long guided meditation about {topic}, deep midnight blue water, soft silver reflection, distant warm horizon glow, calm premium sleep ambience, no people, no readable text, cinematic, 4k",
        ["sleep", "lake", "stillness"],
    ),
    (
        "Breathing particles",
        "Minimal abstract breathing field for {topic}, slow violet gradients, sparse warm gold particles, soft depth, meditative premium background, no readable text, no logos, cinematic, 4k",
        ["abstract", "breath", "calm"],
    ),
    (
        "Safe bedroom",
        "Elegant quiet bedroom at night for a long relaxation session about {topic}, soft lamp glow, linen textures, closed curtains, peaceful empty room, no people, no readable text, premium wellness photography, 4k",
        ["room", "night", "sleep"],
    ),
    (
        "Dawn identity",
        "A soft dawn landscape symbolizing inner confidence and rest for {topic}, distant sun, gentle mist, still mountains, slow contemplative mood, no people, no readable text, cinematic, 8k",
        ["dawn", "identity", "peace"],
    ),
    (
        "Warm light path",
        "A slow glowing path of warm light through a calm dark forest for {topic}, peaceful atmosphere, no faces, no hands, no readable text, premium meditation visual, cinematic, 4k",
        ["path", "light", "safe"],
    ),
]


def _parse_podcast_script(text: str) -> list:
    """
    Parsea un guión de podcast en formato:
        MATEO: …línea…
        LUCÍA: …línea…
    y devuelve lista de bloques: [{"speaker": "A"|"B", "name": "MATEO", "text": "…"}].

    Regex robusto que tolera:
    - Variaciones de acento (LUCÍA / LUCIA)
    - Espacios extra alrededor de los dos puntos
    - Líneas vacías intercaladas
    - Líneas continuación sin prefix de speaker (se asignan al último speaker)

    Si una línea no matchea ningún patrón conocido y aún no hay speaker
    inicial, se descarta. Si ya hay speaker activo, la línea se concatena
    al último bloque (caso: línea cortada por wrap).
    """
    pattern = _re.compile(r"^\s*([A-ZÁÉÍÓÚÑ_]+)\s*:\s*(.+)$")
    blocks = []
    last_speaker_code = None
    last_name = None
    for raw_line in (text or "").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        m = pattern.match(line)
        if m:
            name = m.group(1).upper()
            content = m.group(2).strip()
            speaker_code = PODCAST_SPEAKER_NAMES.get(name)
            if speaker_code is None:
                # Speaker desconocido: lo registramos como "?"
                speaker_code = "?"
            blocks.append({"speaker": speaker_code, "name": name, "text": content})
            last_speaker_code = speaker_code
            last_name = name
        else:
            # Línea sin prefix: continuación del último speaker
            if blocks and last_speaker_code:
                blocks[-1]["text"] = blocks[-1]["text"] + " " + line
    return blocks


def _merge_scene_range(scene_range: list, scene_number: int) -> dict:
    """Une varias escenas podcast en una sola manteniendo dialogue_blocks."""
    blocks = []
    for scene in scene_range:
        blocks.extend(scene.get("dialogue_blocks") or [])
    return {
        "scene_number": scene_number,
        "narration_text": "\n".join(f"{b['name']}: {b['text']}" for b in blocks),
        "narration": " ".join(b["text"] for b in blocks),
        "dialogue_blocks": blocks,
    }


def _cap_podcast_scenes(scenes: list, max_scene_count: int) -> list:
    """Reduce escenas agrupando rangos contiguos para no disparar FLUX/TTS/KB."""
    if not max_scene_count or len(scenes) <= max_scene_count:
        return scenes

    capped = []
    total = len(scenes)
    for i in range(max_scene_count):
        start = round(i * total / max_scene_count)
        end = round((i + 1) * total / max_scene_count)
        chunk = scenes[start:end] or scenes[start:start + 1]
        capped.append(_merge_scene_range(chunk, i + 1))
    return capped


def _group_blocks_into_scenes(
    blocks: list,
    words_per_scene: int = 35,
    target_scene_count: int = None,
    max_scene_count: int = None,
) -> list:
    """
    Agrupa los dialogue_blocks en 'escenas' visuales para que cada escena
    cubra ~12-18 segundos de audio (≈ 35 palabras a ~3 wps).

    Esto permite que el pipeline FLUX genere una imagen por escena
    (consistente con narrativa/cinematico) y que Ken Burns sincronice
    duración con el audio agregado de la escena.

    Return: list de dicts compatible con el shape `video_scenes` esperado
    por factory.py:
      [
        {
          "scene_number": int,
          "narration_text": "MATEO: …\nLUCÍA: …",
          "narration": "…",   # texto plano sin prefijos para subtítulos
          "dialogue_blocks": [{speaker, name, text}, ...],
        }
      ]
    """
    if target_scene_count and blocks:
        total_words = sum(len((blk.get("text") or "").split()) for blk in blocks)
        # Podcast video no necesita una imagen cada 12s. Apuntamos a escenas
        # macro de 1-2 minutos para evitar 100+ generaciones de FLUX.
        words_per_scene = max(90, min(220, (total_words + target_scene_count - 1) // target_scene_count))

    scenes = []
    current_blocks = []
    current_word_count = 0
    scene_num = 0

    for blk in blocks:
        word_count = len(blk["text"].split())
        # Si agregar este bloque excede el target Y ya tenemos bloques, cerramos escena
        if current_blocks and current_word_count + word_count > words_per_scene:
            scene_num += 1
            scenes.append({
                "scene_number": scene_num,
                "narration_text": "\n".join(f"{b['name']}: {b['text']}" for b in current_blocks),
                "narration": " ".join(b["text"] for b in current_blocks),
                "dialogue_blocks": current_blocks,
            })
            current_blocks = []
            current_word_count = 0
        current_blocks.append(blk)
        current_word_count += word_count

    # Cerrar la última escena pendiente
    if current_blocks:
        scene_num += 1
        scenes.append({
            "scene_number": scene_num,
            "narration_text": "\n".join(f"{b['name']}: {b['text']}" for b in current_blocks),
            "narration": " ".join(b["text"] for b in current_blocks),
            "dialogue_blocks": current_blocks,
        })

    return _cap_podcast_scenes(scenes, max_scene_count)


def _topic_tags(topic: str) -> list:
    words = [
        w.lower()
        for w in _re.findall(r"[A-Za-zÁÉÍÓÚáéíóúÑñ0-9]{4,}", topic or "")
        if w.lower() not in {"para", "porque", "sobre", "como", "este", "esta", "tus"}
    ]
    tags = []
    for word in words:
        clean = (
            word.replace("á", "a").replace("é", "e").replace("í", "i")
            .replace("ó", "o").replace("ú", "u").replace("ñ", "n")
        )
        if clean not in tags:
            tags.append(clean)
    return tags[:2]


def _build_podcast_visual_scenes(topic: str, grouped_scenes: list) -> list:
    """
    Construye escenas visuales podcast de forma determinística y acotada.
    El objetivo es evitar que el generador documental produzca 100+ escenas.
    """
    topic_clean = (topic or "the episode theme").strip()
    topic_tags = _topic_tags(topic)
    visual_scenes = []
    safety_suffix = (
        " Faces absent or fully obscured, hands outside frame, fingers not visible, "
        "no readable text, no brand logos."
    )

    for i, scene in enumerate(grouped_scenes):
        category, template, base_tags = PODCAST_VISUAL_TEMPLATES[i % len(PODCAST_VISUAL_TEMPLATES)]
        prompt = template.format(topic=topic_clean)
        if safety_suffix.strip() not in prompt:
            prompt = f"{prompt}{safety_suffix}"
        tags = (base_tags + topic_tags)[:5]
        visual_scenes.append({
            "scene_number": i + 1,
            "narration_text": scene.get("narration_text", ""),
            "narration": scene.get("narration", ""),
            "dialogue_blocks": scene.get("dialogue_blocks", []),
            "prompt": prompt,
            "tags": tags,
            "visual_category": category,
        })

    return visual_scenes


def _split_text_into_balanced_segments(text: str, target_segments: int) -> list:
    """
    Divide texto largo en segmentos balanceados preservando el orden y sin
    perder palabras. Usado por formatos contemplativos donde una escena visual
    puede sostener 60-120s de audio con Ken Burns.
    """
    clean = (text or "").strip()
    if not clean:
        return []

    paragraphs = [p.strip() for p in _re.split(r"\n\s*\n+", clean) if p.strip()]
    if len(paragraphs) < target_segments:
        sentences = [
            s.strip()
            for s in _re.split(r"(?<=[.!?…])\s+", clean)
            if s.strip()
        ]
        units = sentences if len(sentences) >= target_segments else paragraphs
    else:
        units = paragraphs

    target_segments = max(1, min(target_segments, len(units)))
    segments = []
    for i in range(target_segments):
        start = round(i * len(units) / target_segments)
        end = round((i + 1) * len(units) / target_segments)
        chunk_units = units[start:end]
        if chunk_units:
            segments.append("\n\n".join(chunk_units).strip())

    return segments


def _normalize_autohypnosis_delivery(script_text: str) -> str:
    """
    Mantiene texto limpio para TTS: sin tags entre corchetes que puedan leerse
    literal, con pausas representadas por puntuacion natural.
    """
    text = (script_text or "").strip()
    text = _re.sub(r"\[[^\]]+\]", "", text)
    text = _re.sub(r"\s+\.\.\.", "...", text)
    text = _re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _append_unique_prompt_clauses(prompt: str, clauses: list[str]) -> str:
    """Adds safety clauses once, avoiding duplicated prompt instructions."""
    clean = " ".join((prompt or "").split())
    lower = clean.lower()
    for clause in clauses:
        normalized = " ".join((clause or "").split()).strip()
        if normalized and normalized.lower() not in lower:
            clean = f"{clean}, {normalized}"
            lower = clean.lower()
    return clean.strip()


def _autohypnosis_duration_profile(topic: str, requested_profile: str | None = None) -> dict:
    """
    Selects a duration profile without adding UI fields yet. Future UI presets can
    pass short/standard/deep; for now, titles mentioning long-form sessions opt in.
    """
    key = (requested_profile or "").strip().lower()
    if key in AUTOHYPNOSIS_DURATION_PROFILES:
        return AUTOHYPNOSIS_DURATION_PROFILES[key]

    lower = (topic or "").lower()
    if any(token in lower for token in ["3 horas", "tres horas", "180 min", "180 minutos"]):
        return AUTOHYPNOSIS_DURATION_PROFILES["deep"]
    if any(token in lower for token in ["8 min", "8 minutos", "corta", "rapida", "rápida"]):
        return AUTOHYPNOSIS_DURATION_PROFILES["short"]
    return AUTOHYPNOSIS_DURATION_PROFILES["standard"]


def _long_meditation_duration_profile(requested_profile: str | None = None, topic: str = "") -> dict:
    """Normalize 30m/1h/3h presets for long meditation production."""
    raw = (requested_profile or "").strip().lower().replace(" ", "")
    aliases = {
        "30": "30m",
        "30m": "30m",
        "30min": "30m",
        "30minutos": "30m",
        "mediahora": "30m",
        "1h": "60m",
        "60": "60m",
        "60m": "60m",
        "60min": "60m",
        "1hora": "60m",
        "180": "180m",
        "180m": "180m",
        "180min": "180m",
        "3h": "180m",
        "3horas": "180m",
        "treshoras": "180m",
    }
    key = aliases.get(raw)
    if key:
        return {**LONG_MEDITATION_DURATION_PROFILES[key], "key": key}

    lower = (topic or "").lower()
    if any(token in lower for token in ["3 horas", "tres horas", "180 min", "180 minutos"]):
        key = "180m"
    elif any(token in lower for token in ["30 min", "30 minutos", "media hora"]):
        key = "30m"
    else:
        key = "60m"
    return {**LONG_MEDITATION_DURATION_PROFILES[key], "key": key}


def _distribute_duration_seconds(total_seconds: int, scene_count: int) -> list[int]:
    scene_count = max(1, int(scene_count or 1))
    total_seconds = max(scene_count, int(total_seconds or scene_count))
    durations = []
    for i in range(scene_count):
        start = round(i * total_seconds / scene_count)
        end = round((i + 1) * total_seconds / scene_count)
        durations.append(max(1, end - start))
    drift = total_seconds - sum(durations)
    if drift:
        durations[-1] += drift
    return durations


def _build_autohypnosis_visual_scenes(topic: str, script_text: str) -> list:
    """
    Visuales acotados para autohipnosis: pocas escenas, tranquilas, sin manos,
    sin texto legible y sin imagineria clinica. La narracion se reparte completa
    entre las escenas para que el audio no pierda contenido.
    """
    topic_clean = (topic or "personal transformation").strip()
    topic_tags = _topic_tags(topic)
    segments = _split_text_into_balanced_segments(
        script_text,
        target_segments=AUTOHYPNOSIS_TARGET_VISUAL_SCENES,
    )
    if len(segments) > AUTOHYPNOSIS_MAX_VISUAL_SCENES:
        segments = _split_text_into_balanced_segments(
            script_text,
            target_segments=AUTOHYPNOSIS_MAX_VISUAL_SCENES,
        )

    safety_clauses = [
        "no readable text",
        "no logos",
        "no medical setting",
        "no hospital imagery",
        "hands outside frame",
        "fingers not visible",
        "peaceful and non-clinical",
    ]

    visual_scenes = []
    for i, segment in enumerate(segments):
        category, template, base_tags = AUTOHYPNOSIS_VISUAL_TEMPLATES[i % len(AUTOHYPNOSIS_VISUAL_TEMPLATES)]
        prompt = _append_unique_prompt_clauses(
            template.format(topic=topic_clean),
            safety_clauses,
        )
        visual_scenes.append({
            "scene_number": i + 1,
            "narration_text": segment,
            "narration": segment,
            "prompt": prompt,
            "tags": (base_tags + topic_tags)[:5],
            "visual_category": category,
        })

    return visual_scenes


def _build_long_meditation_visual_scenes(topic: str, script_text: str, profile: dict) -> list:
    """
    Long meditation uses few visual scenes and explicit target durations. The
    factory pads each scene audio to these durations, keeping TTS cost bounded.
    """
    topic_clean = (topic or "deep rest").strip()
    topic_tags = _topic_tags(topic)
    target_scene_count = int(profile.get("visual_scenes") or 8)
    segments = _split_text_into_balanced_segments(script_text, target_scene_count)
    if not segments:
        return []

    durations = _distribute_duration_seconds(
        int(float(profile.get("target_minutes", 60)) * 60),
        len(segments),
    )
    safety_clauses = [
        "no readable text",
        "no logos",
        "no medical setting",
        "no hospital imagery",
        "no faces facing camera",
        "hands outside frame",
        "fingers not visible",
        "almost static composition",
        "peaceful and non-clinical",
    ]

    visual_scenes = []
    for i, segment in enumerate(segments):
        category, template, base_tags = LONG_MEDITATION_VISUAL_TEMPLATES[i % len(LONG_MEDITATION_VISUAL_TEMPLATES)]
        prompt = _append_unique_prompt_clauses(
            template.format(topic=topic_clean),
            safety_clauses,
        )
        visual_scenes.append({
            "scene_number": i + 1,
            "narration_text": segment,
            "narration": segment,
            "prompt": prompt,
            "tags": (base_tags + topic_tags)[:5],
            "visual_category": category,
            "target_duration_seconds": durations[i],
            "pace": "long_meditation",
        })

    return visual_scenes


def generate_podcast_script(topic: str, agent_file: str = "agent_podcast_general.md", project_id: str = None) -> dict:
    """
    Genera un guión de podcast conversacional (2 hosts) usando el motor de guion configurado.
    Análogo a generate_script() pero apuntando al prompt podcast y con
    requisitos distintos (14-18K caracteres, formato MATEO:/LUCÍA:).
    """
    agent_name = agent_file.replace("agent_", "").replace(".md", "").replace("_", " ").title()
    print(f"\n🎙️  MOTOR 1 (PODCAST): Generando guión conversacional para '{topic}'...")
    print(f"   Modelo: {CLAUDE_MODEL_SCRIPT if claude_client else GPT_MODEL}")
    print(f"   Agente: {agent_name} ({agent_file})")

    # Investigación web previa (igual que documental)
    research_context = research_topic(topic, project_id)
    research_block = ""
    if research_context:
        research_block = f"""\n\n═══ INVESTIGACIÓN WEB ACTUAL ═══
Usa los siguientes datos reales como base factual para la conversación.
Incorpora cifras, fechas y ejemplos específicos en boca de MATEO (que es el host estructurado).
NO copies directo — los hosts hablan de los datos, no los recitan.

{research_context}
═══ FIN DE INVESTIGACIÓN ═══\n"""

    agent_prompt = load_prompt(agent_file)

    user_message = f"""Genera el guión completo de un episodio de podcast sobre el siguiente tema.

TEMA: {topic}
{research_block}
Requisitos estrictos:
- 14,000 a 18,000 caracteres (estrictos)
- Formato exacto: cada línea inicia con MATEO: o LUCÍA: en mayúsculas, seguido de dos puntos
- 10 secciones según el ROLE definido en el system prompt
- Cierra con LUCÍA hablando
- Tags emocionales solo del set permitido y con la densidad indicada
- Idioma: español neutro de Latinoamérica
- Conversación humana, NO narración ni recitado

Devuelve solo el guión, sin headers ni comentarios."""

    if claude_client:
        response = claude_client.messages.create(
            model=CLAUDE_MODEL_SCRIPT,
            max_tokens=16000,
            system=agent_prompt,
            messages=[{"role": "user", "content": user_message}],
        )
        script_text = response.content[0].text
        used_model = CLAUDE_MODEL_SCRIPT
    else:
        response = openai_client.chat.completions.create(
            model=GPT_MODEL,
            messages=[
                {"role": "system", "content": agent_prompt},
                {"role": "user", "content": user_message},
            ],
        )
        script_text = response.choices[0].message.content
        used_model = GPT_MODEL

    char_count = len(script_text)
    word_count = len(script_text.split())
    estimated_minutes = word_count / 130  # podcast: ~130 palabras/min (más pausado que narración)

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
            "format": "podcast",
            "generated_at": datetime.now().isoformat(),
            "web_research": bool(research_context),
            "research_sources": len(research_context.split("FUENTE")) - 1 if research_context else 0,
        },
    }

    print(f"\n   ✅ Guión podcast generado!")
    print(f"   📝 Caracteres: {char_count:,}")
    print(f"   📊 Palabras: {word_count:,}")
    print(f"   ⏱️  Duración estimada: {estimated_minutes:.1f} minutos")

    return result


def generate_autohypnosis_script(
    topic: str,
    agent_file: str = "agent_autohipnosis.md",
    project_id: str = None,
    duration_profile: str | None = None,
) -> dict:
    """
    Genera una sesión de autohipnosis guiada. No usa investigación web por
    defecto: este formato debe ser estable, seguro y basado en estructura
    terapéutica general de wellness, no en datos noticiosos.
    """
    agent_name = agent_file.replace("agent_", "").replace(".md", "").replace("_", " ").title()
    print(f"\n🌙 MOTOR 1 (AUTOHIPNOSIS): Generando sesión guiada para '{topic}'...")
    print(f"   Modelo: {CLAUDE_MODEL_SCRIPT if claude_client else GPT_MODEL}")
    print(f"   Agente: {agent_name} ({agent_file})")

    agent_prompt = load_prompt(agent_file)
    profile = _autohypnosis_duration_profile(topic, duration_profile)
    user_message = f"""Genera una sesión completa de autohipnosis guiada sobre el siguiente objetivo.

OBJETIVO: {topic}

Requisitos estrictos:
- Duración objetivo: aproximadamente {profile['target_minutes']} minutos
- Extensión objetivo: {profile['characters']} caracteres
- Español neutro de Latinoamérica
- Texto plano de una sola voz, sin encabezados, sin bullets y sin markdown
- Estructura completa: aviso seguro, inducción, profundización, visualización, afirmaciones, ensayo futuro, integración y salida
- Afirmaciones positivas en presente, en segunda persona y/o primera persona cuando suene natural
- No prometas curas, resultados garantizados ni tratamiento médico
- No trabajes traumas, recuerdos reprimidos ni diagnósticos clínicos
- Usa pausas con puntos suspensivos y frases respirables, no tags entre corchetes
- Si el objetivo es sueño o descanso, termina con salida suave para dormir; si no, termina con retorno alerta y tranquilo

Devuelve solo el guion final."""

    if claude_client:
        response = claude_client.messages.create(
            model=CLAUDE_MODEL_SCRIPT,
            max_tokens=14000,
            system=agent_prompt,
            messages=[{"role": "user", "content": user_message}],
        )
        script_text = response.content[0].text
        used_model = CLAUDE_MODEL_SCRIPT
    else:
        response = openai_client.chat.completions.create(
            model=GPT_MODEL,
            messages=[
                {"role": "system", "content": agent_prompt},
                {"role": "user", "content": user_message},
            ],
        )
        script_text = response.choices[0].message.content
        used_model = GPT_MODEL

    script_text = _normalize_autohypnosis_delivery(script_text)
    char_count = len(script_text)
    word_count = len(script_text.split())
    estimated_minutes = word_count / AUTOHYPNOSIS_ESTIMATED_WPM

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
            "target_duration_minutes": profile["target_minutes"],
            "duration_profile": profile["label"],
            "format": "autohipnosis",
            "generated_at": datetime.now().isoformat(),
            "web_research": False,
            "research_sources": 0,
        },
    }

    print(f"\n   ✅ Sesión de autohipnosis generada!")
    print(f"   📝 Caracteres: {char_count:,}")
    print(f"   📊 Palabras: {word_count:,}")
    print(f"   ⏱️  Duración estimada: {estimated_minutes:.1f} minutos")

    return result


def generate_long_meditation_script(
    topic: str,
    agent_file: str = "agent_meditacion_larga.md",
    project_id: str = None,
    duration_profile: str | None = None,
) -> dict:
    """
    Genera la parte hablada de una meditacion larga. La duracion final se logra
    despues con pausas, ambiente y visuales largos; no con 3 horas de TTS.
    """
    agent_name = agent_file.replace("agent_", "").replace(".md", "").replace("_", " ").title()
    profile = _long_meditation_duration_profile(duration_profile, topic)
    print(f"\n🌌 MOTOR 1 (MEDITACION LARGA): Generando guia para '{topic}'...")
    print(f"   Modelo: {CLAUDE_MODEL_SCRIPT if claude_client else GPT_MODEL}")
    print(f"   Agente: {agent_name} ({agent_file})")
    print(f"   Duracion final: {profile['label']} | Voz objetivo: {profile['speech_minutes']} min")

    agent_prompt = load_prompt(agent_file)
    user_message = f"""Genera la parte hablada de una meditacion guiada larga sobre el siguiente objetivo.

OBJETIVO: {topic}

Perfil de produccion:
- Duracion final del video: {profile['target_minutes']} minutos
- Duracion hablada objetivo: aproximadamente {profile['speech_minutes']} minutos
- Extension hablada objetivo: {profile['characters']} caracteres
- Cadencia hablada: disenar intervenciones breves y regulares cada {profile['affirmation_spacing_minutes']} minutos aproximadamente
- Visuales finales: {profile['visual_scenes']} escenas casi estaticas

Requisitos estrictos:
- Espanol neutro de Latinoamerica
- Una sola voz
- Texto plano, sin encabezados, sin bullets, sin markdown
- No uses tags entre corchetes
- Usa puntos suspensivos para respiracion y pausas naturales
- No prometas curas, resultados garantizados ni tratamiento medico
- El guion debe sostener una experiencia larga sin sentirse detenido: presencia regular, pausas meditativas y afirmaciones memorables
- Evita huecos conceptuales enormes; el oyente debe sentir acompanamiento continuo aunque haya momentos de silencio
- Si el objetivo menciona dormir, noche o descanso, termina permitiendo seguir descansando; si no, termina con una integracion tranquila

Devuelve solo el guion hablado final."""

    if claude_client:
        response = claude_client.messages.create(
            model=CLAUDE_MODEL_SCRIPT,
            max_tokens=12000,
            system=agent_prompt,
            messages=[{"role": "user", "content": user_message}],
        )
        script_text = response.content[0].text
        used_model = CLAUDE_MODEL_SCRIPT
    else:
        response = openai_client.chat.completions.create(
            model=GPT_MODEL,
            messages=[
                {"role": "system", "content": agent_prompt},
                {"role": "user", "content": user_message},
            ],
        )
        script_text = response.choices[0].message.content
        used_model = GPT_MODEL

    script_text = _normalize_autohypnosis_delivery(script_text)
    char_count = len(script_text)
    word_count = len(script_text.split())
    speech_minutes = word_count / LONG_MEDITATION_ESTIMATED_WPM

    result = {
        "topic": topic,
        "agent": agent_file,
        "script": script_text,
        "metadata": {
            "model": used_model,
            "agent_personality": agent_file,
            "characters": char_count,
            "words": word_count,
            "estimated_duration_minutes": round(profile["target_minutes"], 1),
            "estimated_speech_minutes": round(speech_minutes, 1),
            "target_duration_minutes": profile["target_minutes"],
            "duration_profile": profile["key"],
            "duration_label": profile["label"],
            "speech_target_minutes": profile["speech_minutes"],
            "visual_scene_target": profile["visual_scenes"],
            "format": LONG_MEDITATION_FORMAT,
            "generated_at": datetime.now().isoformat(),
            "web_research": False,
            "research_sources": 0,
        },
    }

    print(f"\n   ✅ Meditacion larga generada!")
    print(f"   📝 Caracteres TTS: {char_count:,}")
    print(f"   📊 Palabras: {word_count:,}")
    print(f"   ⏱️  Voz estimada: {speech_minutes:.1f} min | Final: {profile['target_minutes']} min")

    return result


# ============================================================
# PIPELINE PRINCIPAL
# ============================================================
def run_full_pipeline(
    topic: str,
    agent_file: str = "agent_erotico_historico.md",
    project_id: str = None,
    generation_options: dict | None = None,
):
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
    generation_options = generation_options or {}

    # Validar que al menos un motor de IA esté disponible
    if not claude_client and not openai_client:
        error_msg = "El estudio no tiene motores creativos configurados."
        print(f"❌ FATAL: {error_msg}")
        update_progress(project_id, f"Error: {error_msg}", 0, {"status": "error"})
        return None

    # Detectar formatos especiales: usan generación y visuales especializados
    # para evitar exceso de escenas y conservar el estilo correcto.
    is_podcast = agent_file.startswith("agent_podcast_")
    is_autohypnosis = agent_file == "agent_autohipnosis.md"
    is_long_meditation = agent_file == "agent_meditacion_larga.md"
    if is_podcast:
        print("🎙️  Modo PODCAST detectado — pipeline conversacional con 2 voces")
    if is_autohypnosis:
        print("🌙 Modo AUTOHIPNOSIS detectado — sesión guiada con visuales contemplativos")
    if is_long_meditation:
        print("🌌 Modo MEDITACION LARGA detectado — duracion extendida con bajo costo")

    try:
        update_progress(project_id, "Escribiendo la estructura narrativa...", 10, {"status": "scripting"})

        # PASO 1: Generar guión (formatos especiales usan generador propio)
        if is_podcast:
            result = generate_podcast_script(topic, agent_file, project_id)
        elif is_autohypnosis:
            result = generate_autohypnosis_script(
                topic,
                agent_file,
                project_id,
                duration_profile=generation_options.get("duration_profile"),
            )
        elif is_long_meditation:
            result = generate_long_meditation_script(
                topic,
                agent_file,
                project_id,
                duration_profile=generation_options.get("duration_profile"),
            )
        else:
            result = generate_script(topic, agent_file)
        script = result["script"]

        update_progress(project_id, "Afinando ritmo, emoción y voz...", 35, {"status": "scripting"})

        # PASO 2: Agregar etiquetas de emoción (tagger especializado para podcast
        # respeta densidades por speaker)
        if is_autohypnosis or is_long_meditation:
            tagged_script = _normalize_autohypnosis_delivery(script)
        else:
            emotion_prompt_file = "emotion_tagger_podcast.md" if is_podcast else "emotion_tagger.md"
            tagged_script = add_emotion_tags(script, prompt_file=emotion_prompt_file)

        # Para podcast, parseamos el guión en bloques de diálogo y agrupamos
        # en escenas visuales antes del PASO 3.
        podcast_blocks = []
        podcast_scenes_grouped = None
        if is_podcast:
            podcast_blocks = _parse_podcast_script(tagged_script)
            podcast_scenes_grouped = _group_blocks_into_scenes(
                podcast_blocks,
                target_scene_count=PODCAST_TARGET_VISUAL_SCENES,
                max_scene_count=PODCAST_MAX_VISUAL_SCENES,
            )
            print(f"   🎭 Podcast parseado: {len(podcast_blocks)} bloques de diálogo → "
                  f"{len(podcast_scenes_grouped)} escenas visuales")

        update_progress(project_id, "Diseñando escenas visuales...", 60, {"status": "prompting"})

        # PASO 3: Generar prompts de video (estética por formato)
        if is_podcast:
            video_scenes = _build_podcast_visual_scenes(topic, podcast_scenes_grouped)
            print(f"   🎬 Podcast visual: {len(video_scenes)} escenas macro "
                  f"(target={PODCAST_TARGET_VISUAL_SCENES}, max={PODCAST_MAX_VISUAL_SCENES})")
        elif is_autohypnosis:
            video_scenes = _build_autohypnosis_visual_scenes(topic, tagged_script)
            print(f"   🌙 Autohipnosis visual: {len(video_scenes)} escenas contemplativas "
                  f"(target={AUTOHYPNOSIS_TARGET_VISUAL_SCENES}, max={AUTOHYPNOSIS_MAX_VISUAL_SCENES})")
        elif is_long_meditation:
            long_profile = _long_meditation_duration_profile(
                result["metadata"].get("duration_profile"),
                topic,
            )
            video_scenes = _build_long_meditation_visual_scenes(topic, tagged_script, long_profile)
            print(f"   🌌 Meditacion larga visual: {len(video_scenes)} escenas casi estaticas "
                  f"(final={long_profile['target_minutes']} min)")
        else:
            video_scenes = generate_video_prompts(script, prompt_file="video_prompt_generator.md")

        # Para podcast: enriquecer las escenas generadas con los dialogue_blocks
        # del parsing previo, alineando por scene_number cuando es posible.
        if is_podcast and podcast_scenes_grouped:
            for scene in video_scenes:
                sn = scene.get("scene_number", 0)
                # scene_number puede no coincidir 1:1 con las escenas agrupadas
                # por palabras, así que las atamos por índice ordinal
                idx = sn - 1
                if 0 <= idx < len(podcast_scenes_grouped):
                    grouped = podcast_scenes_grouped[idx]
                    scene["dialogue_blocks"] = grouped["dialogue_blocks"]
                    # Si el video_prompts perdió el narration_text, restaurar
                    if not scene.get("narration_text"):
                        scene["narration_text"] = grouped["narration_text"]

        update_progress(project_id, "Preparando título, descripción y empaque...", 85, {"status": "prompting"})

        # PASO 4: Generar SEO metadata (mismo para ambos formatos)
        seo = generate_seo_metadata(topic, script[:500])

        # Guardar resultado completo
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = topic.lower().replace(" ", "_")[:50]

        full_result = {
            "topic": topic,
            "agent": agent_file,
            "format": "podcast" if is_podcast else LONG_MEDITATION_FORMAT if is_long_meditation else "autohipnosis" if is_autohypnosis else "narrativa",
            "script_plain": script,
            "script_tagged": tagged_script,
            "video_scenes": video_scenes,
            "seo_metadata": seo,
            "pipeline_metadata": {
                "generated_at": datetime.now().isoformat(),
                "total_scenes": len(video_scenes),
                "script_characters": len(script),
            },
        }
        if is_podcast:
            full_result["podcast"] = {
                "show_name": "Este no es otro podcast más",
                "host_a": {"name": "Mateo", "voice": "Will"},
                "host_b": {"name": "Lucía", "voice": "Lina"},
                "total_blocks": len(podcast_blocks),
            }
        if is_autohypnosis:
            full_result["autohipnosis"] = {
                "voice": "Lorenzo",
                "safety": "wellness_only",
                "visual_scene_target": AUTOHYPNOSIS_TARGET_VISUAL_SCENES,
                "target_minutes": result["metadata"].get("target_duration_minutes"),
                "duration_profile": result["metadata"].get("duration_profile"),
                "background_music": {
                    "enabled": False,
                    "asset": None,
                    "volume_db": -28,
                    "status": "awaiting_curated_tracks",
                },
            }
        if is_long_meditation:
            full_result["longMeditation"] = {
                "voice": "Lorenzo",
                "safety": "wellness_only",
                "target_minutes": result["metadata"].get("target_duration_minutes"),
                "duration_profile": result["metadata"].get("duration_profile"),
                "duration_label": result["metadata"].get("duration_label"),
                "speech_target_minutes": result["metadata"].get("speech_target_minutes"),
                "estimated_speech_minutes": result["metadata"].get("estimated_speech_minutes"),
                "visual_scene_target": result["metadata"].get("visual_scene_target"),
                "affirmation_spacing_minutes": _long_meditation_duration_profile(
                    result["metadata"].get("duration_profile"),
                    topic,
                ).get("affirmation_spacing_minutes"),
                "background_music": {
                    "enabled": True,
                    "asset": None,
                    "volume_db": -24,
                    "status": "procedural_ambient_until_curated_tracks",
                    "procedural_fallback": True,
                },
                "subtitles": {"enabled": False, "reason": "long_form_relaxation"},
                "shorts": {"enabled": False, "reason": "long_form_relaxation"},
            }

        output_path = OUTPUT_DIR / f"FULL_{safe_name}_{timestamp}.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(full_result, f, ensure_ascii=False, indent=2)

        # GUARDAR EN FIREBASE
        if project_id:
            try:
                words = len(script.split())
                # Podcast/autohipnosis son más pausados que narrativa.
                wpm = 130 if is_podcast else LONG_MEDITATION_ESTIMATED_WPM if is_long_meditation else AUTOHYPNOSIS_ESTIMATED_WPM if is_autohypnosis else 150
                estimated_minutes = round(words / wpm, 1)
                if is_long_meditation:
                    estimated_minutes = result["metadata"].get("target_duration_minutes") or estimated_minutes
                firestore_payload = {
                    "status": "script_ready",
                    "script.plain": script,
                    "script.tagged": tagged_script,
                    "script.wordCount": words,
                    "script.estimatedMinutes": round(estimated_minutes, 1),
                    "scenes": video_scenes,
                    "seo": seo,
                    "completedAt": firestore.SERVER_TIMESTAMP,
                }
                if is_long_meditation:
                    firestore_payload["script.speechEstimatedMinutes"] = result["metadata"].get("estimated_speech_minutes")
                    firestore_payload["script.targetMinutes"] = result["metadata"].get("target_duration_minutes")
                if is_podcast:
                    firestore_payload["format"] = "podcast"
                    firestore_payload["podcast"] = full_result["podcast"]
                if is_autohypnosis:
                    firestore_payload["format"] = "autohipnosis"
                    firestore_payload["autohipnosis"] = full_result["autohipnosis"]
                if is_long_meditation:
                    firestore_payload["format"] = LONG_MEDITATION_FORMAT
                    firestore_payload["longMeditation"] = full_result["longMeditation"]
                update_progress(project_id, "Guion listo para revisión", 100, firestore_payload)
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
        update_progress(project_id, "Error: el estudio creativo se detuvo", 0, {"status": "error"})
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
        help="Forzar uso del fallback OpenAI para Motor 2"
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
        print("⚠️  Modo --force-gpt: Motor 2 usará fallback OpenAI")
    
    # Ejecutar pipeline
    run_full_pipeline(args.topic, args.agent, args.project_id)
