from .Parser import Parser
from bashlex import parser, ast
import re


class ScopedVariables:
    def __init__(self, parent, context):
        self.parent = parent
        self.context = context
        if self.context:
            for k, v in context.items():
                parent.push_variable(k, v)

    def __del__(self):
        # breakpoint()
        if self.context:
            for k in self.context.keys():
                self.parent.pop_variable(k)


class IfVisitor(ast.nodevisitor):
    """
        visit 'if' loops

        spawn a visitor:
        maintain state based on ReservedwordNode (update state in visitreserved):
        if state:
            in visitword: capture lhs , op and rhs based on test_state
        then state:
            accrue commands in visitcommand
        fi state:



    IfNode(pos=(290, 334), parts=[
      ReservedwordNode(pos=(290, 292), word='if'),
      ListNode(pos=(293, 306), parts=[
          CommandNode(pos=(293, 305), parts=[
            WordNode(pos=(293, 294), word='['),
            WordNode(pos=(295, 297), word='$?', parts=[
              ParameterNode(pos=(295, 297), value='?'),
            ]),
            WordNode(pos=(298, 301), word='-eq'),
            WordNode(pos=(302, 303), word='0'),
            WordNode(pos=(304, 305), word=']'),
          ]),
          OperatorNode(op=';', pos=(305, 306)),
        ]),
      ReservedwordNode(pos=(307, 311), word='then'),
      CommandNode(pos=(314, 331), parts=[
        WordNode(pos=(314, 319), word='touch'),
        WordNode(pos=(320, 331), word='/tmp/ok.txt'),
      ]),
      ReservedwordNode(pos=(332, 334), word='fi'),
    ])
    """

    def __init__(self, parent):
        self.parent = parent
        self.state = None
        self.test_state = "lhs"
        self.commands = []

    def get_commands(self):
        return self.commands

    def process_test(self):
        test_return_code = False
        if "$?" == self.arg_lhs:
            self.arg_lhs = "0"
            test_return_code = True
        elif "$?" == self.arg_rhs:
            self.arg_rhs = "0"
            test_return_code = True
        result = None
        if "-eq" == self.op:
            result = self.arg_lhs == self.arg_rhs
            result_str = self.arg_lhs + " == " + self.arg_rhs
        elif "-ne" == self.op:
            result = self.arg_lhs != self.arg_rhs
            result_str = self.arg_lhs + " != " + self.arg_rhs
        elif "-lt" == self.op:
            result = self.arg_lhs < self.arg_rhs
            result_str = self.arg_lhs + " < " + self.arg_rhs
        elif "-le" == self.op:
            result = self.arg_lhs <= self.arg_rhs
            result_str = self.arg_lhs + " <= " + self.arg_rhs
        elif "-gt" == self.op:
            result = self.arg_lhs > self.arg_rhs
            result_str = self.arg_lhs + " > " + self.arg_rhs
        elif "-ge" == self.op:
            result = self.arg_lhs >= self.arg_rhs
            result_str = self.arg_lhs + " >= " + self.arg_rhs
        self.result = result
        self.test_return_code = test_return_code
        self.result_str = result_str

    def visitreservedword(self, n, word):
        self.state = word
        if self.state == "then":
            # can process test
            self.process_test()
        elif self.state == "fi":
            # can process body
            pass

    def visitword(self, n, word):
        if self.state == "if":
            if word == "[" or word == "]":
                # Ignore brackets
                return
            if self.test_state == "lhs":
                if word in ("-eq", "-ne", "-lt", "-le", "-gt", "-ge"):
                    self.test_state = "rhs"
                    self.op = word
                else:
                    # maybe +=
                    self.arg_lhs = word
            elif self.test_state == "rhs":
                # maybe +=
                self.arg_rhs = word
        else:
            return

    def visitcommand(self, n, parts):
        if self.state == "then":
            self.commands.append(n)
            return False
        return True


