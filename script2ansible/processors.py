import os
import sys
import glob
from .parsers import ParserFactory
from .generators import GeneratorFactory
import shutil
import logging


class TaskContainer:
    def __init__(self, name):
        self.name = name
        self.tasks = []

    def add_task(self, task):
        self.tasks.append(task)

    def get_tasks(self):
        return self.tasks

    def clear_tasks(self):
        self.tasks = []

    def empty(self):
        return len(self.tasks) == 0


class Processor:

    def __init__(self, config):
        self.config = config
        self.task_containers = []

    def process(self):
        raise NotImplementedError(
            "Subclasses should implement this method to return tasks."
        )

    def get_tasks(self):
        return self.task_containers

    def get_output_dir(self):
        raise NotImplementedError(
            "Subclasses should implement this method to return tasks."
        )

    def get_role_name(self):
        """
        meh
        """
        raise NotImplementedError(
            "Subclasses should implement this method to return tasks."
        )


class SlackRoleProcessor(Processor):

    def __init__(self, role_dir, role_output_dir, config, **kwargs):
        super().__init__(config)
        self.role_dir = role_dir
        if "role_name" in config:
            self.role_name = config["role_name"]
        else:
            self.role_name = os.path.basename(self.role_dir)
        self.role_output_dir = role_output_dir
        if not os.path.isdir(self.role_dir):
            logging.error(f"Role Directory not found: {self.role_dir}")
            sys.exit(1)

        logging.info(f"Processing Slack role: {self.role_name}")
        self.ansible_role_dir = os.path.join(config["output"], "roles", self.role_name)

    def get_output_dir(self):
        return self.role_output_dir

    def get_role_name(self):
        return self.role_name

    def process(self):
        self.task_containers = []
        script_dir = os.path.join(self.role_dir, "scripts")
        for fname in ("fixfiles", "preinstall", "postinstall"):
            task_container = TaskContainer(fname)
            script_name = os.path.join(script_dir, fname)
            if os.path.isfile(script_name):
                logging.info(f"{script_name} found, processing...")
                parser = ParserFactory.get_parser(
                    file_path=script_name, config=self.config
                )
                task_container.tasks = parser.parse()
            self.task_containers.append(task_container)
        files_dir = os.path.join(self.role_dir, "files")
        task_container = TaskContainer("files")
        self.task_containers.append(task_container)
        for file_name in glob.glob(f"{files_dir}/**/*", recursive=True):
            if os.path.isfile(file_name):
                logging.info(f"{file_name} found, processing...")
                relative_path = os.path.relpath(file_name, files_dir)
                dest_path = os.path.join("/", relative_path)
                build_dest_path = os.path.join(
                    self.ansible_role_dir, "files", relative_path
                )
                build_test_dir = os.path.dirname(build_dest_path)
                logging.info(f"Creating directory: {build_test_dir}")
                os.makedirs(build_test_dir, exist_ok=True)  # mode = ????
                logging.info(f"build copying {file_name} to {build_dest_path}")
                shutil.copyfile(file_name, build_dest_path)
                # add a build task to copy the file to the ansible role/files
                task_container.add_task(
                    self.build_ansible_copy(relative_path, dest_path)
                )
        generator = GeneratorFactory.build_generator(
            self.config["generator"], self, self.config.get("output_format", "yaml")
        )
        generator.generate()

    def build_ansible_copy(self, src, dest):
        logging.info(f"build_ansible_copy {src}  to {dest}")
        return {
            "name": f"Copy {src} to {dest}",
            "ansible.builtin.copy": {
                "src": src,
                "dest": dest,
                "mode": "preserve",
            },
        }


class BashProcessor(Processor):
    def __init__(self, file_name, config):
        super().__init__(config)
        self.file_name = config["input"]
        import logging

        if not os.path.exists(self.file_name):
            logging.error(f"Bash File not found: {self.file_name}")
            sys.exit(1)
        self.output_file = self.config["output"]

    def process(self):
        self.task_containers = []
        self.tasks = []
        task_container = TaskContainer("bash_script")
        parser = ParserFactory.get_parser(file_path=self.file_name, config=self.config)
        task_container.tasks = parser.parse()
        self.task_containers.append(task_container)
        generator = GeneratorFactory.build_generator(
            self.config["generator"], self, self.config.get("output_format", "yaml")
        )
        generator.generate()
