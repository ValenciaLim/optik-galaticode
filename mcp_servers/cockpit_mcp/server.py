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
from typing import Set, Dict, Any

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
galaxies: Dict[str, Any] = load_initial_state()
clients: Set[web.WebSocketResponse] = set()
# In-memory store for active optimization tasks
active_optimizations: Dict[str, asyncio.Task] = {} # {planet_id: asyncio.Task}

# --- Image Proxy Logic ---
async def get_texture(request: web.Request) -> web.Response:
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

async def handle_onboard(request: web.Request) -> web.Response:
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
        
        # Announce the update to all clients
        await broadcast_message({"type": "update", "payload": {"galaxies": copy.deepcopy(galaxies)}})

        return web.Response(status=200, text=f"Agent {agent_id} onboarded successfully.")

    except Exception as e:
        print(f"Onboarding error: {e}")
        traceback.print_exc()
        return web.Response(status=500, text="Internal Server Error during onboarding.")

def _update_galaxy_status_based_on_planets(galaxy: Dict[str, Any]) -> None:
    """
    Recalculates the galaxy's status based on the average score of its planets.
    This is called when an optimization completes or is cancelled.
    """
    if galaxy.get("comets"):
        galaxy["status"] = "optimizing"
        return

    planets = galaxy.get("planets", [])
    if not planets:
        galaxy["status"] = "stable"
        return

    total_score = sum(p.get("deployedVersion", {}).get("evaluation", {}).get("score", 0) for p in planets)
    average_score = total_score / len(planets)

    if average_score < 0.6:
        galaxy["status"] = "critical"
    else:
        galaxy["status"] = "stable"

# --- Frontend-driven Optimizer Endpoints ---

async def handle_optimizer_start(request: web.Request) -> web.Response:
    """
    Starts a continuous optimization background task for a given planet.
    """
    try:
        data = await request.json()
        galaxy_id = data.get("galaxy_id")
        planet_id = data.get("planet_id")
        optimizer = data.get("optimizer", "Few-shot Bayesian")
        score_threshold = data.get("score_threshold", 0.95)

        if planet_id in active_optimizations:
            return web.json_response({"status": "already_running"}, status=409)

        galaxy = galaxies.get(galaxy_id)
        if not galaxy:
            return web.Response(status=404, text="Galaxy not found")
        planet = next((p for p in galaxy.get('planets', []) if p['id'] == planet_id), None)
        if not planet:
            return web.Response(status=404, text="Planet not found")

        # Start the background task
        task = asyncio.create_task(
            run_continuous_optimization(galaxy_id, planet_id, optimizer, score_threshold)
        )
        active_optimizations[planet_id] = task

        # Update galaxy status and broadcast
        galaxy["status"] = "optimizing"
        await broadcast_message({"type": "update", "payload": {"galaxies": copy.deepcopy(galaxies)}})
        
        return web.json_response({"status": "success", "message": f"Optimization started for planet {planet_id}."})

    except Exception as e:
        print(f"Optimizer start error: {e}")
        traceback.print_exc()
        return web.Response(status=500, text="Internal Server Error")

async def handle_optimizer_generate_variant(request: web.Request) -> web.Response:
    """Generates and evaluates a single new prompt variant."""
    try:
        data = await request.json()
        galaxy_id = data.get("galaxy_id")
        planet_id = data.get("planet_id")

        galaxy = galaxies.get(galaxy_id)
        if not galaxy:
            return web.Response(status=404, text="Galaxy or Planet not found")
        planet = next((p for p in galaxy.get('planets', []) if p['id'] == planet_id), None)
        if not planet:
            return web.Response(status=404, text="Galaxy or Planet not found")
        
        base_variant = planet["deployedVersion"]
        metrics = galaxy.get("config", {}).get("opikMetrics", [])
        
        new_variant = generate_new_variant(base_variant["text"])
        new_variant["evaluation"] = evaluate_with_opik_judges(base_variant["evaluation"]["score"], metrics)
        
        planet["traceHistory"].insert(0, new_variant)
        if len(planet["traceHistory"]) > 15:
            planet["traceHistory"].pop()
            
        await broadcast_message({"type": "update", "payload": {"galaxies": copy.deepcopy(galaxies)}})
        return web.json_response({"status": "success", "variant": new_variant})

    except Exception as e:
        print(f"Generate variant error: {e}")
        return web.Response(status=500, text="Internal Server Error")

