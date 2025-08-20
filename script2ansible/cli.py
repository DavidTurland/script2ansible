import argparse
import os
import logging
from .config import load_config
from .processors import BashProcessor, SlackRoleProcessor


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Translate Perl or Bash scripts into an Ansible playbook."
    )
    parser.add_argument("input", help="Input  - its complicated")
    parser.add_argument("output", help="Output  - its complicated")
    parser.add_argument("--json", action="store_true", help="Force JSON output")
    parser.add_argument("--yaml", action="store_true", help="Force YAML output")
    parser.add_argument(
        "--strict", action="store_true", help="Strict mode: no shell fallback"
    )
    parser.add_argument(
        "--type",
        choices=["script", "slack"],
        default="script",
        help="type of thing to process (Perl/bash or slack)",
    )
    parser.add_argument(
        "--generator",
        choices=["role", "role_tasks", "playbook"],
        default="role",
        help="type of thing to generate (role or playbook)",
    )

    parser.add_argument("--role_name", 
                        help="ansible role name - overrides implied or defines when missing ")

    parser.add_argument("--debug", action="store_true", help="Enable debug logging")

    args = parser.parse_args()

    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(level=log_level, format="%(levelname)s: %(message)s")

    config = load_config()

    # CLI override config
    if args.json:
        config["output_format"] = "json"
    if args.yaml:
        config["output_format"] = "yaml"
    if args.strict:
        config["allow_shell_fallback"] = False
    args.input = os.path.normpath(args.input)
    args.output = os.path.normpath(args.output)
    config["input"] = args.input
    config["output"] = args.output
    config["generator"] = args.generator
    if args.role_name:
        config["role_name"] = args.role_name

    if args.type == "slack":
        if os.path.isdir(config["input"]):
            dir_name = os.path.basename(config["input"])
            logging.debug(f"dir name is : {dir_name}")
            output_dir_name = os.path.basename(config["output"])
            if dir_name == "roles":
                if output_dir_name == "roles":
                    # assume ansible roles dir
                    output_root = os.path.dirname(config["output"])
                else:
                    # assume we need to add the ansible roles dir
                    output_root = os.path.join(config["output"], "roles")
                for role_name in os.listdir(config["input"]):
                    config["role_name"] = role_name
                    output_dir = os.path.join(output_root, role_name)
                    logging.info(f"Processing Slack role from directory: {role_name}")
                    role_dir = os.path.join(config["input"], role_name)
                    if not os.path.isdir(role_dir):
                        continue
                    processor = SlackRoleProcessor(role_dir, output_dir, config)
                    processor.process()
            else:
                # assume we are processing a single slack role
                if output_dir_name == "roles":
                    # assume ansible roles dir
                    output_dir = os.path.join(config["output"], dir_name)
                else:
                    # assume we need to add the ansible roles dir
                    output_dir = os.path.join(config["output"], "roles", dir_name)
                role_name = dir_name
                # if not set!!!!
                config["role_name"] = role_name
                processor = SlackRoleProcessor(args.input, output_dir, config)
                processor.process()
        else:
            raise ValueError(
                f"Input path {args.input} is not a directory for Slack role processing."
            )
    elif args.type == "script":
        if os.path.isfile(config["input"]):
            processor = BashProcessor(config["input"], config)
            processor.process()
        else:
            raise ValueError(
                f"Input path {args.input} is not a file for Bash processing."
            )
    else:
        raise ValueError(
            f"Unknown type: {args.type}"
        )   