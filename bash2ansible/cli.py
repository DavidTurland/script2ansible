import argparse
import os
import sys
import json
import yaml
from .core import translate_to_ansible, parse_bash_script
from .config import load_config
from .processors import BashProcessor, SlackRoleProcessor



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Translate Bash script into an Ansible playbook.")
    parser.add_argument("input", help="Input Bash script")
    parser.add_argument("output", help="Output Ansible playbook")
    parser.add_argument("--json", action="store_true", help="Force JSON output")
    parser.add_argument("--yaml", action="store_true", help="Force YAML output")
    parser.add_argument("--strict", action="store_true", help="Strict mode: no shell fallback")
    parser.add_argument("--type", choices=["bash", "slack"], default="bash", help="type of thing to process (bash or slack)")
    parser.add_argument("--generator", choices=["role", "playbook"], default="role", help="type of thing to generate (role or playbook)")

    args = parser.parse_args()

    config = load_config()

    # CLI override config
    if args.json:
        config["output_format"] = "json"
    if args.yaml:
        config["output_format"] = "yaml"
    if args.strict:
        config["allow_shell_fallback"] = False
    config["input"] = args.input
    config["output"] = args.output

    config["generator"] = args.generator

    if args.type == "slack":
        processor = SlackRoleProcessor(args.input, config)
    elif args.type == "bash":
        processor = BashProcessor(args.input, config)
    processor.process()


    # tasks = parse_bash_script(args.input, config)
    # if not tasks:
    #     print("⚠️ No tasks generated.")
    #     sys.exit(0)

    # output = generate_playbook(tasks, config["output_format"])
    # with open(args.output, 'w') as f:
    #     f.write(output)

    fmt = config["output_format"].upper()
    print(f"✅ {fmt} playbook written to {args.output}")
