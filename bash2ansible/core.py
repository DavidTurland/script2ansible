import re

def translate_to_ansible(command, config=None):
    config = config or {}
    allow_shell_fallback = config.get("allow_shell_fallback", True)

    # All mappings same as before...
    # (mkdir, chmod, apt, pip, etc...)

    # ... omitted for brevity

    # fallback
    if allow_shell_fallback:
        return {
            "name": f"Run shell command: {command}",
            "ansible.builtin.shell": command
        }
    else:
        return {
            "name": f"Unsupported command (shell fallback disabled): {command}",
            "ansible.builtin.debug": {
                "msg": f"Command skipped: {command}"
            }
        }
