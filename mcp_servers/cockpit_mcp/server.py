import asyncio
import json
import websockets
import random
import os
import copy
import time
from datetime import datetime
import traceback
import httpx
from aiohttp import web
import aiohttp_cors

# --- Constants and Configuration ---
PROMPT_MODIFIERS = [
    "Be more direct.", "Use simpler language.", "Adopt a professional tone.",
    "Explain it like I'm five.", "Be more expressive and use emojis.",
    "Sound more empathetic.", "Focus on the key takeaways.", "Provide a step-by-step guide.",
    "Ensure the answer is factually accurate.", "Format the response as a list.",
    "Summarize the main point in one sentence.", "Add a historical context.",
    "Use a persuasive tone.", "Incorporate a compelling narrative.", "Cite sources.",
    "Be more concise and to the point.", "Expand on the previous point."
]
INITIAL_STATE_FILE = os.path.join(os.path.dirname(__file__), 'simulated_data.json')
# This lock ensures that only one simulation runs at a time globally.
simulation_lock = asyncio.Lock()

# --- Data Loading and State Management ---
def load_initial_state():
    """Loads the initial galaxy state from the JSON file."""
    with open(INITIAL_STATE_FILE, 'r') as f:
        return json.load(f)

# The global state of the universe
galaxies = load_initial_state()
clients = set()

# --- Image Proxy Logic ---
async def get_texture(request):
    theme = request.query.get('theme')
    item_id = request.query.get('id')

    if not theme or not item_id:
        return web.Response(status=400, text="Bad Request: Missing theme or id")

    theme_generators = {
        'cats': f"https://cataas.com/cat/cute/says/galaxy-agent?width=512&height=512&color=white&type=square&s=20&id={item_id}",
        'pokemon': f"https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/{(abs(hash(item_id)) % 898) + 1}.png",
    }

    image_url = theme_generators.get(theme)
    if not image_url:
        return web.Response(status=404, text="Not Found: Invalid theme")

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(image_url, timeout=15.0)
            resp.raise_for_status()  # Raise an exception for bad status codes
            
            headers = {'Content-Type': resp.headers.get('Content-Type', 'image/png')}
            return web.Response(body=resp.content, headers=headers)
        
        except httpx.RequestError as exc:
            print(f"An error occurred while requesting {exc.request.url!r}.")
            return web.Response(status=500, text=f"Error fetching image: {exc}")

async def handle_onboard(request):
    """Handles onboarding of a new agent."""
    try:
        data = await request.json()
        agent_id = data.get("id")
        
        if not agent_id:
            return web.Response(status=400, text="Bad Request: Missing agent id")

        # Create a new galaxy structure for the agent
        new_galaxy = {
            "id": agent_id,
            "name": data.get("name", "Unnamed Agent"),
            "position": [random.uniform(-100, 100), 0, random.uniform(-100, 100)],
            "theme": {"hue": random.random()},
            "status": "initializing",
            "status_message": "Onboarding complete. Awaiting first telemetry.",
            "config": {
                "apiUrl": data.get("apiUrl"),
                "authToken": data.get("authToken"),
                "opikMetrics": data.get("opikMetrics", [])
            },
            "planets": [],
            "comets": []
        }
        
        galaxies[agent_id] = new_galaxy

        # Persist the new state - THIS IS REMOVED TO PREVENT FILE I/O ERRORS
        # In a production system, this would write to a database, not a file.
        # with open(INITIAL_STATE_FILE, 'w') as f:
        #     json.dump(galaxies, f, indent=4)
        
        # Announce the update to all clients
        await broadcast_message({"type": "update", "galaxies": copy.deepcopy(galaxies)})

        return web.Response(status=200, text=f"Agent {agent_id} onboarded successfully.")

    except Exception as e:
        print(f"Onboarding error: {e}")
        traceback.print_exc()
        return web.Response(status=500, text="Internal Server Error during onboarding.")

# --- Frontend-driven Optimizer Endpoints ---

async def handle_optimizer_start(request):
    """Starts an optimization run by creating a 'comet'."""
    try:
        data = await request.json()
        galaxy_id = data.get("galaxy_id")
        planet_id = data.get("planet_id")

        galaxy = galaxies.get(galaxy_id)
        if not galaxy or not any(p['id'] == planet_id for p in galaxy.get('planets', [])):
            return web.Response(status=404, text="Galaxy or Planet not found")

        comet_id = f"comet-{int(time.time()*1000)}"
        new_comet = {
            "id": comet_id,
            "targetPlanetId": planet_id,
            "progress": 0,
            # Visual properties for the frontend
            "position": [galaxy['position'][0] + random.uniform(-30, 30), random.uniform(-5, 5), galaxy['position'][2] + random.uniform(-30, 30)],
            "trajectory": [random.uniform(-0.5, 0.5), random.uniform(-0.1, 0.1), random.uniform(-0.5, 0.5)]
        }

        if "comets" not in galaxy:
            galaxy["comets"] = []
        galaxy["comets"].append(new_comet)
        galaxy["status"] = "optimizing"
        
        await broadcast_message({"type": "update", "galaxies": copy.deepcopy(galaxies)})
        return web.json_response({"status": "success", "comet_id": comet_id})

    except Exception as e:
        print(f"Optimizer start error: {e}")
        return web.Response(status=500, text="Internal Server Error")

