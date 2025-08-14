from .Parser import Parser
from bashlex import parser, ast
import re

class TestVisitor(ast.nodevisitor):
    def __init__(self):
        self.op = None
        self.state = 'lhs'
        self.arg_lhs = None
        self.arg_rhs = None

    def test(self):
        test_return_code = False
        if('$?' == self.arg_lhs):
            self.arg_lhs = '0'
            test_return_code = True
        elif ('$?' == self.arg_rhs):
            self.arg_rhs = '0'
            test_return_code = True
        result = None
        if ('-eq' == self.op):
            result = (self.arg_lhs  == self.arg_rhs)
            result_str = self.arg_lhs  + " == " + self.arg_rhs
        elif ('-ne' == self.op):
            result = (self.arg_lhs  != self.arg_rhs)
            result_str = self.arg_lhs  + " != " + self.arg_rhs
        elif ('-lt' == self.op):
            result = (self.arg_lhs  < self.arg_rhs)
            result_str = self.arg_lhs  + " < " + self.arg_rhs
        elif ('-le' == self.op):
            result = (self.arg_lhs  <= self.arg_rhs)
            result_str = self.arg_lhs  + " <= " + self.arg_rhs
        elif ('-gt' == self.op):
            result = (self.arg_lhs  > self.arg_rhs)
            result_str = self.arg_lhs  + " > " + self.arg_rhs
        elif ('-ge' == self.op):
            result =  (self.arg_lhs  >= self.arg_rhs)
            result_str = self.arg_lhs  + " >= " + self.arg_rhs
        return (test_return_code, result, result_str)

    def __str__(self):
        return (f"TestVisitor(op={self.op}, arg_lhs={self.arg_lhs}, arg_rhs={self.arg_rhs})")
    def visitlist(self, n, parts):
        for part in parts:
            self.visit(part)
        return False
    def visitcommand(self, n, parts):
        for part in parts:
            self.visit(part)
        return False
    def visitword(self, n, word):
        if word == '[' or word == ']':
            # Ignore brackets
            return
        if self.state == 'lhs':
            if ('-eq' == word or
                '-ne' == word or
                '-lt' == word or
                '-le' == word or
                '-gt' == word or
                '-ge' == word):
                self.state = 'rhs'
                self.op = word
            else:
                self.arg_lhs = word
        elif self.state == 'rhs':
            self.arg_rhs = word
    # def visitoperator(self, n, op):
    #     return
    # def visitparameter(self, n, value):
    #     if self.state == 'lhs':
    #         pass # self.arg_lhs = value
    #     elif self.state == 'rhs':
    #         pass #self.arg_rhs = value
