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
        if self.context:
            for k in self.context.keys():
                self.parent.pop_variable(k)


class CommandVisitor(ast.nodevisitor):
    def __init__(self, parent):
        self.parent = parent
        self.cmd = None
        self.sub_cmd = None  # eg the get in 'apt get'
        self.parsed_args = []
        self.args = []
        self.options = {}
        self.redir_type = None
        self.redir_file = None
        self.is_command = True

    def visitword(self, n, word):
        if self.cmd is None:
            self.cmd = word
        else:
            self.parsed_args.append(word)
        return False

    def visitcommand(self, n, parts):
        for child in n.parts:
            self.visit(child)
        self.process_command()
        return False

    def visitredirect(self, n, input, type, output, heredoc):
        """CommandNode(pos=(258, 289), parts=[
        WordNode(pos=(258, 262), word='echo'),
        WordNode(pos=(263, 271), word='append'),
        RedirectNode(output=
            WordNode(pos=(275, 289), word='/tmp/hello.txt'), pos=(272, 289), type='>>'),
        ])"""
        if type in (">", ">>"):
            # breakpoint()  # Debugging point
            self.redir_type = type
            self.redir_file = output.word
        elif type in ("<",):
            self.redir_type = type
            self.redir_file = input.word

    def visitassignment(self, n, word):
        """.CommandNode(pos=(0, 12), parts=[
        AssignmentNode(pos=(0, 12), word='MYVAR=wibble'),
        ])"""
        if "=" in n.word:
            var, val = n.word.split("=", 1)
            self.parent.set_variable(var, val)

            self.is_command = False
        # self.tasks.append({"_set_var": (var, val)})
        return False

    def visitparameter(self, n, value):
        """
        WordNode(pos=(58, 71), word='/tmp/bar_${s}', parts=[
            ParameterNode(pos=(67, 71), value='s'),
        ]),
        """
        pass

    def process_args(self, spec):

        ov = spec.get("ov", {})
        o = spec.get("o", {})
        sub_cmd = spec.get("sub_cmd", {})

        self.options = {}
        self.args = []
        prev = None
        for index, arg in enumerate(self.parsed_args):
            # if arg.startswith('-'):
            if index == 0 and (arg in sub_cmd):
                self.sub_cmd = arg
                continue
            if arg in o:
                self.options[arg] = 1
                prev = None
            elif arg in ov:
                prev = arg
            elif prev is not None:
                self.options[prev] = arg
                prev = None
            else:
                self.args.append(arg)
        return True

    def process_command(self):

        specs = {
            "cp": {
                "ov": set(),
                "o": {
                    "-r",
                },
            },
            "ln": {
                "ov": set(),
                "o": {
                    "-s",
                },
            },
            "scp": {
                "ov": {
                    "-i",
                    "-P",
                },
                "o": {
                    "-r",
                },
            },
            "chmod": {
                "ov": set(),
                "o": {
                    "-R",
                    "-f",
                    "-v",
                },
            },
            "chown": {
                "ov": set(),
                "o": {
                    "-R",
                    "-f",
                    "-v",
                    "-c",
                },
            },
            "umask": {
                "ov": set(),
                "o": set(),
            },
            "mkdir": {
                "ov": set(),
                "o": {
                    "-p",
                },
            },
            "ldconfig": {
                "ov": set(),
                "o": set(),
            },
            "gunzip": {
                "ov": set(),
                "o": set(),
            },
            "apt": {
                "sub_cmd": {"update", "install", "upgrade"},
                "ov": set(),
                "o": {"-y", "update", "install", "upgrade"},  # meh
            },
            "apt-get": {
                "sub_cmd": {"update", "install", "upgrade"},
                "ov": set(),
                "o": {"-y", "update", "install", "upgrade"},  # meh
            },
            "yum": {
                "sub_cmd": {"update", "install", "upgrade"},
                "ov": set(),
                "o": {"-y", "update", "install", "upgrade"},  # meh
            },
            "echo": {
                "ov": set(),
                "o": {
                    "-y",
                },
            },
            "touch": {
                "ov": set(),
                "o": {"-a", "-c"},
            },
        }
        if self.is_command:
            if self.cmd not in specs:
                breakpoint()
                print(f" failed to find {self.cmd}")
            else:
                spec = specs[self.cmd]
                self.process_args(spec)
            # print(f"---- finishing {self.cmd} ")
        else:
            pass
            # print(f"---- finishing  assignment ")


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
        if self.state == "done":
            for loop_var in self.loop_vars:
                context = {}
                context[self.for_var] = loop_var
                for command in self.commands:
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


