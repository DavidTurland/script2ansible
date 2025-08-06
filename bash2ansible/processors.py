import os
import sys
from .core import translate_to_ansible, parse_bash_script
from .generators import generate_playbook

class SlackRoleProcessor:

    def __init__(self, role_dir, config):
        self.role_dir = role_dir
        self.config = config
        if not os.path.isdir(self.role_dir):
            print(f"❌ Role Directory not found: {self.role_dir}")
            sys.exit(1)
   
    def process(self):
        script_dir = os.path.join(self.role_dir,'scripts' )
        for fname in ('preinstall','postinstall'):
            script_name = os.path.join(script_dir,fname)
            if (os.path.isfile(script_name)):
                print(f"{script_name} found, processing...")

class BashProcessor:

    def __init__(self, file_name, config):
        self.file_name = config["input"]
        if not os.path.exists(self.file_name):
            print(f"❌ Bash File not found: {self.file_name}")
            sys.exit(1)
        self.output_file = config["output"]
        self.config = config

    def process(self):
        tasks = parse_bash_script(self.file_name, self.config)
        if not tasks:
            print("⚠️ No tasks generated.")
            sys.exit(0)

        output = generate_playbook(tasks, self.config["output_format"])
        with open(self.output_file, 'w') as f:
            f.write(output)