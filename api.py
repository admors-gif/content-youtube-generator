from fastapi import FastAPI, BackgroundTasks, Request
import subprocess
import os

app = FastAPI(title="Content Factory API")

@app.get("/")
def health_check():
    return {"status": "online", "service": "Content Factory API"}

@app.post("/generate")
async def trigger_generation(request: Request, background_tasks: BackgroundTasks):
    data = await request.json()
    topic = data.get("topic")
    agent_file = data.get("agentFile", "agent_erotico_historico.md")
    project_id = data.get("projectId")
    
    if not topic:
        return {"status": "error", "message": "Missing 'topic' in request body"}

    # Ejecutar en segundo plano para no dejar colgada la petición HTTP a n8n
    background_tasks.add_task(run_script, topic, agent_file, project_id)
    
    return {
        "status": "accepted", 
        "message": f"Generation started for '{topic}' with agent '{agent_file}' (Project: {project_id})"
    }

def run_script(topic, agent_file, project_id):
    print(f"🚀 [API] Starting background job for '{topic}' with '{agent_file}' (Project: {project_id})...")
    try:
        # Ejecutamos el script igual que en consola
        args = ["python", "scripts/generate_content.py", "--agent", agent_file]
        if project_id:
            args.extend(["--project-id", project_id])
        args.append(topic)
        
        process = subprocess.run(
            args,
            check=False,
            capture_output=True,
            text=True
        )
        print("✅ [API] Script finished.")
        print("--- STDOUT ---")
        print(process.stdout)
        if process.stderr:
            print("--- STDERR ---")
            print(process.stderr)
    except Exception as e:
        print(f"❌ [API] Error running script: {e}")
