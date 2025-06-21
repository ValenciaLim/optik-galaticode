import asyncio
import json
import websockets
import random
import os
import copy
import time
from datetime import datetime

PROMPT_MODIFIERS = [
    "Be more direct.", "Use simpler language.", "Adopt a professional tone.",
    "Explain it like I'm five.", "Be more expressive and use emojis.",
    "Sound more empathetic.", "Focus on the key takeaways.", "Provide a step-by-step guide.",
    "Ensure the answer is factually accurate.", "Format the response as a list.",
    "Summarize the main point in one sentence.", "Add a historical context."
]

def create_initial_version(text, score):
    return {
        "id": f"v{random.randint(1000, 9999)}",
        "text": text,
        "evaluationScore": score,
        "telemetry": {"latency": f"{random.randint(80, 250)}ms", "cost": f""},
        "timestamp": datetime.now().isoformat()
    }

galaxies = {
    "galaxy-alpha": {
        "id": "galaxy-alpha",
        "name": "E-commerce Support Agent",
        "position": [-50, 0, 0],
        "theme": {"hue": 0.6},
        "planets": [
            {
                "id": "planet_intent",
                "name": "Intent Classifier",
                "position": [10, 0, 0],
                "orbitRadius": 10,
                "status": "deployed",
                "deployedVersion": create_initial_version("Classify user intent for an e-commerce query.", 0.92),
                "traceHistory": [],
                "isOptimizing": False
            },
            {
                "id": "planet_retrieval",
                "name": "Product Retriever",
                "position": [0, 0, 16],
                "orbitRadius": 16,
                "status": "testing",
                "deployedVersion": create_initial_version("Retrieve relevant products based on the classified intent.", 0.85),
                "traceHistory": [],
                "isOptimizing": False
            },
            {
                "id": "planet_generator",
                "name": "Answer Generator",
                "position": [-22, 0, 0],
                "orbitRadius": 22,
                "status": "deployed",
                "deployedVersion": create_initial_version("Generate a helpful response incorporating product details.", 0.88),
                "traceHistory": [],
                "isOptimizing": False
            }
        ],
        "config": {
            "activeOptimizer": "Evolutionary Strategy",
            "evaluationMetrics": ["Score", "Toxicity", "Latency"]
        }
    },
    "galaxy-beta": {
        "id": "galaxy-beta",
        "name": "Developer Assistant Agent",
        "position": [50, 0, 0],
        "theme": {"hue": 0.1},
        "planets": [
            {
                "id": "planet_code_gen",
                "name": "Code Generator",
                "position": [12, 0, 0],
                "orbitRadius": 12,
                "status": "deployed",
                "deployedVersion": create_initial_version("Generate a Python function based on the user's request.", 0.95),
                "traceHistory": [],
                "isOptimizing": False
            },
            {
                "id": "planet_code_explain",
                "name": "Code Explainer",
                "position": [-18, 0, 0],
                "orbitRadius": 18,
                "status": "testing",
                "deployedVersion": create_initial_version("Explain a complex piece of code in simple terms.", 0.91),
                "traceHistory": [],
                "isOptimizing": False
            }
        ],
        "config": {
            "activeOptimizer": "A/B Test",
            "evaluationMetrics": ["Score", "Correctness", "Readability"]
        }
    }
}

async def optimization_cycle(websocket):
    while True:
        try:
            galaxy_id = random.choice(list(galaxies.keys()))
            galaxy_data = galaxies[galaxy_id]
            
            if not any(p['isOptimizing'] for p in galaxy_data['planets']):
                planet_to_optimize = random.choice(galaxy_data['planets'])
                planet_to_optimize['isOptimizing'] = True

                await websocket.send(json.dumps({"type": "status", "message": f"Starting optimization for '{planet_to_optimize['name']}' in '{galaxy_data['name']}'..."}))
                await websocket.send(json.dumps({"type": "update", "payload": copy.deepcopy(galaxies)}))
                await asyncio.sleep(3) 

                deployed_version = planet_to_optimize['deployedVersion']
                new_text = f"{deployed_version['text']} Instruction: {random.choice(PROMPT_MODIFIERS)}"
                new_score = round(deployed_version['evaluationScore'] * random.uniform(0.95, 1.08), 2)
                new_score = min(new_score, 0.99)
                new_variant = create_initial_version(new_text, new_score)
                
                planet_to_optimize['traceHistory'].append(new_variant)
                planet_to_optimize['traceHistory'].sort(key=lambda v: v['evaluationScore'], reverse=True)
                planet_to_optimize['traceHistory'] = planet_to_optimize['traceHistory'][:10]
                
                await websocket.send(json.dumps({"type": "status", "message": f"New variant for '{planet_to_optimize['name']}' scored {new_score:.2f}."}))
                await websocket.send(json.dumps({"type": "update", "payload": copy.deepcopy(galaxies)}))
                await asyncio.sleep(2)

                if new_variant['evaluationScore'] > deployed_version['evaluationScore']:
                    planet_to_optimize['traceHistory'].append(deployed_version)
                    planet_to_optimize['deployedVersion'] = new_variant
                    await websocket.send(json.dumps({"type": "status", "message": f"Promoted new version for '{planet_to_optimize['name']}'!"}))
                    await asyncio.sleep(1)
                
                planet_to_optimize['isOptimizing'] = False
                await websocket.send(json.dumps({"type": "update", "payload": copy.deepcopy(galaxies)}))

            await asyncio.sleep(random.uniform(5, 10))
        except websockets.exceptions.ConnectionClosed:
            break
        except Exception:
            print(f"An error occurred in the optimization cycle.")
            import traceback
            traceback.print_exc()
            await asyncio.sleep(5)

async def client_handler(websocket):
    print("AI Cockpit client connected. Starting role-based agent simulation...")
    try:
        await websocket.send(json.dumps({"type": "init", "payload": copy.deepcopy(galaxies)}))
        await optimization_cycle(websocket)
    except websockets.exceptions.ConnectionClosed:
        print("AI Cockpit client disconnected.")
    except Exception as e:
        print(f"An error occurred in the client handler: {e}")
        import traceback
        traceback.print_exc()

async def main():
    async with websockets.serve(client_handler, "0.0.0.0", 8765):
        print("Role-Based Planet Agent started on ws://0.0.0.0:8765")
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())
