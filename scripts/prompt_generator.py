import sys
import argparse
import subprocess
import json
from pathlib import Path

import re

# Fix Windows CP1251 encoding
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

def get_template_path(prompt_type="worker"):
    script_dir = Path(__file__).parent
    if prompt_type == "orchestrator":
        return script_dir.parent / "references" / "swarm_orchestrator_template.md"
    return script_dir.parent / "references" / "system_prompt_template.md"

def get_available_skills(skills_arg=None):
    """Возвращает список скиллов экосистемы, отфильтрованный от бэкапов и мусора."""
    skills_dir = Path.home() / ".gemini" / "config" / "skills"
    
    if skills_arg and skills_arg.lower() in ["none", "false", "off", "нет"]:
        return "- Специализированные скиллы не требуются. Используй системные инструменты."
        
    if skills_arg and skills_arg.lower() != "all":
        # Явный список через запятую
        selected = [s.strip() for s in skills_arg.split(",") if s.strip()]
        return "\n".join(f"- {s}" for s in selected)
    
    # По умолчанию отдаем все рабочие скиллы экосистемы (без бэкап-папок и мусора)
    skills = []
    if skills_dir.exists():
        for d in sorted(skills_dir.iterdir()):
            if d.is_dir() and (d / "SKILL.md").exists():
                name = d.name.lower()
                # Фильтруем бэкапы, тесты и временные папки
                if any(x in name for x in ["backup", "temp", "tmp", "old", "test_"]) or name.startswith("."):
                    continue
                skills.append(f"- {d.name}")
                
    return "\n".join(skills) if skills else "- Скиллы не найдены или директория недоступна."

def extract_template(text: str) -> str:
    if "```markdown" in text:
        parts = text.split("```markdown")
        if len(parts) > 1:
            return parts[-1].split("```")[0].strip()
    return text

def build_prompt(args_dict: dict, template_content: str) -> str:
    """Build a single prompt from args dict and template."""
    prompt_template = extract_template(template_content)
    
    prompt_type = args_dict.get("type", "worker")
    
    # Форматируем ограничения (restrictions)
    restrictions = args_dict.get("restrictions", "")
    if restrictions:
        restrs = [r.strip() for r in re.split(r'[\n;]', restrictions) if r.strip()]
        formatted_restrictions = "\n".join(f"- ⚠️ {r}" for r in restrs)
    else:
        formatted_restrictions = ""

    # Замены
    prompt = prompt_template.replace("{{AGENT_ROLE}}", args_dict.get("role", "Agent"))
    prompt = prompt.replace("{{PROJECT_NAME}}", args_dict.get("project", "Project"))
    prompt = prompt.replace("{{AGENT_SPECIALIZATION}}", args_dict.get("specialization", ""))
    prompt = prompt.replace("{{DATA_SOURCES}}", args_dict.get("sources", ""))
    prompt = prompt.replace("{{EXPECTED_OUTPUT}}", args_dict.get("output_format", ""))
    prompt = prompt.replace("{{TASK_STEPS}}", args_dict.get("task_steps", ""))
    prompt = prompt.replace("{{PROJECT_RESTRICTIONS}}", formatted_restrictions)
    prompt = prompt.replace("{{FEW_SHOT_EXAMPLES}}", args_dict.get("examples", ""))
    prompt = prompt.replace("{{AVAILABLE_SKILLS}}", get_available_skills(args_dict.get("skills")))
    
    if prompt_type == "orchestrator":
        prompt = prompt.replace("{{SWARM_TOPOLOGY}}", args_dict.get("topology", "Fan-Out / Fan-In"))
    
    # Формируем чек-лист
    task_steps = args_dict.get("task_steps", "")
    steps = [s.strip() for s in task_steps.split('\n') if s.strip()]
    checklist = ""
    for i, step in enumerate(steps, 1):
        clean_step = re.sub(r"^\d+[\.)\]]\s*", "", step)
        checklist += f"- [ ] Шаг {i}: {clean_step}\n"
    prompt = prompt.replace("{{CHECKLIST_ITEMS}}", checklist.strip())
    
    # Префикс отчета — safe для кириллицы
    role = args_dict.get("role", "AGENT")
    # Берём первое ASCII-слово или транслитерируем
    ascii_words = re.findall(r'[A-Za-z]+', role)
    if ascii_words:
        report_prefix = ascii_words[0].upper()
    else:
        report_prefix = "AGENT"
    prompt = prompt.replace("{{REPORT_PREFIX}}", f"{report_prefix} Report")
    
    return prompt