async def handle_optimizer_generate_variant(request):
    """Generates and evaluates a single new prompt variant."""
    try:
        data = await request.json()
        galaxy_id = data.get("galaxy_id")
        planet_id = data.get("planet_id")

        galaxy = galaxies.get(galaxy_id)
        planet = next((p for p in galaxy.get('planets', []) if p['id'] == planet_id), None)
        if not galaxy or not planet:
            return web.Response(status=404, text="Galaxy or Planet not found")
        
        base_variant = planet["deployedVersion"]
        metrics = galaxy.get("config", {}).get("opikMetrics", [])
        
        new_variant = generate_new_variant(base_variant["text"])
        new_variant["evaluation"] = evaluate_with_opik_judges(base_variant["evaluation"]["score"], metrics)
        
        planet["traceHistory"].insert(0, new_variant)
        if len(planet["traceHistory"]) > 15:
            planet["traceHistory"].pop()
            
        await broadcast_message({"type": "update", "galaxies": copy.deepcopy(galaxies)})
        return web.json_response({"status": "success", "variant": new_variant})

    except Exception as e:
        print(f"Generate variant error: {e}")
        return web.Response(status=500, text="Internal Server Error")

async def handle_optimizer_deploy_variant(request):
    """Deploys a specific variant from the trace history."""
    try:
        data = await request.json()
        galaxy_id = data.get("galaxy_id")
        planet_id = data.get("planet_id")
        variant_id = data.get("variant_id")

        galaxy = galaxies.get(galaxy_id)
        planet = next((p for p in galaxy.get('planets', []) if p['id'] == planet_id), None)
        if not galaxy or not planet:
            return web.Response(status=404, text="Galaxy or Planet not found")

        variant_to_deploy = next((v for v in planet.get('traceHistory', []) if v['id'] == variant_id), None)
        if not variant_to_deploy:
            return web.Response(status=404, text="Variant not found in trace history")

        planet["deployedVersion"] = variant_to_deploy
        
        # Optionally, end the optimization run after a successful deployment
        galaxy["comets"] = []
        galaxy["status"] = "active"

        await broadcast_message({"type": "update", "galaxies": copy.deepcopy(galaxies)})
        return web.json_response({"status": "success", "deployed_variant_id": variant_id})

    except Exception as e:
        print(f"Deploy variant error: {e}")
        return web.Response(status=500, text="Internal Server Error")

async def handle_delete_agent(request):
    """Deletes an agent (galaxy) from the simulation."""
    try:
        agent_id = request.match_info.get('agent_id')
        if not agent_id:
            return web.Response(status=400, text="Bad Request: Missing agent_id")

        if agent_id in galaxies:
            del galaxies[agent_id]
            print(f"Agent {agent_id} deleted.")
            
            await broadcast_message({"type": "update", "galaxies": copy.deepcopy(galaxies)})
            return web.json_response({"status": "success", "message": f"Agent {agent_id} deleted."})
        else:
            return web.Response(status=404, text=f"Not Found: Agent {agent_id} not found.")

    except Exception as e:
        print(f"Delete agent error: {e}")
        return web.Response(status=500, text="Internal Server Error")

async def handle_update_position(request):
    """Updates the position of an agent (galaxy)."""
    try:
        agent_id = request.match_info.get('agent_id')
        if not agent_id:
            return web.Response(status=400, text="Bad Request: Missing agent_id")

        data = await request.json()
        new_position = data.get('position')
        
        if not new_position or len(new_position) != 3:
            return web.Response(status=400, text="Bad Request: Invalid position format")

        if agent_id in galaxies:
            galaxies[agent_id]['position'] = new_position
            print(f"Agent {agent_id} position updated to {new_position}")
            
            await broadcast_message({"type": "update", "galaxies": copy.deepcopy(galaxies)})
            return web.json_response({"status": "success", "position": new_position})
        else:
            return web.Response(status=404, text=f"Not Found: Agent {agent_id} not found.")

    except Exception as e:
        print(f"Update position error: {e}")
        return web.Response(status=500, text="Internal Server Error")

