import re

def translate_to_ansible(command, config=None):
    config = config or {}
    allow_shell_fallback = config.get("allow_shell_fallback", True)

    # mkdir
    if match := re.match(r'mkdir\s+(-p\s+)?(?P<path>\S+)', command):
        return {
            "name": f"Ensure directory {match.group('path')} exists",
            "ansible.builtin.file": {
                "path": match.group("path"),
                "state": "directory"
            }
        }

    # chmod
    if match := re.match(r'chmod\s+(?P<mode>\d+)\s+(?P<path>\S+)', command):
        return {
            "name": f"Set permissions of {match.group('path')} to {match.group('mode')}",
            "ansible.builtin.file": {
                "path": match.group("path"),
                "mode": match.group("mode")
            }
        }

    # apt install
    if match := re.match(r'apt(-get)?\s+install\s+(-y\s+)?(?P<packages>.+)', command):
        packages = match.group("packages").split()
        return {
            "name": f"Install packages: {' '.join(packages)}",
            "ansible.builtin.apt": {
                "name": packages,
                "state": "present",
                "update_cache": True
            }
        }

    # pip install
    if match := re.match(r'pip3?\s+install\s+(?P<packages>.+)', command):
        packages = match.group("packages").split()
        return {
            "name": f"Install Python packages: {' '.join(packages)}",
            "ansible.builtin.pip": {
                "name": packages
            }
        }

    # md5sum
    if match := re.match(r'md5sum\s+(?P<path>\S+)', command):
        return {
            "name": f"Check MD5 checksum of {match.group('path')}",
            "ansible.builtin.stat": {
                "path": match.group("path"),
                "checksum_algorithm": "md5"
            }
        }

    # wget -O dest
    if match := re.match(r'wget\s+(?P<url>\S+)\s+-O\s+(?P<dest>\S+)', command):
        return {
            "name": f"Download {match.group('url')} to {match.group('dest')}",
            "ansible.builtin.get_url": {
                "url": match.group("url"),
                "dest": match.group("dest")
            }
        }

    # wget
    if match := re.match(r'wget\s+(?P<url>\S+)', command):
        filename = match.group("url").split("/")[-1]
        return {
            "name": f"Download {match.group('url')} to ./{filename}",
            "ansible.builtin.get_url": {
                "url": match.group("url"),
                "dest": f"./{filename}"
            }
        }

    # touch
    if match := re.match(r'touch\s+(?P<path>\S+)', command):
        return {
            "name": f"Ensure file {match.group('path')} exists",
            "ansible.builtin.file": {
                "path": match.group("path"),
                "state": "touch"
            }
        }

    # cp
    if match := re.match(r'cp\s+(?P<src>\S+)\s+(?P<dest>\S+)', command):
        return {
            "name": f"Copy {match.group('src')} to {match.group('dest')}",
            "ansible.builtin.copy": {
                "src": match.group("src"),
                "dest": match.group("dest"),
                "remote_src": True
            }
        }

    # mv
    if match := re.match(r'mv\s+(?P<src>\S+)\s+(?P<dest>\S+)', command):
        return {
            "name": f"Move {match.group('src')} to {match.group('dest')}",
            "ansible.builtin.command": f"mv {match.group('src')} {match.group('dest')}"
        }

    # systemctl start
    if match := re.match(r'systemctl\s+start\s+(?P<svc>\S+)', command):
        return {
            "name": f"Start service {match.group('svc')}",
            "ansible.builtin.service": {
                "name": match.group("svc"),
                "state": "started"
            }
        }

    # systemctl enable
    if match := re.match(r'systemctl\s+enable\s+(?P<svc>\S+)', command):
        return {
            "name": f"Enable service {match.group('svc')}",
            "ansible.builtin.service": {
                "name": match.group("svc"),
                "enabled": True
            }
        }

    # echo "..." > file
    if match := re.match(r'echo\s+"(?P<content>.*)"\s*>\s*(?P<dest>\S+)', command):
        return {
            "name": f"Write content to {match.group('dest')}",
            "ansible.builtin.copy": {
                "dest": match.group("dest"),
                "content": match.group("content") + "\n"
            }
        }


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
