from .Parser import Parser
from bashlex import parser, ast
import re



class BashNodeVisitor(ast.nodevisitor):
    def __init__(self, tasks):
        self.tasks = tasks
        self.variables = {}

    def get_variables(self):
        return self.variables

    def substitute_variables(self, stringy: str) -> str:
        # Replace ${VAR} style
        stringy = re.sub(
            r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}",
            lambda m: self.variables.get(m.group(1), m.group(0)),
            stringy,
        )

        # Replace $VAR style (only if followed by non-word char or end-of-line)
        def replace_var(match):
            var = match.group(1)
            return self.variables.get(var, match.group(0))
        return re.sub(r"\$(\w+)\b", replace_var, stringy)

    def visitassignment(self, n, parts):
        if '=' in n.word:
            var, val = n.word.split('=', 1)
            self.variables[var] = val
        # self.tasks.append({"_set_var": (var, val)})
        return False

    def visitcommand(self, n, parts):
        # Build the command string from parts
        cmd = []
        redir_type = None
        redir_file = None
        for part in parts:
            if part.kind == 'word':
                cmd.append(part.word)
            elif part.kind == 'redirect':
                # Only handle > and >> for echo
                if part.type in ('>', '>>'):
                    redir_type = part.type
                    redir_file = part.input.word
            else:
                # Recursively visit other nodes
                self.visit(part)
        command_str = ' '.join(cmd)

        # Match and capture supported commands
        # umask
        m = re.match(r"umask\s+(?P<mask>\d{3,4})", command_str)
        if m:
            self.tasks.append({"_umask": m.group("mask")})
            return False

        # mkdir
        m = re.match(r"mkdir\s+(-p\s+)?(?P<path>\S+)", command_str)
        if m:
            self.tasks.append({
                "name": f"Ensure directory {m.group('path')} exists",
                "ansible.builtin.file": {
                    "path": m.group("path"),
                    "state": "directory"
                }
            })
            return False

        # touch
        m = re.match(r"touch\s+(?P<path>\S+)", command_str)
        if m:
            self.tasks.append({
                "name": f"Ensure file {m.group('path')} exists",
                "ansible.builtin.file": {
                    "path": m.group("path"),
                    "state": "touch"
                }
            })
            return False

        # ln
        m = re.match(r"ln(\s+-s)?\s+(?P<src>\S+)\s+(?P<dest>\S+)", command_str)
        if m:
            is_symlink = bool(m.group(1))
            self.tasks.append({
                "name": f"Create {'symlink' if is_symlink else 'hard link'} {m.group('dest')} → {m.group('src')}",
                "ansible.builtin.file": {
                    "src": m.group("src"),
                    "dest": m.group("dest"),
                    "state": "link" if is_symlink else "hard"
                }
            })
            return False

        # cp
        m = re.match(r"cp\s+(-[a-zA-Z]+\s+)?(?P<src>\S+)\s+(?P<dest>\S+)", command_str)
        if m:
            self.tasks.append({
                "name": f"Copy {m.group('src')} to {m.group('dest')}",
                "ansible.builtin.copy": {
                    "src": m.group("src"),
                    "dest": m.group("dest"),
                    "remote_src": False
                }
            })
            return False

        # ldconfig
        if command_str.startswith("ldconfig"):
            self.tasks.append({
                "name": "Run ldconfig",
                "ansible.builtin.shell": "ldconfig"
            })
            return False

        # gunzip
        m = re.match(r"gunzip\s+(?P<path>\S+)", command_str)
        if m:
            self.tasks.append({
                "name": f"Extract GZ archive {m.group('path')}",
                "ansible.builtin.unarchive": {
                    "src": m.group("path"),
                    "remote_src": False,
                    "dest": "/tmp"
                }
            })
            return False

        # chmod
        m = re.match(r"chmod\s+(?P<mode>\d+)\s+(?P<path>\S+)", command_str)
        if m:
            self.tasks.append({
                "name": f"Set permissions of {m.group('path')} to {m.group('mode')}",
                "ansible.builtin.file": {
                    "path": m.group("path"),
                    "mode": m.group("mode")
                }
            })
            return False

        # apt update
        if re.match(r"apt(-get)?\s+update", command_str):
            self.tasks.append({
                "name": "Update APT package cache",
                "ansible.builtin.apt": {"update_cache": True}
            })
            return False

        # apt upgrade
        if re.match(r"apt(-get)?\s+upgrade", command_str):
            self.tasks.append({
                "name": "Upgrade all packages",
                "ansible.builtin.apt": {"upgrade": "dist"}
            })
            return False

        # apt install
        m = re.match(r"apt(-get)?\s+install\s+(-y\s+)?(?P<packages>.+)", command_str)
        if m:
            pkgs = m.group("packages").split()
            self.tasks.append({
                "name": f"Install packages: {' '.join(pkgs)}",
                "ansible.builtin.apt": {
                    "name": pkgs,
                    "state": "present",
                    "update_cache": True
                }
            })
            return False

        # yum update
        if re.match(r"yum\s+update(\s+-y)?", command_str):
            self.tasks.append({
                "name": "Update YUM package cache",
                "ansible.builtin.yum": {"name": "*", "state": "latest"}
            })
            return False

        # yum install
        m = re.match(r"yum\s+install\s+(-y\s+)?(?P<packages>.+)", command_str)
        if m:
            pkgs = m.group("packages").split()
            self.tasks.append({
                "name": f"Install packages: {' '.join(pkgs)}",
                "ansible.builtin.yum": {
                    "name": pkgs,
                    "state": "present"
                }
            })
            return False

        # echo with redirect
        m = re.match(r'echo\s+(?P<text>".+?"|\'.+?\'|.+)', command_str)
        if m and redir_type and redir_file:
            text = m.group("text").strip('"\'')
            if redir_type == '>':
                self.tasks.append({
                    "name": f"Write text to {redir_file}",
                    "ansible.builtin.copy": {
                        "dest": redir_file,
                        "content": text
                    }
                })
            else:  # >>
                self.tasks.append({
                    "name": f"Append text to {redir_file}",
                    "ansible.builtin.lineinfile": {
                        "path": redir_file,
                        "line": text,
                        "create": True,
                        "insertafter": "EOF"
                    }
                })
            return False

        # echo without redirect
        m = re.match(r'echo\s+(?P<text>".+?"|\'.+?\'|.+)', command_str)
        if m and not redir_type:
            text = m.group("text").strip('"\'')
            self.tasks.append({
                "name": f"Echo text: {text}",
                "ansible.builtin.debug": {"msg": text}
            })
            return False

        return False

class BashLexParser(Parser):
    def __init__(self, file_path, config):
        super().__init__(file_path, config)

    def parse(self):
        """
        https://github.com/idank/bashlex/blob/master/examples/commandsubstitution-remover.py
        """
        tasks = []
        current_command = ""
        current_umask = "022"
        variables = {}
        last_register = None
        last_status_cond = None
        source = None
        with open(self.file_path, "r") as file:
            source = file.read()
        # breakpoint()
        print(f"Parsing {self.file_path} with BashLexParser")
        trees = parser.parse(source)
        for tree in trees:
            print("" * 80)
            print (tree.dump())
        visitor = BashNodeVisitor(tasks)
        for tree in trees:
            visitor.visit(tree)
        return visitor.tasks