async def handle_optimizer_deploy_variant(request: web.Request) -> web.Response:
    """Deploys a specific variant from the trace history."""
    try:
        data = await request.json()
        galaxy_id = data.get("galaxy_id")
        planet_id = data.get("planet_id")
        variant_id = data.get("variant_id")

        galaxy = galaxies.get(galaxy_id)
        if not galaxy:
            return web.Response(status=404, text="Galaxy or Planet not found")
        planet = next((p for p in galaxy.get('planets', []) if p['id'] == planet_id), None)
        if not planet:
            return web.Response(status=404, text="Galaxy or Planet not found")

        variant_to_deploy = next((v for v in planet.get('traceHistory', []) if v['id'] == variant_id), None)
        if not variant_to_deploy:
            return web.Response(status=404, text="Variant not found in trace history")

        planet["deployedVersion"] = variant_to_deploy
        
        # End optimization for the planet and check if the galaxy is still optimizing
        galaxy["comets"] = [c for c in galaxy.get("comets", []) if c.get("targetPlanetId") != planet_id]
        _update_galaxy_status_based_on_planets(galaxy)

        await broadcast_message({"type": "update", "payload": {"galaxies": copy.deepcopy(galaxies)}})
        return web.json_response({"status": "success", "deployed_variant_id": variant_id})

    except Exception as e:
        print(f"Deploy variant error: {e}")
        return web.Response(status=500, text="Internal Server Error")

async def handle_optimizer_stop(request: web.Request) -> web.Response:
    """Stops a continuous optimization run for a given planet."""
    try:
        data = await request.json()
        planet_id = data.get("planet_id")

        task = active_optimizations.get(planet_id)
        if task:
            task.cancel()
            # The task's finally block will handle cleanup
            return web.json_response({"status": "success", "message": f"Optimization stopping for planet {planet_id}."})
        else:
            return web.Response(status=404, text="No active optimization found for this planet.")

    except Exception as e:
        print(f"Optimizer stop error: {e}")
        return web.Response(status=500, text="Internal Server Error")

async def handle_delete_agent(request: web.Request) -> web.Response:
    """Deletes an agent (galaxy) from the simulation."""
    agent_id = request.match_info.get('agent_id')
    if not agent_id:
        return web.Response(status=400, text="Bad Request: Missing agent_id")

    if agent_id in galaxies:
        del galaxies[agent_id]
        # Persist changes
        # ... (removed for simplicity)
        await broadcast_message({"type": "update", "payload": {"galaxies": copy.deepcopy(galaxies)}})
        return web.Response(status=200, text=f"Agent {agent_id} deleted.")
    else:
        return web.Response(status=404, text="Agent not found.")

async def handle_update_position(request: web.Request) -> web.Response:
    """Updates the 3D position of a galaxy."""
    try:
        agent_id = request.match_info.get('agent_id')
        if not agent_id:
            return web.Response(status=400, text="Bad Request: Missing agent_id")
        
        data = await request.json()
        new_position = data.get('position')
        
        if agent_id in galaxies:
            galaxies[agent_id]['position'] = new_position
            # No broadcast needed, client handles optimistic update
            return web.Response(status=200)
        else:
            return web.Response(status=404, text="Agent not found")
    except Exception as e:
        print(f"Update position error: {e}")
        return web.Response(status=500, text="Internal Server Error")

async def handle_update_metric_mapping(request: web.Request) -> web.Response:
    """Updates the metric mapping for a galaxy."""
    try:
        agent_id = request.match_info.get('agent_id')
        if not agent_id:
            return web.Response(status=400, text="Bad Request: Missing agent_id")

        data = await request.json()
        new_mapping = data.get('metricMapping')

        if agent_id in galaxies:
            if 'config' not in galaxies[agent_id]:
                galaxies[agent_id]['config'] = {}
            galaxies[agent_id]['config']['metricMapping'] = new_mapping
            await broadcast_message({"type": "update", "payload": {"galaxies": copy.deepcopy(galaxies)}})
            return web.Response(status=200)
        else:
            return web.Response(status=404, text="Agent not found")
    except Exception as e:
        print(f"Error updating metric mapping: {e}")
        return web.Response(status=500, text="Internal Server Error")