class BashScriptVisitor(ast.nodevisitor):
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
        if var in self.stack_variables:
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
        return False

    def visitcommand(self, n, parts, context=None):
        # scoped_vars = ScopedVariables(self, context)  # noqa: F841
        cv = CommandVisitor(self)
        cv.visit(n)
        if "umask" == cv.cmd:
            self.current_umask = cv.args[0]
            return False
        elif "mkdir" == cv.cmd:
            arg_path = cv.args[0]
            mode = self.umask_to_mode(is_dir=True)
            path = self.interpret_variable(arg_path)
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
        elif "touch" == cv.cmd:
            arg_path = cv.args[0]
            mode = self.umask_to_mode(is_dir=False)
            path = self.interpret_variable(arg_path)
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
        elif "ln" == cv.cmd:
            is_symlink = "-s" in cv.options
            src = self.interpret_variable(cv.args[0])
            dest = self.interpret_variable(cv.args[1])
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
        elif "cp" == cv.cmd:
            src = self.interpret_variable(cv.args[0])
            dest = self.interpret_variable(cv.args[1])
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
        elif "scp" == cv.cmd:
            # scp_options = cv.options
            remote_pattern = re.compile(
                r"^(?:(?P<user>[^@]+)@)?(?P<host>[^:]+):(?P<path>.+)$"
            )

            def split_target(target):
                rm = remote_pattern.match(target)
                if rm:
                    return rm.groupdict()
                else:
                    return {"user": None, "host": None, "path": target}

            scp_src = split_target(cv.args[0])
            # NOTE scp '-r'      Recursively copy entire directories.  Note that scp follows symbolic links encountered in the tree traversal.
            # NOTE ansible.builtin.copy 'src'
            # If path is a directory, it is copied recursively. In this case,
            # if path ends with /, only inside contents of that directory are copied to
            # destination. Otherwise, if it does not end with /, the directory itself
            # with all contents is copied. This behavior is similar to the rsync command line tool.
            scp_dest = split_target(cv.args[1])

            # TODO compare and contrast:
            # self.pull &&
            # scp_src['remote_host']
            # scp_dest['remote_host']
            # and and look at options
            validate_request = {"op": "scp"}
            if bool(scp_src.get("host")):
                validate_request["src_host"] = True
            if bool(scp_dest.get("host")):
                validate_request["dest_host"] = True
            # breakpoint()
            validate_response = self.parser.validate_command(validate_request)
            if "accept" == validate_response["status"]:
                self.tasks.append(
                    {
                        "name": f"Scp {scp_src['path']} to {scp_dest['path']}",
                        "ansible.builtin.copy": {
                            "src": scp_src["path"],
                            "dest": scp_dest["path"],
                            "remote_src": False,
                        },
                        "register": self.get_register_name(cv.cmd),
                    }
                )
            else:
                print(f"scp skipping command {cv.cmd}")
        elif "mv" == cv.cmd:
            src = self.interpret_variable(cv.args[0])
            dest = self.interpret_variable(cv.args[1])
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
        elif "ldconfig" == cv.cmd:
            reg_name = self.get_register_name("ldconfig")
            self.tasks.append(
                {
                    "name": "Run ldconfig",
                    "ansible.builtin.command": "ldconfig",
                    "register": reg_name,
                    "changed_when": f"'changed' in {reg_name}.stdout or 'updated' in {reg_name}.stdout",
                }
            )
        elif "gunzip" == cv.cmd:
            path = self.interpret_variable(cv.args[0])
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
        elif "chown" == cv.cmd:
            (owner, group) = cv.args[0].split(":")
            path = self.interpret_variable(cv.args[1])
            recursive = "-R" in cv.options
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
        elif "chmod" == cv.cmd:
            mode = self.interpret_variable(cv.args[0])
            path = self.interpret_variable(cv.args[1])
            # n_num = re.match(f"(?P<mode>\d+)", mode, )
            # m_sym = re.match(r"(?P<mode>[ugoa]+[+-=][rwx]+)", mode, )
            recursive = "-R" in cv.options
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
        elif cv.cmd in ("apt", "apt-get", "yum"):
            ans_builtin = "yum" if cv.cmd == "yum" else "apt"
            sub_command = cv.sub_cmd
            if sub_command == "update":
                self.tasks.append(
                    {
                        "name": "Update APT package cache",
                        f"ansible.builtin.{ans_builtin}": {"update_cache": True},
                        "register": self.get_register_name(f"{cv.cmd}_{sub_command}"),
                    }
                )
            elif sub_command == "upgrade":
                self.tasks.append(
                    {
                        "name": "Upgrade all packages",
                        f"ansible.builtin.{ans_builtin}": {"upgrade": "dist"},
                        "register": self.get_register_name(f"{cv.cmd}_{sub_command}"),
                    }
                )
            elif sub_command == "install":
                packages = " ".join(cv.args)
                self.tasks.append(
                    {
                        "name": f"Install packages: {packages}",
                        f"ansible.builtin.{ans_builtin}": {
                            "name": packages,
                            "state": "present",
                            "update_cache": True,
                        },
                        "register": self.get_register_name(f"{cv.cmd}_{sub_command}"),
                    }
                )
        elif "echo" == cv.cmd:
            text = cv.args[0]
            if cv.redir_type in (">", ">>"):
                redir_type = cv.redir_type
                redir_file = self.interpret_variable(cv.redir_file)
                if redir_type == ">":
                    self.tasks.append(
                        {
                            "name": f"Write text to {redir_file}",
                            "ansible.builtin.copy": {
                                "dest": redir_file,
                                "content": text,
                            },
                            "register": self.get_register_name("echo_redirect"),
                        }
                    )
                else:  # >>
                    mode = self.umask_to_mode(is_dir=False)
                    self.tasks.append(
                        {
                            "name": self.interpret_variable(
                                f"Append text to {redir_file}"
                            ),
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
            else:
                text = self.interpret_variable(text)
                self.tasks.append(
                    {
                        "name": f"Echo text: {text}",
                        "ansible.builtin.debug": {"msg": text},
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
        trees = parser.parse(source)

        visitor = BashScriptVisitor(tasks, self)
        for tree in trees:
            visitor.visit(tree)
        return visitor.tasks
