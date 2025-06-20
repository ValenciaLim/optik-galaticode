import asyncio
import json
import websockets
import random
import subprocess
import os

# --- Prompt Generation Modifiers ---
# In a real system, an LLM would generate these variations.
PROMPT_MODIFIERS = [
    "Be more direct.", "Use simpler language.", "Adopt a professional tone.",
    "Explain it like I'm five.", "Be more expressive and use emojis.",
    "Sound more empathetic.", "Focus on the key takeaways.", "Provide a step-by-step guide.",
    "Ensure the answer is factually accurate.", "Format the response as a list.",
    "Summarize the main point in one sentence.", "Add a historical context."
]

# --- Defines the orbits for ranks 1 through 10 ---
ORBIT_RADII = [6, 9, 12, 15, 18, 21, 24, 27, 30, 33]

async def self_optimizing_agent_handler(websocket):
    """
    Handles the WebSocket connection and runs the main agent loop.
    This version adds a temporary 'isNew' flag to highlight new prompts.
    """
    print("AI Cockpit client connected. Starting Final Agent with Highlighting...")
    
    # --- Initial State ---
    prompts = [
        {"id": "prompt_v1", "name": "Prompt Variant A (Gen 1)", "text": "As an assistant, your goal is to be concise.", "accuracy": 0.80, "hallucination": 0.20, "speed": 0.4},
        {"id": "prompt_v2", "name": "Prompt Variant B (Gen 1)", "text": "You are a laconic assistant. Be brief.", "accuracy": 0.75, "hallucination": 0.25, "speed": 0.3},
        {"id": "prompt_v3", "name": "Prompt Variant C (Gen 1)", "text": "You are an AI assistant. Provide short answers.", "accuracy": 0.85, "hallucination": 0.15, "speed": 0.2}
    ]
    next_prompt_num = 4

    try:
        # --- Main Optimization Loop ---
        num_rounds = 10 # More rounds to see the evolution
        for i in range(num_rounds):
            await websocket.send(json.dumps({"type": "status", "message": f"--- Starting Optimization Round {i+1}/{num_rounds} ---"}))
            await asyncio.sleep(2)

            # ** Remove 'isNew' flag from previous round before creating a new one **
            for p in prompts:
                if 'isNew' in p:
                    del p['isNew']

            # 1. Generate a New Challenger Prompt if not at max capacity
            if len(prompts) < 10:
                best_prompt = max(prompts, key=lambda p: p['accuracy'])
                await websocket.send(json.dumps({"type": "status", "message": f"Evolving from winner '{best_prompt['name']}'..."}))
                await asyncio.sleep(1)

                new_modifier = random.choice(PROMPT_MODIFIERS)
                new_prompt = {
                    "id": f"prompt_v{next_prompt_num}",
                    "name": f"Variant {chr(ord('A') + next_prompt_num - 1)} (Gen {i+2})",
                    "text": f"{best_prompt['text']} Instruction: {new_modifier}",
                    "accuracy": round(best_prompt['accuracy'] * 0.95, 2),
                    "hallucination": round(best_prompt['hallucination'] * 1.05, 2),
                    "speed": round(random.uniform(0.1, 0.5), 2),
                    "isNew": True  # <--- HERE IS THE NEW FLAG
                }
                prompts.append(new_prompt)
                next_prompt_num += 1

            # 2. Simulate the A/B test results for the current fleet
            await websocket.send(json.dumps({"type": "status", "message": "Evaluating fleet performance..."}))
            for p in prompts:
                p['accuracy'] = round(p['accuracy'] * random.uniform(0.97, 1.06), 2)
                p['accuracy'] = min(p['accuracy'], 0.99)
            await asyncio.sleep(2)

            # 3. Re-rank and assign new orbits based on performance
            await websocket.send(json.dumps({"type": "status", "message": "Re-ranking fleet and assigning new orbits..."}))
            prompts.sort(key=lambda p: p['accuracy'], reverse=True) # Sort best to worst
            
            # Trim the fleet back to 10 if we've exceeded it
            if len(prompts) > 10:
                prompts = prompts[:10]

            for index, p in enumerate(prompts):
                p['orbitRadius'] = ORBIT_RADII[index]

            # Send the complete, re-ranked update to the frontend
            await websocket.send(json.dumps({"type": "update", "payload": prompts}))
            await asyncio.sleep(4) # Pause so the user can see the re-ranking

        # --- Finalization ---
        await websocket.send(json.dumps({"type": "status", "message": "Optimization complete. Selecting final champion..."}))
        final_winner = prompts[0] # The best is now always the first in the list
        
        await websocket.send(json.dumps({"type": "status", "message": f"Champion '{final_winner['name']}' selected! Committing to GitHub..."}))

        # Commit to Git
        if not os.path.exists('prompts'): os.makedirs('prompts')
        with open("prompts/winning_prompt.txt", "w") as f:
            f.write(f"# Prompt Name: {final_winner['name']}\n# Rank: 1\n# Accuracy: {final_winner['accuracy']}\n\n{final_winner['text']}")
        try:
            subprocess.run(["git", "add", "prompts/winning_prompt.txt"], check=True)
            commit_message = f"auto: Promote evolved prompt '{final_winner['name']}' to rank 1"
            subprocess.run(["git", "commit", "-m", commit_message], check=True)
            await websocket.send(json.dumps({"type": "status", "message": "Successfully committed winning prompt."}))
        except Exception as e:
            await websocket.send(json.dumps({"type": "status", "message": f"Git commit failed: {e}"}))
        
        await asyncio.sleep(3)
        await websocket.send(json.dumps({"type": "status", "message": "Prompt DevOps cycle complete. Agent is now idle."}))

    except websockets.exceptions.ConnectionClosed:
        print("AI Cockpit client disconnected.")
    except Exception as e:
        print(f"An error occurred in the agent handler: {e}")

async def main():
    async with websockets.serve(self_optimizing_agent_handler, "0.0.0.0", 8765):
        print("Rank-Based Orbit Agent with Highlighting started on ws://0.0.0.0:8765")
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())