import os
import sys
import glob
from .parsers import ParserFactory
from .generators import GeneratorFactory
from .utility import TaskContainer
import shutil
import logging


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

    @staticmethod
    def build_ansible_copy(src, dest, **kwargs):
        logging.debug(f"build_ansible_copy {src}  to {dest}")

        task = {
            "name": f"Copy {src} to {dest}",
            "ansible.builtin.copy": {
                "src": src,
                "dest": dest,
                "mode": "preserve",
            },
        }
        if kwargs.get('when'):
            task['when'] = kwargs.get('when')
        return task

    def get_output_dir(self):
        return self.role_output_dir

    def get_role_name(self):
        return self.role_name

    # https://www.tutorialspoint.com/python-ndash-move-given-element-to-list-start
    def move_to_start_using_list_comprehension(self, my_list, element):
        return [item for item in my_list if item == element] + [item for item in my_list if item != element]

    def process_files(self):
        """
        See issues.md for dicsussion
        """
        # examples/slack/roles/foo/files/
        #   dirname examples/slack/roles/foo/files
        # examples/slack/roles/foo/files.wibble/
        files_dir = os.path.join(self.role_dir, "files")
        logging.debug(f"files_dir {files_dir}")
        logging.debug(f"self.role_dir {self.role_dir}")

        role_file_dirs = glob.glob(f"{self.role_dir}/files*", recursive=False)
        role_file_dirs = self.move_to_start_using_list_comprehension(role_file_dirs, ' files')
        # for role_file_dir in glob.glob(f"{self.role_dir}/files*", recursive=False):
        for role_file_dir in role_file_dirs:
            logging.debug(f"role_file_dir {role_file_dir}")

            # files.wibble
            # files
            subrole_name = os.path.basename(role_file_dir)
            logging.debug(f"  subrole_name  {subrole_name}")
            if subrole_name == 'files':
                # files
                ans_files_dir_name = subrole_name
                # /tmp/roles/foo/files
                ans_sub_role_files_path = os.path.join(self.ansible_role_dir, "files")
                when = None
            else:
                # NOTE: this is the mapping from slack subrole files dir to
                #       ansible files dir
                # foo.wibble
                ans_files_dir_name = subrole_name.replace('files', self.role_name)

                # /tmp/roles/foo/files/files.wibble
                ans_sub_role_files_path = os.path.join(self.ansible_role_dir, "files", ans_files_dir_name)
                when = f"sub_role is '{ans_files_dir_name}'"

            task_container = TaskContainer(ans_files_dir_name)
            self.task_containers.append(task_container)
            logging.debug(f"  ans_files_dir_name {ans_files_dir_name}")
            logging.debug(f"  ans_sub_role_files_path {ans_sub_role_files_path}")
            # examples/slack/roles/foo/files.wibble/etc
            for file_name in glob.glob(f"{role_file_dir}/*", recursive=False):
                if os.path.isdir(file_name):
                    logging.debug(f"    file_name {file_name} found dir , processing...")
                    # etc
                    relative_path = os.path.relpath(file_name, role_file_dir)
                    logging.debug(f"    relative_path {relative_path}")
                    # where we need to copy it to now
                    build_dest_path = os.path.join(
                        ans_sub_role_files_path, relative_path
                    )
                    logging.debug(f"    build_dest_path {build_dest_path}")
                    shutil.copytree(file_name, build_dest_path, dirs_exist_ok=True, ignore_dangling_symlinks=True)
                    # foo.wibble/etc
                    task_src_path = os.path.join(ans_files_dir_name, relative_path)
                    logging.debug(f"    task_src_path  {task_src_path}")
                    # /etc
                    task_dest_path = os.path.join("/", relative_path)
                    logging.debug(f"    task_dest_path {task_dest_path}")
                    copy_task = self.build_ansible_copy(task_src_path, task_dest_path, when=when)
                    task_container.add_task(
                        copy_task
                    )
        return True

    def process(self):
        self.task_containers = []
        self.process_files()

        script_dir = os.path.join(self.role_dir, "scripts")

        for fname in ("fixfiles", "preinstall", "postinstall"):
            script_name = os.path.join(script_dir, fname)
            if os.path.isfile(script_name):
                # task_container = TaskContainer(fname)
                logging.info(f"{script_name} found, processing...")
                parser = ParserFactory.get_parser(
                    file_path=script_name, config=self.config
                )
                task_container = parser.parse()
                task_container.name = fname
                self.task_containers.append(task_container)
        generator = GeneratorFactory.build_generator(
            self.config["generator"], self, self.config.get("output_format", "yaml")
        )
        generator.generate()


class ScriptProcessor(Processor):
    def __init__(self, file_name, config):
        super().__init__(config)
        self.file_name = config["input"]
        import logging

        if not os.path.exists(self.file_name):
            logging.error(f"Script File not found: {self.file_name}")
            sys.exit(1)
        self.output_file = self.config["output"]

    def process(self):
        self.task_containers = []
        # self.tasks = []
        # task_container = TaskContainer("bash_script")
        parser = ParserFactory.get_parser(file_path=self.file_name, config=self.config)
        task_container = parser.parse()
        task_container.name = "bash_script"
        self.task_containers.append(task_container)
        generator = GeneratorFactory.build_generator(
            self.config["generator"], self, self.config.get("output_format", "yaml")
        )
        generator.generate()