async def handle_toggle_planet_status(request: web.Request) -> web.Response:
    """Toggles a planet's status between 'active' and 'inactive'."""
    try:
        agent_id = request.match_info.get('agent_id')
        planet_id = request.match_info.get('planet_id')
        
        if not agent_id or not planet_id:
            return web.Response(status=400, text="Bad Request: Missing agent or planet ID")

        data = await request.json()
        new_status = data.get('status')

        if new_status not in ['active', 'inactive']:
            return web.Response(status=400, text="Bad Request: Invalid status")

        galaxy = galaxies.get(agent_id)
        if not galaxy:
            return web.Response(status=404, text="Agent not found")
        
        planet = next((p for p in galaxy.get('planets', []) if p['id'] == planet_id), None)
        if not planet:
            return web.Response(status=404, text="Planet not found")

        planet['status'] = new_status
        await broadcast_message({"type": "update", "payload": {"galaxies": copy.deepcopy(galaxies)}})
        return web.json_response({"status": "success"})
    except Exception as e:
        print(f"Error toggling planet status: {e}")
        return web.Response(status=500, text="Internal Server Error")


def evaluate_with_opik_judges(base_score: float, metrics_to_evaluate: list) -> Dict[str, Any]:
    """
    Simulates calling Opik judges for a more comprehensive evaluation.
    This is a placeholder for a real-world, complex evaluation system.
    """
    score_multiplier = random.uniform(0.8, 1.2) # Simulate variability
    new_score = max(0, min(1, base_score * score_multiplier))
    
    return {
        "score": new_score,
        "factuality": random.choice(["Meets Expectations", "Exceeds Expectations", "Needs Improvement"]),
        "hallucination": "Detected" if random.random() < 0.1 else "Not Detected",
        "speed": int(random.uniform(50, 500)),
    }


def generate_new_variant(base_text: str) -> Dict[str, Any]:
    """Generates a new prompt variant by applying a random modification."""
    modifier = random.choice(PROMPT_MODIFIERS)
    new_text = f"{base_text} [{modifier}]"
    
    return {
        "id": f"var_{int(time.time() * 1000)}_{random.randint(1000, 9999)}",
        "text": new_text,
        "evaluation": {},
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "isDeployed": False,
    }

def generate_new_planet(galaxy_id: str) -> Dict[str, Any]:
    """Generates a new planet with default values."""
    planet_id = f"p_{int(time.time() * 1000)}_{random.randint(1000, 9999)}"
    return {
        "id": planet_id,
        "name": f"Planet-{random.choice(['Alpha', 'Beta', 'Gamma', 'Delta'])}-{random.randint(100, 999)}",
        "status": "active",
        "orbitRadius": random.uniform(10, 40),
        "deployedVersion": {
            "id": f"v_{int(time.time() * 1000)}",
            "text": "Initial default prompt.",
            "evaluation": {
                "score": random.uniform(0.5, 0.8),
                "factuality": "N/A",
                "hallucination": "N/A",
                "speed": 0,
            },
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "isDeployed": True,
        },
        "traceHistory": [],
    }

async def run_continuous_optimization(galaxy_id: str, planet_id: str, optimizer: str, score_threshold: float):
    """
    A background task that continuously generates and evaluates variants
    for a given planet until it's cancelled or a score threshold is met.
    """
    try:
        while True:
            galaxy = galaxies.get(galaxy_id)
            if not galaxy:
                print(f"Optimization ended: Galaxy {galaxy_id} not found.")
                break
                
            planet = next((p for p in galaxy.get('planets', []) if p['id'] == planet_id), None)
            if not planet:
                print(f"Optimization ended: Planet {planet_id} not found.")
                break
            
            base_variant = planet["deployedVersion"]
            metrics = galaxy.get("config", {}).get("opikMetrics", [])
            
            new_variant = generate_new_variant(base_variant["text"])
            new_variant["evaluation"] = evaluate_with_opik_judges(base_variant["evaluation"]["score"], metrics)

            # Add to the start of the history
            planet["traceHistory"].insert(0, new_variant)
            if len(planet["traceHistory"]) > 15:
                planet["traceHistory"].pop()

            # Broadcast update with the new trace entry
            await broadcast_message({
                "type": "update",
                "payload": {
                    "galaxies": copy.deepcopy(galaxies),
                    "optimizing_planets": list(active_optimizations.keys())
                }
            })

            # Check for score threshold
            if new_variant["evaluation"]["score"] >= score_threshold:
                print(f"Score threshold {score_threshold} reached for planet {planet_id}. Stopping optimization.")
                break # Exit the loop, which will end the task

            # Wait a bit before the next iteration
            await asyncio.sleep(random.uniform(3, 7))

    except asyncio.CancelledError:
        print(f"Optimization for {planet_id} was cancelled.")
        
    finally:
        # This block executes on cancellation or completion
        print(f"Ending optimization for {planet_id}.")
        if planet_id in active_optimizations:
            del active_optimizations[planet_id]
        
        # Update the galaxy status and broadcast the final state
        galaxy = galaxies.get(galaxy_id)
        if galaxy:
            _update_galaxy_status_based_on_planets(galaxy)
            await broadcast_message({
                "type": "update",
                "payload": {
                    "galaxies": copy.deepcopy(galaxies),
                    "optimizing_planets": list(active_optimizations.keys())
                }
            })


