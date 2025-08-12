import os
import yaml

DEFAULT_CONFIG = {
    "output_format": "yaml",  # or "json"
    "allow_shell_fallback": True,
    "verbose": False,
    "strict": False,
    "perl_custom": "",
}


def load_config():
    path = ".script2ansible.yaml"
    if os.path.exists(path):
        with open(path, "r") as f:
            try:
                user_config = yaml.safe_load(f)
                return {**DEFAULT_CONFIG, **(user_config or {})}
            except Exception as e:
                import logging

                logging.error(f"Error reading config: {e}")
    return DEFAULT_CONFIG
