import sys
import argparse
import subprocess
from pathlib import Path

# Fix Windows CP1251 encoding
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

def get_template_path(prompt_type="worker"):
    script_dir = Path(__file__).parent
    if prompt_type == "orchestrator":
        return script_dir.parent / "references" / "swarm_orchestrator_template.md"
    return script_dir.parent / "references" / "system_prompt_template.md"

def get_available_skills():
    """Сканирует директорию скиллов и возвращает их список."""
    skills_dir = Path.home() / ".gemini" / "config" / "skills"
    skills = []
    if skills_dir.exists():
        for d in skills_dir.iterdir():
            if d.is_dir() and (d / "SKILL.md").exists():
                skills.append(f"- {d.name}")
    return "\n".join(skills) if skills else "- Скиллы не найдены или директория недоступна."

def extract_template(text: str) -> str:
    if "```markdown" in text:
        parts = text.split("```markdown")
        if len(parts) > 1:
            return parts[-1].split("```")[0].strip()
    return text

def main():
    parser = argparse.ArgumentParser(description="Prompt Generator for Gemini Flash Agents")
    parser.add_argument("--project", required=True)
    parser.add_argument("--role", required=True)
    parser.add_argument("--specialization", required=True)
    parser.add_argument("--sources", required=True)
    parser.add_argument("--output_format", required=True)
    parser.add_argument("--task_steps", required=True)
    parser.add_argument("--restrictions", default="")
    parser.add_argument("--examples", default="[ЗАГЛУШКА: Замените на реальные примеры ввода-вывода]")
    parser.add_argument("--outdir", default="scripts/prompts")
    
    # New Swarm Arguments
    parser.add_argument("--type", choices=["worker", "orchestrator"], default="worker")
    parser.add_argument("--topology", default="Fan-Out / Fan-In", help="Topology for orchestrators")
    
    args = parser.parse_args()
    
    template_path = get_template_path(args.type)
    if not template_path.exists():
        print(f"❌ Ошибка: Шаблон {template_path.name} не найден!")
        sys.exit(1)
        
    template_content = template_path.read_text(encoding="utf-8")
    prompt_template = extract_template(template_content)
    
    # Замены
    prompt = prompt_template.replace("{{AGENT_ROLE}}", args.role)
    prompt = prompt.replace("{{PROJECT_NAME}}", args.project)
    prompt = prompt.replace("{{AGENT_SPECIALIZATION}}", args.specialization)
    prompt = prompt.replace("{{DATA_SOURCES}}", args.sources)
    prompt = prompt.replace("{{EXPECTED_OUTPUT}}", args.output_format)
    prompt = prompt.replace("{{TASK_STEPS}}", args.task_steps)
    prompt = prompt.replace("{{PROJECT_RESTRICTIONS}}", args.restrictions)
    prompt = prompt.replace("{{FEW_SHOT_EXAMPLES}}", args.examples)
    prompt = prompt.replace("{{AVAILABLE_SKILLS}}", get_available_skills())
    
    if args.type == "orchestrator":
        prompt = prompt.replace("{{SWARM_TOPOLOGY}}", args.topology)
    
    # Формируем чек-лист
    steps = [s.strip() for s in args.task_steps.split('\n') if s.strip()]
    checklist = ""
    for i, step in enumerate(steps, 1):
        preview = step[:20] + "..." if len(step) > 20 else step
        checklist += f"- [ ] Пункт {i}: {preview} — выполнен\n"
    prompt = prompt.replace("{{CHECKLIST_ITEMS}}", checklist.strip())
    
    # Префикс отчета
    role_prefix = args.role.split()[0].upper()
    prompt = prompt.replace("{{REPORT_PREFIX}}", f"{role_prefix} Report")
    
    # Сохранение
    out_dir = Path(args.outdir)
    out_dir.mkdir(parents=True, exist_ok=True)
    
    safe_name = args.role.lower().replace(" ", "_").replace("/", "_")
    out_path = out_dir / f"{safe_name}_prompt.md"
    out_path.write_text(prompt, encoding="utf-8")
    
    print(f"\n✅ Промпт успешно сгенерирован: {out_path}")
    
    # Валидация
    validator_path = Path(__file__).parent / "prompt_validator.py"
    if validator_path.exists():
        print(f"\n🔍 Запуск автоматической валидации промпта ({args.type} mode)...")
        result = subprocess.run(
            [sys.executable, str(validator_path), "--input", str(out_path), "--mode", args.type],
            capture_output=True,
            text=True,
            encoding="utf-8"
        )
        print(result.stdout)
        if result.returncode != 0:
            print("⚠️ ВНИМАНИЕ: Промпт не прошел проверки валидатора.")
    
if __name__ == "__main__":
    main()
