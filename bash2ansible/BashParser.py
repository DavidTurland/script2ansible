import re
from .Parser import Parser


class BashParser(Parser):
    def __init__(self, file_path, config):
        super().__init__(file_path, config)

    def umask_to_mode(self, umask: str, is_dir: bool = True):
        """Convert umask (e.g., '0022') to default mode (e.g., '0755')."""
        try:
            mask = int(umask, 8)
            default = 0o777 if is_dir else 0o666
            return format(default & ~mask, "04o")
        except Exception:
            return None

    def substitute_variables(self, command: str, variables: dict) -> str:
        # Replace ${VAR} style
        command = re.sub(
            r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}",
            lambda m: variables.get(m.group(1), m.group(0)),
            command,
        )

        # Replace $VAR style (only if followed by non-word char or end-of-line)
        def replace_var(match):
            var = match.group(1)
            return variables.get(var, match.group(0))

        return re.sub(r"\$(\w+)\b", replace_var, command)

    def translate_to_ansible(self, command, config=None, umask=None, variables=None):
        config = config or {}
        variables = variables or {}
        allow_shell_fallback = config.get("allow_shell_fallback", True)

        # Variable substitution
        for var, val in variables.items():
            command = command.replace(f"${var}", val)

        # Variable definition
        if match := re.match(r"(?P<var>[A-Za-z_][A-Za-z0-9_]*)=(?P<val>.+)", command):
            return {"_set_var": (match.group("var"), match.group("val"))}

        # umask
        if match := re.match(r"umask\s+(?P<mask>\d{3,4})", command):
            return {"_umask": match.group("mask")}

        # mkdir
        if match := re.match(r"mkdir\s+(-p\s+)?(?P<path>\S+)", command):
            mode = self.umask_to_mode(umask or "022", is_dir=True)
            return {
                "name": f"Ensure directory {match.group('path')} exists",
                "ansible.builtin.file": {
                    "path": match.group("path"),
                    "state": "directory",
                    "mode": mode,
                },
            }

        # touch
        if match := re.match(r"touch\s+(?P<path>\S+)", command):
            mode = self.umask_to_mode(umask or "022", is_dir=False)
            return {
                "name": f"Ensure file {match.group('path')} exists",
                "ansible.builtin.file": {
                    "path": match.group("path"),
                    "state": "touch",
                    "mode": mode,
                },
            }

        # ln [/ -s] SRC DEST
        if match := re.match(r"ln(\s+-s)?\s+(?P<src>\S+)\s+(?P<dest>\S+)", command):
            is_symlink = bool(match.group(1))
            return {
                "name": f"Create {'symlink' if is_symlink else 'hard link'} {match.group('dest')} → {match.group('src')}",
                "ansible.builtin.file": {
                    "src": match.group("src"),
                    "dest": match.group("dest"),
                    "state": "link" if is_symlink else "hard",
                },
            }

        # cp SRC DEST
        cp_match = re.match(
            r"cp\s+(-[a-zA-Z]+\s+)?(?P<src>\S+)\s+(?P<dest>\S+)", command
        )
        if cp_match:
            src = cp_match.group("src")
            dest = cp_match.group("dest")
            return {
                "name": f"Copy {src} to {dest}",
                "ansible.builtin.copy": {"src": src, "dest": dest, "remote_src": True},
            }

        # ldconfig (no native Ansible module — fallback)
        if re.match(r"ldconfig", command):
            return {"name": "Run ldconfig", "ansible.builtin.shell": "ldconfig"}

        # gunzip file.gz
        if match := re.match(r"gunzip\s+(?P<path>\S+)", command):
            return {
                "name": f"Extract GZ archive {match.group('path')}",
                "ansible.builtin.unarchive": {
                    "src": match.group("path"),
                    "remote_src": True,
                    "dest": "/tmp",  # default unless configured
                },
            }

        # chmod 755 /some/file
        chmod_match = re.match(r"chmod\s+(?P<mode>\d+)\s+(?P<path>\S+)", command)
        if chmod_match:
            mode = chmod_match.group("mode")
            path = chmod_match.group("path")
            return {
                "name": f"Set permissions of {path} to {mode}",
                "ansible.builtin.file": {"path": path, "mode": mode},
            }
        # apt update
        apt_update_match = re.match(r"apt(-get)?\s+update", command)
        if apt_update_match:
            return {
                "name": "Update APT package cache",
                "ansible.builtin.apt": {"update_cache": True},
            }

        # apt upgrade
        apt_upgrade_match = re.match(r"apt(-get)?\s+upgrade", command)
        if apt_upgrade_match:
            return {
                "name": "Upgrade all packages",
                "ansible.builtin.apt": {"upgrade": "dist"},
            }
        # apt install -y package1 package2
        apt_match = re.match(
            r"apt(-get)?\s+install\s+(-y\s+)?(?P<packages>.+)", command
        )
        if apt_match:
            packages = apt_match.group("packages").split()
            return {
                "name": f"Install packages: {' '.join(packages)}",
                "ansible.builtin.apt": {
                    "name": packages,
                    "state": "present",
                    "update_cache": True,
                },
            }

        # yum update
        yum_update_match = re.match(r"yum\s+update(\s+-y)?", command)
        if yum_update_match:
            return {
                "name": "Update YUM package cache",
                "ansible.builtin.yum": {"name": "*", "state": "latest"},
            }

        # yum install -y package1 package2
        yum_install_match = re.match(
            r"yum\s+install\s+(-y\s+)?(?P<packages>.+)", command
        )
        if yum_install_match:
            packages = yum_install_match.group("packages").split()
            return {
                "name": f"Install packages: {' '.join(packages)}",
                "ansible.builtin.yum": {"name": packages, "state": "present"},
            }

        # fallback
        if allow_shell_fallback:
            return {
                "name": f"Run shell command: {command}",
                "ansible.builtin.shell": command,
            }
        else:
            return {
                "name": f"Unsupported command (shell fallback disabled): {command}",
                "ansible.builtin.debug": {"msg": f"Command skipped: {command}"},
            }

    def parse(self):
        tasks = []
        current_command = ""
        current_umask = "022"
        variables = {}

        with open(self.file_path, "r") as file:
            lines = file.readlines()

        import logging

        if lines and lines[0].startswith("#!"):
            if not any(shell in lines[0] for shell in ("bash", "sh")):
                logging.warning(f"Skipped: Unsupported shell: {lines[0].strip()}")
                return []

        for line in lines:
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            if line.endswith("\\"):
                current_command += line[:-1] + " "
                continue
            else:
                current_command += line

            result = self.translate_to_ansible(
                current_command.strip(),
                config=self.config,
                umask=current_umask,
                variables=variables,
            )

            # internal results
            if "_umask" in result:
                current_umask = result["_umask"]
            elif "_set_var" in result:
                var, val = result["_set_var"]
                variables[var] = val
            else:
                tasks.append(result)

            current_command = ""

        return tasks
