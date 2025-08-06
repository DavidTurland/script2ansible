import argparse
import os
import sys
import json
import yaml
from .core import translate_to_ansible
from .config import load_config

def parse_bash_script(file_path, config):
    tasks = []
    with open(file_path, 'r') as file:
        lines = file.readlines()

    if lines and lines[0].startswith("#!"):
        if not any(shell in lines[0] for shell in ("bash", "sh")):
            print(f"⚠️ Skipped: Unsupported shell: {lines[0].strip()}")
            return []

    current_command = ""
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.endswith("\\"):
            current_command += line[:-1] + " "
            continue
        else:
            current_command += line

        task = translate_to_ansible(current_command.strip(), config)
        tasks.append(task)
        current_command = ""

    return tasks

def generate_playbook(tasks, output_format="yaml"):
    playbook = [{
        'name': 'Execute translated shell commands',
        'hosts': 'all',
        'become': True,
        'tasks': tasks
    }]
    return json.dumps(playbook, indent=2) if output_format == "json" else yaml.dump(playbook, sort_keys=False)

def main():
    parser = argparse.ArgumentParser(description="Translate Bash script into an Ansible playbook.")
    parser.add_argument("input", help="Input Bash script")
    parser.add_argument("output", help="Output Ansible playbook")
    parser.add_argument("--json", action="store_true", help="Force JSON output")
    parser.add_argument("--yaml", action="store_true", help="Force YAML output")
    parser.add_argument("--strict", action="store_true", help="Strict mode: no shell fallback")

    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"❌ File not found: {args.input}")
        sys.exit(1)

    config = load_config()

    # CLI override config
    if args.json:
        config["output_format"] = "json"
    if args.yaml:
        config["output_format"] = "yaml"
    if args.strict:
        config["allow_shell_fallback"] = False

    tasks = parse_bash_script(args.input, config)
    if not tasks:
        print("⚠️ No tasks generated.")
        sys.exit(0)

    output = generate_playbook(tasks, config["output_format"])
    with open(args.output, 'w') as f:
        f.write(output)

    fmt = config["output_format"].upper()
    print(f"✅ {fmt} playbook written to {args.output}")
