from opik_optimizer import MetaPromptOptimizer, TaskConfig, MetricConfig
from opik.evaluation.metrics import LevenshteinRatio
from opik_optimizer.utils import from_dataset_field, from_llm_response_text
import json

# Load dataset (e.g., from a JSON file inside /data)
with open('data/prompt_testset.json') as f:
    dataset = json.load(f)

task = TaskConfig(
    instruction_prompt="You're a helpful assistant. Answer concisely.",
    input_dataset_fields=["input"],
    output_dataset_field="expected_output",
    use_chat_prompt=True,
)

metric = MetricConfig(
    metric=LevenshteinRatio(),
    inputs={"output": from_llm_response_text(), "reference": from_dataset_field(name="expected_output")}
)

optimizer = MetaPromptOptimizer(
    model="openai/gpt-4",
    reasoning_model="openai/gpt-4",
    max_rounds=3,
    num_prompts_per_round=4,
    improvement_threshold=0.05,
    project_name="GalactiCode"
)

result = optimizer.optimize_prompt(dataset=dataset, task_config=task, metric_config=metric)
result.display()

with open("prompts/winning_prompt.txt", "w") as f:
    f.write(result.best_prompt)
