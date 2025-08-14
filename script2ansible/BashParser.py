import re
import logging
from .Parser import Parser


class BashParser(Parser):
    def __init__(self, file_path=None, script_string=None, config=None):
        super().__init__(file_path=file_path, config=config, script_string=script_string)

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

    def translate_to_ansible(
        self,
        command,
        config=None,
        umask=None,
        variables=None,
        last_register=None,
        last_status_cond=None,
    ):
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
                "ansible.builtin.copy": {
                    "src": src,
                    "dest": dest,
                    "remote_src": False,
                },
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
                    "remote_src": False,
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

        # echo "text" > file or echo "text" >> file
        echo_match = re.match(
            r'echo\s+(?P<text>".*?"|\'.*?\'|[^>]+)\s*(?P<redir>>|>>)\s*(?P<file>\S+)',
            command,
        )
        if echo_match:
            text = echo_match.group("text")
            redir = echo_match.group("redir")
            file = echo_match.group("file")
            if redir == ">":
                return {
                    "name": f"Write text to {file}",
                    "ansible.builtin.copy": {
                        "dest": file,
                        "content": text.strip("\"'"),
                        "mode": self.umask_to_mode(umask or "022", is_dir=False),
                    },
                    "register": "echo_result",
                }
            else:  # >>
                return {
                    "name": f"Append text to {file}",
                    "ansible.builtin.lineinfile": {
                        "path": file,
                        "line": text.strip("\"'"),
                        "create": True,
                        "mode": self.umask_to_mode(umask or "022", is_dir=False),
                        "insertafter": "EOF",
                    },
                    "register": "echo_result",
                }

        # grep "pattern" file
        grep_match = re.match(
            r'grep\s+(?P<pattern>".+?"|\'.+?\'|\S+)\s+(?P<file>\S+)', command
        )
        if grep_match:
            pattern = grep_match.group("pattern")
            file = grep_match.group("file")
            return {
                "name": f"grep for {pattern} in {file}",
                "shell": f"grep {pattern} {file}",
                "register": "grep_result",
            }

        # fallback
        if allow_shell_fallback:
            result = {
                "name": f"Run shell command: {command}",
                "ansible.builtin.shell": command,
                "register": "shell_command_result",
            }
            if last_status_cond:
                result["when"] = last_status_cond
            return result
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
        last_register = None
        last_status_cond = None
        if self.file_path:
            with open(self.file_path, "r") as file:
                lines = file.readlines()
        elif self.script_string:
            lines = self.script_string.splitlines()
        else:
            return []




        if lines and lines[0].startswith("#!"):
            if not any(shell in lines[0] for shell in ("bash", "sh")):
                logging.warning(f"Skipped: Unsupported shell: {lines[0].strip()}")
                return []

        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if not line or line.startswith("#"):
                i += 1
                continue

            if line.endswith("\\"):
                current_command += line[:-1] + " "
                i += 1
                continue
            else:
                current_command += line

            # Detect if-block for $? test
            if re.match(
                r"if\s+\[\[\s+\$\?\s+-eq\s+(\d+)\s*\]\];\s*then", current_command
            ):
                status_code = re.search(r"-eq\s+(\d+)", current_command).group(1)
                # Map $? == 0 to "is succeeded", $? == 1 to "is failed"
                if status_code == "0":
                    last_status_cond = f"{last_register} is succeeded"
                else:
                    last_status_cond = f"{last_register} is failed"
                current_command = ""
                i += 1
                continue

            # End of if-block
            if current_command == "fi":
                last_status_cond = None
                current_command = ""
                i += 1
                continue

            result = self.translate_to_ansible(
                current_command.strip(),
                config=self.config,
                umask=current_umask,
                variables=variables,
                last_register=last_register,
                last_status_cond=last_status_cond,
            )

            # internal results
            if "_umask" in result:
                current_umask = result["_umask"]
            elif "_set_var" in result:
                var, val = result["_set_var"]
                variables[var] = val
            else:
                # Track register for grep
                if "register" in result:
                    last_register = result["register"]
                # Add when condition if present
                if "when" in result:
                    tasks.append(result)
                else:
                    # If last_status_cond is set, add it as 'when'
                    if last_status_cond:
                        result["when"] = last_status_cond
                        last_status_cond = None
                    tasks.append(result)

            current_command = ""
            i += 1

        return tasks