async def handle_update_metric_mapping(request):
    """Updates the metric mapping for an agent (galaxy)."""
    try:
        agent_id = request.match_info.get('agent_id')
        if not agent_id:
            return web.Response(status=400, text="Bad Request: Missing agent_id")

        data = await request.json()
        metric_mapping = data.get('metricMapping')
        
        if not metric_mapping:
            return web.Response(status=400, text="Bad Request: Missing metricMapping")

        if agent_id in galaxies:
            if 'config' not in galaxies[agent_id]:
                galaxies[agent_id]['config'] = {}
            galaxies[agent_id]['config']['metricMapping'] = metric_mapping
            print(f"Agent {agent_id} metric mapping updated: {metric_mapping}")
            
            await broadcast_message({"type": "update", "galaxies": copy.deepcopy(galaxies)})
            return web.json_response({"status": "success", "metricMapping": metric_mapping})
        else:
            return web.Response(status=404, text=f"Not Found: Agent {agent_id} not found.")

    except Exception as e:
        print(f"Update metric mapping error: {e}")
        return web.Response(status=500, text="Internal Server Error")

# --- Mock Opik SDK Functions ---
def evaluate_with_opik_judges(base_score, metrics_to_evaluate):
    """Simulates opik's evaluation suite for a prompt variant."""
    score_multiplier = random.uniform(0.9, 1.1)
    new_score = min(round(base_score * score_multiplier, 2), 0.99)
    
    return {
        "score": new_score,
        "factuality": round(random.uniform(0.85, 0.99), 2),
        "hallucination": round(random.uniform(0.01, 0.15), 2),
        "speed": random.randint(100, 500)
    }

def generate_new_variant(base_text):
    """Simulates Opik's few-shot prompt tuning."""
    modifier = random.choice(PROMPT_MODIFIERS)
    new_text = f"{base_text} Additional instruction: {modifier}"
    new_id = f"v{random.randint(10000, 99999)}"
    return {"id": new_id, "text": new_text, "timestamp": datetime.now().isoformat()}

# --- Simulation Logic ---
async def telemetry_ingestion_loop():
    """
    Periodically simulates fetching telemetry from onboarded agents,
    """
    while True:
        await asyncio.sleep(2)  # Update every 2 seconds
        if galaxies and random.random() < 0.7:
            try:
                galaxy_id = random.choice(list(galaxies.keys()))
                target_galaxy = galaxies[galaxy_id]
                if target_galaxy.get("planets"):
                    planet_id = random.choice(range(len(target_galaxy["planets"])))
                    target_planet = target_galaxy["planets"][planet_id]
                    current_score = target_planet["deployedVersion"]["evaluation"]["score"]
                    new_score = current_score + random.uniform(-0.05, 0.05)
                    new_score = max(0.1, min(0.99, new_score))
                    target_planet["deployedVersion"]["evaluation"]["score"] = new_score

                    if new_score > current_score:
                        target_planet["deployedVersion"] = target_planet["traceHistory"][0]
                        print(f"New version deployed for {target_planet['name']} with score {new_score:.2f}")

            except (KeyError, IndexError) as e:
                print(f"Skipping telemetry ingestion tick due to data structure error: {e}")

        # Comment out the broadcast to prevent overriding dragged positions
        # await broadcast_state()

async def broadcast_state():
    """Broadcasts the current galaxy state to all connected clients."""
    if clients:
        # Each client gets a slightly randomized version of the state
        tasks = []
        for client in clients:
            # Simulate comets or other dynamic elements
            galaxies_with_comets = copy.deepcopy(galaxies)
            for galaxy_id, galaxy_data in galaxies_with_comets.items():
                if galaxy_data['status'] == 'optimizing' and random.random() < 0.2:
                    if 'comets' not in galaxy_data:
                        galaxy_data['comets'] = []
                    
                    start_pos = [random.uniform(-50, 50), random.uniform(-10, 10), random.uniform(-50, 50)]
                    end_pos = [random.uniform(-50, 50), random.uniform(-10, 10), random.uniform(-50, 50)]
                    
                    galaxy_data['comets'].append({
                        "id": f"comet-{int(time.time()*1000)}",
                        "from": start_pos,
                        "to": end_pos,
                        "speed": random.uniform(0.5, 2.0)
                    })

            message = json.dumps({
                "type": "update",
                "galaxies": galaxies_with_comets
            })
            tasks.append(client.send(message))
        await asyncio.gather(*tasks)