class ForVisitor(ast.nodevisitor):
    """
        Handle 'for' loops in bash scripts.
        n: the for node
        parts: child nodes

        spawn a visitor:
        maintain state based on ReservedwordNode (update state in visitreserved):
        for state:
            in visitword: capture WordNode as var
        in state:
            in visitword: capture WordNode's as valuesvar
        do state:
            visitcommand as normal(?)
        done:
            wrap-up

    [ReservedwordNode(pos=(1, 4) word='for'),
     WordNode(parts=[] pos=(5, 6) word='s'),
     ReservedwordNode(pos=(7, 9) word='in'),
     WordNode(parts=[] pos=(10, 17) word='server1'),
     WordNode(parts=[] pos=(18, 25) word='server2'),
     WordNode(parts=[] pos=(26, 33) word='server3'),
     ReservedwordNode(pos=(34, 36) word='do'),
     CommandNode(parts=[WordNode(parts=[] pos=(41, 43) word='cp'), WordNode(parts=[ParameterNode(pos=(49, 53) value='s')] pos=(44, 57) word='/tmp/${s}.txt'), WordNode(parts=[ParameterNode(pos=(67, 71) value='S')] pos=(58, 71) word='/tmp/bar_${S}')] pos=(41, 71)),
     ReservedwordNode(pos=(72, 76) word='done')]

    """

    def __init__(self, parent):
        self.parent = parent
        self.state = None
        self.for_var = None
        self.loop_vars = []
        self.commands = []

    def visitreservedword(self, n, word):
        self.state = word
        if self.state == "do":
            pass
            # self.parent.push_var()
        elif self.state == "done":
            for loop_var in self.loop_vars:
                context = {}
                context[self.for_var] = loop_var
                for command in self.commands:
                    # breakpoint()
                    self.parent.visitcommand(command, command.parts, context=context)

    def visitlist(self, n, parts):
        for part in parts:
            self.visit(part)
        return False

    def visitcommand(self, n, parts):
        if self.state == "do":
            self.commands.append(n)

        else:
            breakpoint()
        return False

    def visitword(self, n, word):
        if self.state == "for":
            self.for_var = word
        elif self.state == "in":
            self.loop_vars.append(word)
        elif self.state == "done":
            pass


