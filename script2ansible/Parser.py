class Parser:
    def __init__(self, file_path=None, script_string=None, config=None):
        self.file_path = file_path
        self.script_string = script_string
        self.config = config
        self.register_names = {}

    def parse(self):
        raise NotImplementedError(
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
