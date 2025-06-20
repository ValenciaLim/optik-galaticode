import subprocess
subprocess.run([
    "git", "add", "prompts/winning_prompt.txt"
])
subprocess.run([
    "git", "commit", "-m", "auto: commit best-performing prompt"
])
subprocess.run(["git", "push"])
