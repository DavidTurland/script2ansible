# from script2ansible import config


class Parser:
    def __init__(self, file_path=None, script_string=None, config={}):
        self.file_path = file_path
        self.script_string = script_string
        self.config = config
        self.register_names = {}
        self.pull = config.get("pull", False)
        self.push = config.get("push", False)
        self.root = config.get("root", '/')
        self.stage = config.get("stage", '/tmp/s2a_stage')
        self.hostname = config.get("hostname", 'localhost')
        self.verbose = config.get("verbose", "1")

    def parse(self):
        raise NotImplementedError(  # pragma: no cover
            "Subclasses should implement this method to parse the script."
        )

    def get_register_name(self, name):
        """Generate a unique register name for Ansible."""
        if "role_name" in self.config:
            name = f"{self.config['role_name']}_{name}"
        if name not in self.register_names:
            self.register_names[name] = 1
        else:
            self.register_names[name] += 1
        return f"{name}_{self.register_names[name]}"

    def get_env(self):
        return {"ROOT": self.root,
                "STAGE": self.stage,
                "HOSTNAME": self.hostname,
                "VERBOSE": '1' if self.verbose else '0',
                }

    def validate_command(self, command={}):
        """
         Initial Use case is validating scp,ssh,rsync etc where the
         source or target might be on a remote host
         This may morph but the intention is that this will validate
         commands and accept, reject, or suggest replacement
        """
        op = command['op']

        response = {"status": "accept"}
        # breakpoint()
        if op in ('scp', 'rsync'):
            if 'src_host' in command and not self.pull:
                response["status"] = 'reject'
            if 'dest_host' in command and not self.push:
                response["status"] = 'reject'
        elif op in ('ssh'):
            pass

        return response