class BashNodeVisitor(ast.nodevisitor):
    def __init__(self, tasks):
        self.tasks = tasks
        self.current_umask = "022"
        self.variables = {}
        self.register_names = {}
        self.last_register = None  # Track last registered result

    def umask_to_mode(self, is_dir: bool = True):
        """Convert umask (e.g., '0022') to default mode (e.g., '0755')."""
        try:
            mask = int(self.current_umask, 8)
            default = 0o777 if is_dir else 0o666
            return format(default & ~mask, "04o")
        except Exception:
            return None
        
    def get_register_name(self, name):
        """Generate a unique register name for Ansible."""
        if name not in self.register_names:
            self.register_names[name] = 1
        else:
            self.register_names[name] += 1
        self.last_register = f"{name}_{self.register_names[name]}"
        return self.last_register

    def get_variables(self):
        return self.variables

    def set_variable(self, var: str, value: str):
        value = self.interpret_variable(value)
        self.variables[var] = value

    def interpret_variable(self, stringy: str) -> str:
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
            self.set_variable(var, val)
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
                    # breakpoint()  # Debugging point
                    redir_type = part.type
                    redir_file = part.output.word
            else:
                # Recursively visit other nodes
                self.visit(part)
        command_str = ' '.join(cmd)

        # Match and capture supported commands
        # umask
        m = re.match(r"umask\s+(?P<mask>\d{3,4})", command_str)
        if m:
            self.current_umask = m.group("mask")
            return False

        # mkdir
        m = re.match(r"mkdir\s+(-p\s+)?(?P<path>\S+)", command_str)
        if m:
            mode = self.umask_to_mode(is_dir=True)
            path = self.interpret_variable(m.group("path"))
            self.tasks.append({
                "name": f"Ensure directory {path} exists",
                "ansible.builtin.file": {
                    "path": path,
                    "state": "directory",
                    "mode": mode
                },
                "register": self.get_register_name("mkdir"),
            })
            return False

        # touch
        m = re.match(r"touch\s+(?P<path>\S+)", command_str)
        if m:
            mode = self.umask_to_mode(is_dir=False)
            path = self.interpret_variable(m.group("path"))
            self.tasks.append({
                "name": f"Ensure file {path} exists",
                "ansible.builtin.file": {
                    "path": path,
                    "state": "touch",
                    "mode": mode
                },
                "register": self.get_register_name("touch_file"),   
            })
            return False

        # ln
        m = re.match(r"ln(\s+-s)?\s+(?P<src>\S+)\s+(?P<dest>\S+)", command_str)
        if m:
            is_symlink = bool(m.group(1))
            src = self.interpret_variable(m.group("src"))
            dest = self.interpret_variable(m.group("dest"))
            self.tasks.append({
                "name": f"Create {'symlink' if is_symlink else 'hard link'} {dest} → {src}",
                "ansible.builtin.file": {
                    "src": src,
                    "dest": dest,
                    "state": "link" if is_symlink else "hard"
                },
                "register": self.get_register_name("ln"),
            })
            return False

        # cp
        m = re.match(r"cp\s+(-[a-zA-Z]+\s+)?(?P<src>\S+)\s+(?P<dest>\S+)", command_str)
        if m:
            src = self.interpret_variable(m.group("src"))
            dest = self.interpret_variable(m.group("dest"))
            self.tasks.append({
                "name": f"Copy {src} to {dest}",
                "ansible.builtin.copy": {
                    "src": src,
                    "dest": dest,
                    "remote_src": False
                },
                "register": self.get_register_name("copy_file"),
            })
            return False

        # ldconfig
        if command_str.startswith("ldconfig"):
            self.tasks.append({
                "name": "Run ldconfig",
                "ansible.builtin.shell": "ldconfig",
                "register": self.get_register_name("ldconfig"),
            })
            return False

        # gunzip
        m = re.match(r"gunzip\s+(?P<path>\S+)", command_str)
        if m:
            path = self.interpret_variable(m.group("path"))
            self.tasks.append({
                "name": f"Extract GZ archive {path}",
                "ansible.builtin.unarchive": {
                    "src": path,
                    "remote_src": False,
                    "dest": "/tmp"
                },
                "register": self.get_register_name("extract_gz"),
            })
            return False

        # chmod
        m = re.match(r"chmod\s+(?P<mode>\d+)\s+(?P<path>\S+)", command_str)
        if m:
            mode = m.group("mode")
            path = self.interpret_variable(m.group("path"))
            self.tasks.append({
                "name": f"Set permissions of {path} to {mode}",
                "ansible.builtin.file": {
                    "path": path,
                    "mode": mode
                },
                "register": self.get_register_name("file_persmissions"),
            })
            return False

        # apt update
        if re.match(r"apt(-get)?\s+update", command_str):
            self.tasks.append({
                "name": "Update APT package cache",
                "ansible.builtin.apt": {"update_cache": True},
                "register": self.get_register_name("apt_update"),
            })
            return False

        # apt upgrade
        if re.match(r"apt(-get)?\s+upgrade", command_str):
            self.tasks.append({
                "name": "Upgrade all packages",
                "ansible.builtin.apt": {"upgrade": "dist"},
                "register": self.get_register_name("apt_upgrade"),
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
                },
                "register": self.get_register_name("apt_install"),
            })
            # print(f"Installing packages: {pkgs}")
            return False

        # yum update
        if re.match(r"yum\s+update(\s+-y)?", command_str):
            self.tasks.append({
                "name": "Update YUM package cache",
                "ansible.builtin.yum": {
                    "name": "*", 
                    "state": "latest",
                },
                "register": self.get_register_name("yum_update"),
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
            text = self.interpret_variable(text)
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
            text = self.interpret_variable(text)
            self.tasks.append({
                "name": f"Echo text: {text}",
                "ansible.builtin.debug": {"msg": text}
            })
            return False

        # For every command, if it's not a variable assignment, add a register
        # Only add register for shell commands, not for Ansible builtin tasks
        # For simplicity, register every shell command as "last_result"
        # (You may want to refine this for more accurate mapping)
        # After adding a task, update self.last_register
        # For shell commands not matched above:
        if cmd and not command_str.startswith("echo"):
            self.tasks.append({
                "name": f"Run shell command: {command_str}",
                "shell": command_str,
                "register": self.get_register_name(cmd),
            })

        return False

    def visitif(self, n, parts):
        # Only support two forms:
        # 1. if [ $? -eq 0 ]; then ... fi
        # 2. if [ "$foo" -eq "wibble" ]; then ... fi
        # The test is in n.parts[1], 
        #    body is n.parts[3:]
        print("x" * 80)
        print (n.dump())
        test_node = n.parts[1] # ListNode
        body_nodes = n.parts[3:]
        when_cond = None
        # breakpoint()

        tv = TestVisitor()
        tv.visit(test_node)
        print(tv)

        (test_return_code, result, result_str) = tv.test()
        print(f"Test result: {result}, return code: {test_return_code}, result_str: {result_str}")
        if test_return_code:
            if result:
                when_cond = f"{self.last_register} is succeeded"
            else:
                when_cond = f"{self.last_register} is failed"
        else:
            when_cond = result_str

        # Visit body and add 'when' to each task generated
        before_len = len(self.tasks)
        for part in body_nodes:
            self.visit(part)
        for i in range(before_len, len(self.tasks)):
            if when_cond:
                self.tasks[i]["when"] = when_cond
        return False

class BashLexParser(Parser):
    def __init__(self, file_path=None, script_string=None, config=None):
        super().__init__(file_path=file_path, config=config, script_string=script_string)
    def parse(self):
        """
        https://github.com/idank/bashlex/blob/master/examples/commandsubstitution-remover.py
        """
        tasks = []
        current_command = ""
        current_umask = "022"
        last_register = None
        last_status_cond = None
        source = None
        with open(self.file_path, "r") as file:
            source = file.read()
        # breakpoint()
        #print(f"Parsing {self.file_path} with BashLexParser")
        trees = parser.parse(source)
        #for tree in trees:
        #    print("" * 80)
        #    print (tree.dump())
        visitor = BashNodeVisitor(tasks)
        for tree in trees:
            visitor.visit(tree)
        return visitor.tasks