async def telemetry_ingestion_loop():
    """Simulates receiving periodic telemetry data for all agents."""
    while True:
        try:
            # Wait for a random interval before the next telemetry push
            await asyncio.sleep(random.uniform(15, 30))
            
            # This lock prevents race conditions if multiple background tasks modify the state
            async with simulation_lock:
                print("Simulating telemetry data ingestion...")
                
                for galaxy in galaxies.values():
                    if not galaxy.get("planets"):
                        # If no planets, maybe create one
                        if random.random() < 0.2:
                            new_planet = generate_new_planet(galaxy["id"])
                            galaxy["planets"].append(new_planet)
                            print(f"New planet '{new_planet['name']}' discovered in {galaxy['name']}.")

                    for planet in galaxy.get("planets", []):
                        # Randomly degrade or improve the score
                        if random.random() < 0.3:
                            score_change = random.uniform(-0.15, 0.08)
                            current_score = planet["deployedVersion"]["evaluation"].get("score", 0.7)
                            new_score = max(0, min(1, current_score + score_change))
                            planet["deployedVersion"]["evaluation"]["score"] = new_score
                            print(f"Score for planet '{planet['name']}' in {galaxy['name']} changed to {new_score:.2f}")

                # After all updates, broadcast the new state
                await broadcast_message({
                    "type": "update",
                    "payload": {
                        "galaxies": copy.deepcopy(galaxies),
                        "optimizing_planets": list(active_optimizations.keys())
                    }
                })

        except Exception as e:
            print(f"Error in telemetry loop: {e}")
            traceback.print_exc()


async def handle_telemetry(request: web.Request) -> web.Response:
    """
    Handles incoming telemetry data from agents.
    This would be the primary way the simulation state is updated in a real system.
    """
    try:
        data = await request.json()
        agent_id = data.get("agent_id")
        
        galaxy = galaxies.get(agent_id)
        if not galaxy:
            return web.Response(status=404, text=f"Agent '{agent_id}' not found.")

        # This lock is crucial to prevent multiple telemetry updates from interfering
        async with simulation_lock:
            # Update planets based on telemetry
            telemetry_planets = data.get("planets", [])
            existing_planets = {p["id"]: p for p in galaxy.get("planets", [])}

            for tel_planet in telemetry_planets:
                planet_id = tel_planet["id"]
                if planet_id in existing_planets:
                    # Update existing planet's deployed version
                    existing_planet = existing_planets[planet_id]
                    existing_planet["name"] = tel_planet.get("name", existing_planet["name"])
                    
                    # Update deployed version if telemetry contains it
                    if "deployedVersion" in tel_planet:
                        existing_planet["deployedVersion"] = tel_planet["deployedVersion"]
                else:
                    # Onboard a new planet
                    new_planet = {
                        "id": planet_id,
                        "name": tel_planet.get("name", "Unnamed Planet"),
                        "status": "active",
                        "orbitRadius": random.uniform(10, 40),
                        "deployedVersion": tel_planet.get("deployedVersion", {}),
                        "traceHistory": []
                    }
                    galaxy.setdefault("planets", []).append(new_planet)
            
            _update_galaxy_status_based_on_planets(galaxy)
            
            # Broadcast the changes to all connected clients
            await broadcast_message({
                "type": "update",
                "payload": {
                    "galaxies": {agent_id: copy.deepcopy(galaxy)},
                    "optimizing_planets": list(active_optimizations.keys())
                }
            })

        return web.Response(status=200, text="Telemetry received.")
        
    except Exception as e:
        print(f"Telemetry error: {e}")
        traceback.print_exc()
        return web.Response(status=500, text="Internal Server Error")