async def handle_telemetry(request):
    """
    Handles telemetry data ingestion from agents.
    This is the integrated version of the telemetry endpoint.
    """
    try:
        data = await request.json()
        agent_id = data.get("agent_id")
        payload = data.get("payload")

        if not agent_id or not payload:
            print(f"TELEMETRY VALIDATION FAILED: Missing agent_id or payload. Data: {data}")
            return web.Response(status=400, text="Bad Request: Missing agent_id or payload")
        
        if agent_id not in galaxies:
            print(f"TELEMETRY WARNING: Received data for unknown agent '{agent_id}'")
            return web.Response(status=404, text=f"Not Found: Agent {agent_id} is not onboarded.")

        galaxy = galaxies[agent_id]
        print(f"TELEMETRY RECEIVED for Agent '{galaxy['name']}': {json.dumps(payload, indent=2)}")

        # --- Create a default planet if this is the first telemetry for the agent ---
        if not galaxy.get("planets"):
            galaxy["planets"] = [{
                "id": f"{agent_id}-p1",
                "name": "Primary Prompt",
                "status": "deployed",
                "deployedVersion": {
                    "id": "v1", "text": "Initial prompt from live telemetry.",
                    "evaluation": {"score": 0.5}, "timestamp": datetime.now().isoformat()
                },
                "traceHistory": []
            }]
            galaxy["status"] = "active"

        # --- Update the planet's state from the payload ---
        planet = galaxy["planets"][0]
        if "score" in payload:
            planet["deployedVersion"]["evaluation"]["score"] = payload["score"]
        
        galaxy['status_message'] = f"Latency: {payload.get('latency_ms', 'N/A')}ms | Errors: {payload.get('error_count', 'N/A')}"
        
        # Broadcast the update to all clients
        await broadcast_message({"type": "update", "galaxies": copy.deepcopy(galaxies)})
        
        return web.Response(status=200, text="Telemetry received successfully.")

    except json.JSONDecodeError:
        return web.Response(status=400, text="Bad Request: Invalid JSON format.")
    except Exception as e:
        print(f"TELEMETRY ERROR: {e}")
        traceback.print_exc()
        return web.Response(status=500, text="Internal Server Error processing telemetry.")

# --- WebSocket Handling ---
async def broadcast_message(message):
    """Sends a message to all connected clients."""
    if clients:
        # Use asyncio.gather to run all send tasks concurrently
        await asyncio.gather(*[client.send(json.dumps(message)) for client in clients])

async def client_handler(websocket):
    """Handles WebSocket client connections."""
    clients.add(websocket)
    print(f"Client connected. Total clients: {len(clients)}")
    
    try:
        # Send initial state immediately
        await websocket.send(json.dumps({"type": "init", "galaxies": galaxies}))

        async for message in websocket:
            # This part is intentionally left blank for this simulation
            pass
            
    except websockets.exceptions.ConnectionClosed:
        print("Client connection closed.")
    finally:
        clients.remove(websocket)
        print(f"Client disconnected. Total clients: {len(clients)}")

# --- Main Entry Point ---
async def main():
    """Starts the WebSocket and HTTP servers."""
    # --- HTTP Server Setup ---
    app = web.Application()
    app.router.add_get("/api/texture", get_texture)
    app.router.add_post("/api/onboard", handle_onboard)
    app.router.add_post("/api/telemetry", handle_telemetry)
    app.router.add_post("/api/optimizer/start", handle_optimizer_start)
    app.router.add_post("/api/optimizer/generate_variant", handle_optimizer_generate_variant)
    app.router.add_post("/api/optimizer/deploy_variant", handle_optimizer_deploy_variant)
    app.router.add_delete("/api/agent/{agent_id}", handle_delete_agent)
    app.router.add_put("/api/agent/{agent_id}/position", handle_update_position)
    app.router.add_put("/api/agent/{agent_id}/metric_mapping", handle_update_metric_mapping)
    
    # Configure CORS
    cors = aiohttp_cors.setup(app, defaults={
        "*": aiohttp_cors.ResourceOptions(
            allow_credentials=True,
            expose_headers="*",
            allow_headers="*",
            allow_methods="*",
        )
    })
    for route in list(app.router.routes()):
        cors.add(route)
        
    http_runner = web.AppRunner(app)
    await http_runner.setup()
    http_site = web.TCPSite(http_runner, '0.0.0.0', 8080)
    
    # --- WebSocket Server Setup ---
    websocket_server = await websockets.serve(client_handler, "0.0.0.0", 8765)

    print("AI Cockpit MCP Server started:")
    print("  - WebSocket on ws://0.0.0.0:8765")
    print("  - HTTP API on http://0.0.0.0:8080")

    # ✅ Keeps both servers running
    await asyncio.gather(
        http_site.start(),
        websocket_server.wait_closed()
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Server shutting down.")