def process_batch(batch_path: str, project: str, outdir: str):
    """Process a batch JSON manifest file with multiple agents."""
    batch_file = Path(batch_path)
    if not batch_file.exists():
        print(f"❌ Ошибка: Batch-файл {batch_path} не найден!")
        sys.exit(1)
    
    manifest = json.loads(batch_file.read_text(encoding="utf-8"))
    agents = manifest.get("agents", [])
    
    if not agents:
        print("❌ Ошибка: В манифесте нет агентов (поле 'agents' пустое)!")
        sys.exit(1)
    
    # Глобальные настройки из манифеста
    global_sources = manifest.get("global_sources", "")
    global_restrictions = manifest.get("global_restrictions", "")
    global_skills = manifest.get("global_skills", None)
    
    out_dir = Path(outdir)
    out_dir.mkdir(parents=True, exist_ok=True)
    
    # Определяем тип шаблона
    worker_template = get_template_path("worker")
    orch_template = get_template_path("orchestrator")
    
    generated = []
    
    for agent in agents:
        agent_type = agent.get("type", "worker")
        template_path = orch_template if agent_type == "orchestrator" else worker_template
        
        if not template_path.exists():
            print(f"⚠️ Шаблон {template_path.name} не найден, пропуск агента {agent.get('role', '?')}")
            continue
            
        template_content = template_path.read_text(encoding="utf-8")
        
        # Мержим глобальные и локальные настройки
        agent_dict = {
            "project": project,
            "role": agent.get("role", "Agent"),
            "type_name": agent.get("type_name", "self"),
            "specialization": agent.get("specialization", ""),
            "sources": global_sources + "\n" + agent.get("sources", ""),
            "output_format": agent.get("output_format", ""),
            "task_steps": agent.get("task_steps", ""),
            "restrictions": global_restrictions + "\n" + agent.get("restrictions", ""),
            "skills": agent.get("skills", global_skills),
            "examples": agent.get("examples", ""),
            "type": agent_type,
            "topology": agent.get("topology", "Fan-Out / Fan-In"),
        }
        
        prompt = build_prompt(agent_dict, template_content)
        
        safe_name = agent.get("role", "agent").lower().replace(" ", "_").replace("/", "_")
        safe_name = re.sub(r'[^a-z0-9_]', '', safe_name)
        out_path = out_dir / f"{safe_name}_prompt.md"
        out_path.write_text(prompt, encoding="utf-8")
        
        model = agent.get("model", "flash")
        generated.append({
            "type_name": agent.get("type_name", "self"),
            "role": agent.get("role"),
            "prompt": prompt,
            "model": model,
            "depends_on": agent.get("depends_on", [])
        })
        print(f"  ✅ {agent.get('role')} → {out_path} (model: {model})")
    
    # Сохраняем invoke-manifest для удобного запуска
    waves = []
    resolved = set()
    pending = generated.copy()
    wave_idx = 1
    while pending:
        current_wave = []
        next_pending = []
        for a in pending:
            deps = set(a.get("depends_on", []))
            if deps.issubset(resolved):
                current_wave.append(a)
            else:
                next_pending.append(a)
        
        if not current_wave: # cycle or missing deps, force them into current wave
            current_wave = next_pending
            next_pending = []
            
        waves.append({
            "wave": wave_idx,
            "Subagents": [
                {
                    "TypeName": a["type_name"],
                    "Role": a["role"],
                    "Prompt": a["prompt"],
                    "Model": a["model"]
                }
                for a in current_wave
            ]
        })
        resolved.update(a["role"] for a in current_wave)
        pending = next_pending
        wave_idx += 1

    invoke_manifest = {
        "project": project,
        "waves": waves
    }
    invoke_path = out_dir / "_invoke_manifest.json"
    invoke_path.write_text(json.dumps(invoke_manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    
    print(f"\n🚀 Batch complete! {len(generated)} промптов сгенерировано.")
    print(f"📋 Invoke-манифест: {invoke_path}")
    print(f"\n💡 Для запуска роя: прочитай каждый файл через view_file и запусти")
    print(f"   ОДНИМ вызовом invoke_subagent с массивом Subagents[].")
    
    return generated


def main():
    parser = argparse.ArgumentParser(description="Prompt Generator for Gemini Flash Agents v2.0")
    parser.add_argument("--project", required=True)
    parser.add_argument("--role", default="Agent")
    parser.add_argument("--specialization", default="")
    parser.add_argument("--sources", default="")
    parser.add_argument("--output_format", default="")
    parser.add_argument("--task_steps", default="")
    parser.add_argument("--restrictions", default="")
    parser.add_argument("--skills", default=None, help="Comma-separated skills, 'all', or omit for clean mode")
    parser.add_argument("--examples", default="")
    parser.add_argument("--outdir", default="scripts/prompts")
    
    # Agent type & model
    parser.add_argument("--type", choices=["worker", "orchestrator"], default="worker")
    parser.add_argument("--topology", default="Fan-Out / Fan-In", help="Topology for orchestrators")
    parser.add_argument("--model", default="flash", choices=["flash", "flash_lite", "pro", "inherit"],
                        help="Model recommendation for this agent")
    
    # Batch mode
    parser.add_argument("--batch", default=None, help="Path to batch JSON manifest for multi-agent generation")
    
    args = parser.parse_args()
    
    # Batch mode
    if args.batch:
        process_batch(args.batch, args.project, args.outdir)
        return
    
    # Single agent mode
    if not args.role or args.role == "Agent":
        print("❌ Ошибка: --role обязателен в single-agent режиме!")
        sys.exit(1)
    
    template_path = get_template_path(args.type)
    if not template_path.exists():
        print(f"❌ Ошибка: Шаблон {template_path.name} не найден!")
        sys.exit(1)
        
    template_content = template_path.read_text(encoding="utf-8")
    
    args_dict = {
        "project": args.project,
        "role": args.role,
        "specialization": args.specialization,
        "sources": args.sources,
        "output_format": args.output_format,
        "task_steps": args.task_steps,
        "restrictions": args.restrictions,
        "skills": args.skills,
        "examples": args.examples,
        "type": args.type,
        "topology": args.topology,
    }
    
    prompt = build_prompt(args_dict, template_content)
    
    # Сохранение
    out_dir = Path(args.outdir)
    out_dir.mkdir(parents=True, exist_ok=True)
    
    safe_name = args.role.lower().replace(" ", "_").replace("/", "_")
    safe_name = re.sub(r'[^a-z0-9_]', '', safe_name)
    out_path = out_dir / f"{safe_name}_prompt.md"
    out_path.write_text(prompt, encoding="utf-8")
    
    print(f"\n✅ Промпт успешно сгенерирован: {out_path}")
    print(f"   Model: {args.model}")
    
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