async def broadcast_message(message: Dict[str, Any]):
    """Sends a JSON message to all connected clients."""
    if clients:
        # Use asyncio.gather to send messages concurrently, handling potential errors
        tasks = [client.send_json(message) for client in clients]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for result in results:
            if isinstance(result, Exception):
                print(f"Error broadcasting message: {result}")

async def main():
    """Sets up the web server and starts the simulation loops."""
    # --- Background tasks ---
    asyncio.create_task(telemetry_ingestion_loop())

    # --- Web server setup ---
    app = web.Application()
    
    # Configure CORS
    cors = aiohttp_cors.setup(app, defaults={
        "*": aiohttp_cors.ResourceOptions(
            allow_credentials=True,
            expose_headers="*",
            allow_headers="*",
            allow_methods="*", # Allow all methods including DELETE
        )
    })

    # --- HTTP Routes ---
    app.router.add_get('/api/texture', get_texture)
    app.router.add_post('/api/onboard', handle_onboard)
    app.router.add_post('/api/optimizer/start', handle_optimizer_start)
    app.router.add_post('/api/optimizer/stop', handle_optimizer_stop)
    app.router.add_post('/api/optimizer/variant/generate', handle_optimizer_generate_variant)
    app.router.add_post('/api/optimizer/variant/deploy', handle_optimizer_deploy_variant)
    app.router.add_post('/api/telemetry', handle_telemetry)
    app.router.add_delete('/api/agent/{agent_id}', handle_delete_agent)
    app.router.add_put('/api/agent/{agent_id}/position', handle_update_position)
    app.router.add_put('/api/agent/{agent_id}/config/metrics', handle_update_metric_mapping)
    app.router.add_put('/api/agent/{agent_id}/planet/{planet_id}/status', handle_toggle_planet_status)

    # Apply CORS to all routes
    for route in list(app.router.routes()):
        cors.add(route)

    # --- WebSocket Server ---
    async def websocket_handler_wrapper(request):
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        
        clients.add(ws) 
        try:
            await ws.send_json({
                "type": "update",
                "payload": {
                    "galaxies": copy.deepcopy(galaxies),
                    "optimizing_planets": list(active_optimizations.keys())
                }
            })

            async for msg in ws:
                if msg.type == web.WSMsgType.TEXT:
                    message = json.loads(msg.data)
                    if message['type'] == 'deploy_variant':
                        payload = message.get('payload', {})
                        galaxy_id = payload.get('galaxyId')
                        planet_id = payload.get('planetId')
                        variant = payload.get('variant')

                        if all([galaxy_id, planet_id, variant]):
                            galaxy = galaxies.get(galaxy_id)
                            if not galaxy:
                                continue
                            planet = next((p for p in galaxy.get('planets', []) if p['id'] == planet_id), None)

                            if planet:
                                old_deployed = planet.get("deployedVersion")
                                if old_deployed:
                                    old_deployed_copy = copy.deepcopy(old_deployed)
                                    old_deployed_copy['isDeployed'] = False
                                    if not any(t['id'] == old_deployed_copy['id'] for t in planet.get('traceHistory', [])):
                                        planet.setdefault('traceHistory', []).insert(0, old_deployed_copy)
                                
                                new_deployed = copy.deepcopy(variant)
                                new_deployed['isDeployed'] = True
                                planet['deployedVersion'] = new_deployed
                                planet['traceHistory'] = [t for t in planet.get('traceHistory', []) if t['id'] != new_deployed['id']]
                                
                                await broadcast_message({
                                    "type": "update",
                                    "payload": {"galaxies": copy.deepcopy(galaxies), "optimizing_planets": list(active_optimizations.keys())}
                                })
                elif msg.type == web.WSMsgType.ERROR:
                    print(f'WebSocket connection closed with exception {ws.exception()}')
        
        finally:
            if ws in clients:
                clients.remove(ws)
        
        return ws


    app.router.add_get('/ws', websocket_handler_wrapper)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, 'localhost', 8080)
    
    print("🚀 GalactiCode MCP Server is running on http://localhost:8080")
    print("📡 WebSocket endpoint is ws://localhost:8080/ws")
    await site.start()

    await asyncio.Event().wait()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Server shutting down.")
