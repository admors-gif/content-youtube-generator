"""
Content Factory - Test Rapido: ElevenLabs + Luma
Prueba ambas APIs con 1 escena para verificar que funcionan
y medir costos reales.

Uso: python scripts/test_new_workflows.py
"""
import os
import sys
import time
from pathlib import Path
from dotenv import load_dotenv

# Agregar el directorio de scripts al path
sys.path.insert(0, str(Path(__file__).parent))
load_dotenv()

BASE_DIR = Path(__file__).parent.parent


def test_elevenlabs():
    """Prueba ElevenLabs TTS con 1 parrafo."""
    print("\n" + "=" * 60)
    print("   TEST 1: ElevenLabs Text-to-Speech")
    print("=" * 60)
    
    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        print("   [SKIP] ELEVENLABS_API_KEY no configurada en .env")
        print("   Para obtener: https://elevenlabs.io/app/settings/api-keys")
        print("   Plan Free = 10,000 chars/mes (suficiente para 1 video)")
        return False
    
    from elevenlabs_tts import generate_narration
    
    test_text = (
        "En las sombras de Jonestown, mas de novecientas almas "
        "siguieron a un hombre hacia la oscuridad. Esta es la "
        "historia de Jim Jones, el predicador que se convirtio en dios "
        "y arrastro a su congregacion al abismo."
    )
    
    output_path = BASE_DIR / "output" / "test_elevenlabs.mp3"
    
    print(f"   Texto: {test_text[:60]}...")
    print(f"   Caracteres: {len(test_text)}")
    print(f"   Costo estimado: ${len(test_text)/1000 * 0.12:.4f}")
    print(f"   Voz: Josh")
    print()
    
    start = time.time()
    ok = generate_narration(test_text, output_path, voice="Josh")
    elapsed = time.time() - start
    
    if ok:
        size_kb = output_path.stat().st_size / 1024
        print(f"\n   [OK] Audio generado en {elapsed:.1f}s")
        print(f"   Archivo: {output_path}")
        print(f"   Tamano: {size_kb:.0f} KB")
        print(f"   Abrelo para escuchar la calidad!")
        return True
    else:
        print(f"\n   [FAIL] No se pudo generar el audio")
        return False


def test_luma():
    """Prueba Luma AI con 1 imagen existente."""
    print("\n" + "=" * 60)
    print("   TEST 2: Luma AI Image-to-Video")
    print("=" * 60)
    
    api_key = os.getenv("LUMA_API_KEY")
    if not api_key:
        print("   [SKIP] LUMA_API_KEY no configurada en .env")
        print("   Para obtener: https://lumalabs.ai/dream-machine/api/keys")
        return False
    
    imgbb_key = os.getenv("IMGBB_API_KEY")
    temp_host = os.getenv("TEMP_IMAGE_HOST")
    if not imgbb_key and not temp_host:
        print("   [SKIP] Necesitas configurar hosting de imagenes")
        print("   Opcion 1: IMGBB_API_KEY (gratis en imgbb.com)")
        print("   Opcion 2: TEMP_IMAGE_HOST (tu propio servidor)")
        return False
    
    # Buscar una imagen de prueba
    videos_dir = BASE_DIR / "output" / "videos"
    test_image = None
    
    if videos_dir.exists():
        for project_dir in videos_dir.iterdir():
            if not project_dir.is_dir():
                continue
            for subdir in ["images", "clips"]:
                img_dir = project_dir / subdir
                if img_dir.exists():
                    for img in sorted(img_dir.glob("scene_*.png")):
                        if img.stat().st_size > 5000:
                            test_image = img
                            break
                if test_image:
                    break
            if test_image:
                break
    
    if not test_image:
        print("   [SKIP] No se encontro imagen de prueba")
        print("   Genera un video primero con el pipeline normal")
        return False
    
    from luma_video import upload_image_to_temp, create_generation, poll_generation, download_video
    
    output_path = BASE_DIR / "output" / "test_luma.mp4"
    
    print(f"   Imagen: {test_image.name}")
    print(f"   Proyecto: {test_image.parent.parent.name}")
    print()
    
    start = time.time()
    
    # 1. Subir imagen
    print("   [1/3] Subiendo imagen...")
    image_url = upload_image_to_temp(test_image)
    if not image_url:
        print("   [FAIL] No se pudo subir la imagen")
        return False
    print(f"   URL: {image_url[:60]}...")
    
    # 2. Crear generacion
    print("   [2/3] Creando generacion en Luma...")
    gen_id = create_generation(
        image_url=image_url,
        prompt="Slow subtle push in, gentle atmospheric haze, cinematic lighting shifts",
        model="ray-flash-2"
    )
    if not gen_id:
        print("   [FAIL] No se pudo crear la generacion")
        return False
    
    # 3. Esperar y descargar
    print("   [3/3] Esperando video (puede tomar 1-3 min)...")
    result = poll_generation(gen_id, timeout_min=5)
    
    if result and result.get("video_url"):
        ok = download_video(result["video_url"], output_path)
        elapsed = time.time() - start
        
        if ok:
            size_mb = output_path.stat().st_size / (1024 * 1024)
            print(f"\n   [OK] Video generado en {elapsed:.1f}s")
            print(f"   Archivo: {output_path}")
            print(f"   Tamano: {size_mb:.1f} MB")
            print(f"   Abrelo para ver la calidad!")
            return True
    
    print(f"\n   [FAIL] No se pudo generar el video")
    return False


if __name__ == "__main__":
    print("=" * 60)
    print("   CONTENT FACTORY — Test de APIs Directas")
    print("=" * 60)
    
    results = {}
    
    # Test 1: ElevenLabs
    results["ElevenLabs TTS"] = test_elevenlabs()
    
    # Test 2: Luma
    results["Luma Video"] = test_luma()
    
    # Resumen
    print("\n" + "=" * 60)
    print("   RESUMEN")
    print("=" * 60)
    for name, passed in results.items():
        status = "[OK]" if passed else "[SKIP/FAIL]"
        print(f"   {status} {name}")
    
    # Mostrar que falta
    missing = []
    if not os.getenv("ELEVENLABS_API_KEY"):
        missing.append("ELEVENLABS_API_KEY")
    if not os.getenv("LUMA_API_KEY"):
        missing.append("LUMA_API_KEY")
    if not os.getenv("IMGBB_API_KEY") and not os.getenv("TEMP_IMAGE_HOST"):
        missing.append("IMGBB_API_KEY (o TEMP_IMAGE_HOST)")
    
    if missing:
        print(f"\n   Variables faltantes en .env:")
        for var in missing:
            print(f"   -> {var}")
    
    print("=" * 60)