class BashNodeVisitor(ast.nodevisitor):
    def __init__(self, tasks, parser):
        self.tasks = tasks
        self.current_umask = "022"
        self.variables = {}
        self.stack_variables = {}
        self.register_names = {}
        self.parser = parser
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
        """
        Generate a unique register name for Ansible.
        TODO: this should be a generator thing maybe?
        """
        # breakpoint()
        self.last_register = self.parser.get_register_name(name)
        return self.last_register

    def get_variables(self):
        return self.variables

    def get_variable(self, var, default=None):
        if var in self.stack_variables:
            return self.stack_variables[var]
        return self.variables.get(var, default)

    def set_variable(self, var: str, value: str):
        value = self.interpret_variable(value)
        self.variables[var] = value

    def push_variable(self, var: str, value: str):
        """
        sets a scoped variable
        """
        self.stack_variables[var] = value

    def pop_variable(self, var: str):
        """
        deletes a scoped variable
        """
        del self.stack_variables[var]

    def interpret_variable(self, stringy: str, type: str = "interpret") -> str:
        def replace_var(match):
            var = match.group("var")
            return self.get_variable(var, match.group(0))

        def jinja_var(match):
            var = match.group("var")
            return f"{{{{ {var} }}}}"

        if type == "interpret":
            replacer = replace_var
        elif type == "jinja":
            replacer = jinja_var

        # Replace ${VAR} style
        stringy = re.sub(r"\$\{(?P<var>[A-Za-z_][A-Za-z0-9_]*)\}", replacer, stringy)

        # Replace $VAR style (only if followed by non-word char or end-of-line)
        return re.sub(r"\$(?P<var>\w+)\b", replacer, stringy)

    def visitassignment(self, n, parts):
        if "=" in n.word:
            var, val = n.word.split("=", 1)
            self.set_variable(var, val)
        # self.tasks.append({"_set_var": (var, val)})
        return False

    def visitcommand(self, n, parts, context=None):
        # Build the command string from parts
        cmd = []
        redir_type = None
        redir_file = None

        scoped_vars = ScopedVariables(self, context)  # noqa: F841

        for part in parts:
            if part.kind == "word":
                cmd.append(part.word)
            elif part.kind == "redirect":
                # Only handle > and >> for echo
                if part.type in (">", ">>"):
                    # breakpoint()  # Debugging point
                    redir_type = part.type
                    redir_file = part.output.word
            else:
                # Recursively visit other nodes
                self.visit(part)
        command_str = " ".join(cmd)

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
            self.tasks.append(
                {
                    "name": f"Ensure directory {path} exists",
                    "ansible.builtin.file": {
                        "path": path,
                        "state": "directory",
                        "mode": mode,
                    },
                    "register": self.get_register_name("mkdir"),
                }
            )
            return False

        # touch
        m = re.match(r"touch\s+(?P<path>\S+)", command_str)
        if m:
            mode = self.umask_to_mode(is_dir=False)
            path = self.interpret_variable(m.group("path"))
            self.tasks.append(
                {
                    "name": f"Ensure file {path} exists",
                    "ansible.builtin.file": {
                        "path": path,
                        "state": "touch",
                        "mode": mode,
                    },
                    "register": self.get_register_name("touch_file"),
                }
            )
            return False

        # ln
        m = re.match(r"ln(\s+-s)?\s+(?P<src>\S+)\s+(?P<dest>\S+)", command_str)
        if m:
            is_symlink = bool(m.group(1))
            src = self.interpret_variable(m.group("src"))
            dest = self.interpret_variable(m.group("dest"))
            # TODO directory?
            mode = self.umask_to_mode(is_dir=False)
            self.tasks.append(
                {
                    "name": f"Create {'symlink' if is_symlink else 'hard link'} {dest} → {src}",
                    "ansible.builtin.file": {
                        "src": src,
                        "dest": dest,
                        "state": "link" if is_symlink else "hard",
                        "mode": mode,
                    },
                    "register": self.get_register_name("ln"),
                }
            )
            return False

        # cp
        m = re.match(r"cp\s+(-[a-zA-Z]+\s+)?(?P<src>\S+)\s+(?P<dest>\S+)", command_str)
        if m:
            src = self.interpret_variable(m.group("src"))
            dest = self.interpret_variable(m.group("dest"))
            self.tasks.append(
                {
                    "name": f"Copy {src} to {dest}",
                    "ansible.builtin.copy": {
                        "src": src,
                        "dest": dest,
                        "remote_src": False,
                    },
                    "register": self.get_register_name("copy_file"),
                }
            )
            return False
        # mv
        m = re.match(r"mv\s+(?P<src>\S+)\s+(?P<dest>\S+)", command_str)
        if m:
            src = self.interpret_variable(m.group("src"))
            dest = self.interpret_variable(m.group("dest"))
            command_str = f"mv {src} {dest}"
            self.tasks.append(
                {
                    "name": f"Run shell command: {command_str}",
                    "shell": command_str,
                    "creates": dest,
                    "removes": src,
                    "register": self.get_register_name("mv"),
                }
            )
            # self.tasks.append(
            #     {
            #         "name": f"Copy {src} to {dest}",
            #         "ansible.builtin.copy": {
            #             "src": src,
            #             "dest": dest,
            #             "remote_src": False,
            #         },
            #         "register": self.get_register_name("copy_file"),
            #     }
            # )
            return False

        # ldconfig
        if command_str.startswith("ldconfig"):
            reg_name = self.get_register_name("ldconfig")
            self.tasks.append(
                {
                    "name": "Run ldconfig",
                    "ansible.builtin.command": "ldconfig",
                    "register": reg_name,
                    "changed_when": f"'changed' in {reg_name}.stdout or 'updated' in {reg_name}.stdout",
                }
            )
            return False

        # gunzip
        m = re.match(r"gunzip\s+(?P<path>\S+)", command_str)
        if m:
            path = self.interpret_variable(m.group("path"))
            self.tasks.append(
                {
                    "name": f"Extract GZ archive {path}",
                    "ansible.builtin.unarchive": {
                        "src": path,
                        "remote_src": False,
                        "dest": "/tmp",
                    },
                    "register": self.get_register_name("extract_gz"),
                }
            )
            return False

        # chmod with numeric mode (e.g., chmod 0700 /path)
        m = re.match(r"chmod\s+(?P<mode>\d+)\s+(?P<path>\S+)", command_str)
        if m:
            mode = m.group("mode")
            path = self.interpret_variable(m.group("path"))
            self.tasks.append(
                {
                    "name": f"Set permissions of {path} to {mode}",
                    "ansible.builtin.file": {"path": path, "mode": mode},
                    "register": self.get_register_name("file_permissions"),
                }
            )
            return False

        # chmod with optional -R (recursive), numeric mode
        m = re.match(
            r"chmod\s+(?P<recursive>-R\s+)?(?P<mode>\d+)\s+(?P<path>\S+)", command_str
        )
        if m:
            mode = m.group("mode")
            path = self.interpret_variable(m.group("path"))
            recursive = bool(m.group("recursive"))
            task = {
                "name": f"Set permissions of {path} to {mode}"
                + (" recursively" if recursive else ""),
                "ansible.builtin.file": {"path": path, "mode": mode},
                "register": self.get_register_name(
                    "file_permissions" + ("_recursive" if recursive else "")
                ),
            }
            if recursive:
                task["ansible.builtin.file"]["recurse"] = True
            self.tasks.append(task)
            return False

        # chmod with optional -R (recursive), symbolic mode
        m = re.match(
            r"chmod\s+(?P<recursive>-R\s+)?(?P<mode>[ugoa]+[+-=][rwx]+)\s+(?P<path>\S+)",
            command_str,
        )
        if m:
            mode = m.group("mode")
            path = self.interpret_variable(m.group("path"))
            recursive = bool(m.group("recursive"))
            task = {
                "name": f"Set symbolic permissions of {path} to {mode}"
                + (" recursively" if recursive else ""),
                "ansible.builtin.file": {"path": path, "mode": mode},
                "register": self.get_register_name(
                    "file_permissions_symbolic" + ("_recursive" if recursive else "")
                ),
            }
            if recursive:
                task["ansible.builtin.file"]["recurse"] = True
            self.tasks.append(task)
            return False

        # chown with optional -R (recursive), symbolic mode
        m = re.match(
            r"chown\s+(?P<recursive>-R\s+)?(?P<owner>\w+):(?P<group>\w+)\s+(?P<path>\S+)",
            command_str,
        )
        if m:
            owner = m.group("owner")
            group = m.group("group")

            path = self.interpret_variable(m.group("path"))
            recursive = bool(m.group("recursive"))
            task = {
                "name": f"Set owner: group of {owner} :{group}"
                + (" recursively" if recursive else ""),
                "ansible.builtin.file": {"path": path, "owner": owner, "group": group},
                "register": self.get_register_name(
                    "chown" + ("_recursive" if recursive else "")
                ),
            }
            if recursive:
                task["ansible.builtin.file"]["recurse"] = True
            self.tasks.append(task)
            return False

        # apt update
        if re.match(r"apt(-get)?\s+update", command_str):
            self.tasks.append(
                {
                    "name": "Update APT package cache",
                    "ansible.builtin.apt": {"update_cache": True},
                    "register": self.get_register_name("apt_update"),
                }
            )
            return False

        # apt upgrade
        if re.match(r"apt(-get)?\s+upgrade", command_str):
            self.tasks.append(
                {
                    "name": "Upgrade all packages",
                    "ansible.builtin.apt": {"upgrade": "dist"},
                    "register": self.get_register_name("apt_upgrade"),
                }
            )
            return False

        # apt install (support optional --assume-yes or -y)
        m = re.match(
            r"apt(-get)?\s+install\s+(--assume-yes\s+|-y\s+)?(?P<packages>.+)",
            command_str,
        )
        if m:
            pkgs = m.group("packages").split()
            self.tasks.append(
                {
                    "name": f"Install packages: {' '.join(pkgs)}",
                    "ansible.builtin.apt": {
                        "name": pkgs,
                        "state": "present",
                        "update_cache": True,
                    },
                    "register": self.get_register_name("apt_install"),
                }
            )
            return False

        # yum update
        if re.match(r"yum\s+update(\s+-y)?", command_str):
            self.tasks.append(
                {
                    "name": "Update YUM package cache",
                    "ansible.builtin.yum": {
                        "name": "*",
                        "state": "latest",
                    },
                    "register": self.get_register_name("yum_update"),
                }
            )
            return False

        # yum install
        m = re.match(r"yum\s+install\s+(-y\s+)?(?P<packages>.+)", command_str)
        if m:
            pkgs = m.group("packages").split()
            self.tasks.append(
                {
                    "name": f"Install packages: {' '.join(pkgs)}",
                    "ansible.builtin.yum": {"name": pkgs, "state": "present"},
                    "register": self.get_register_name("yum_install"),
                }
            )
            return False

        # echo with redirect
        m = re.match(r'echo\s+(?P<text>".+?"|\'.+?\'|.+)', command_str)
        if m and redir_type and redir_file:
            text = m.group("text").strip("\"'")
            text = self.interpret_variable(text)
            if redir_type == ">":
                self.tasks.append(
                    {
                        "name": f"Write text to {redir_file}",
                        "ansible.builtin.copy": {"dest": redir_file, "content": text},
                        "register": self.get_register_name("echo_redirect"),
                    }
                )
            else:  # >>
                mode = self.umask_to_mode(is_dir=False)
                self.tasks.append(
                    {
                        "name": self.interpret_variable(f"Append text to {redir_file}"),
                        "ansible.builtin.lineinfile": {
                            "path": redir_file,
                            "line": text,
                            "create": True,
                            "insertafter": "EOF",
                            "mode": mode,
                        },
                        "register": self.get_register_name("echo_redirect_append"),
                    }
                )
            return False

        # echo without redirect
        m = re.match(r'echo\s+(?P<text>".+?"|\'.+?\'|.+)', command_str)
        if m and not redir_type:
            text = m.group("text").strip("\"'")
            text = self.interpret_variable(text)
            self.tasks.append(
                {"name": f"Echo text: {text}", "ansible.builtin.debug": {"msg": text}}
            )
            return False

        # For every command, if it's not a variable assignment, add a register
        # Only add register for shell commands, not for Ansible builtin tasks
        # For simplicity, register every shell command as "last_result"
        # (You may want to refine this for more accurate mapping)
        # After adding a task, update self.last_register
        # For shell commands not matched above:
        if cmd and not command_str.startswith("echo"):
            self.tasks.append(
                {
                    "name": f"Run shell command: {command_str}",
                    "shell": command_str,
                    "register": self.get_register_name(cmd),
                }
            )

        return False

    def visitif(self, n, parts):
        # Only support two forms:
        # 1. if [ $? -eq 0 ]; then ... fi
        # 2. if [ "$foo" -eq "wibble" ]; then ... fi
        # The test is in n.parts[1],
        #    body is n.parts[3:]
        # when_cond = None
        # breakpoint()

        # tv = TestVisitor()
        # tv.visit(test_node)
        # print(tv)

        # (test_return_code, result, result_str) = tv.test()

        iv = IfVisitor(self)
        iv.visit(n)
        test_return_code = iv.test_return_code
        result = iv.result
        result_str = iv.result_str

        print(
            f"Test result: {result}, return code: {test_return_code}, result_str: {result_str}"
        )
        if test_return_code:
            if result:
                when_cond = f"{self.last_register} is succeeded"
            else:
                when_cond = f"{self.last_register} is failed"
        else:
            when_cond = result_str

        body_nodes = iv.get_commands()

        # Visit body and add 'when' to each task generated
        before_len = len(self.tasks)
        for part in body_nodes:
            self.visit(part)
        for i in range(before_len, len(self.tasks)):
            if when_cond:
                self.tasks[i]["when"] = when_cond
        return False

    def visitfor(self, n, parts):
        for_visitor = ForVisitor(self)
        for_visitor.visit(n)


class BashLexParser(Parser):
    def __init__(self, file_path=None, script_string=None, config=None):
        super().__init__(
            file_path=file_path, config=config, script_string=script_string
        )

    def parse(self):
        """
        https://github.com/idank/bashlex/blob/master/examples/commandsubstitution-remover.py
        """
        tasks = []
        source = None
        if self.file_path:
            with open(self.file_path, "r") as file:
                source = file.read()
        else:
            source = self.script_string
        # breakpoint()
        # print(f"Parsing {self.file_path} with BashLexParser")
        trees = parser.parse(source)

        visitor = BashNodeVisitor(tasks, self)
        for tree in trees:
            visitor.visit(tree)
        return visitor.tasks
        return visitor.tasks
