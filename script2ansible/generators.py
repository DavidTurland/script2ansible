import json
import yaml
import os


class IndenterDumper(yaml.Dumper):
    """Custom YAML dumper to handle indentation correctly.
    at least it keeps ansible lint happy
    """

    def increase_indent(self, flow=False, indentless=False):
        return super(IndenterDumper, self).increase_indent(flow, False)


class GeneratorRole:
    def __init__(self, processor, output_format="yaml"):
        self.processor = processor
        self.output_format = output_format

    def create_role_structure(self):
        """Create standard directories and stub files for an Ansible role."""
        role_dir = self.processor.get_output_dir()
        dirs = [
            "tasks",
            "handlers",
            "files",
            "templates",
            "vars",
            "defaults",
            "meta",
        ]
        for d in dirs:
            os.makedirs(os.path.join(role_dir, d), exist_ok=True)
        # Create stub main.yml files if not present
        stub_content = "# This is a stub file for Ansible role\n"
        for d in ["tasks", "handlers", "vars", "defaults", "meta"]:
            stub_file = os.path.join(role_dir, d, "main.yml")
            if not os.path.exists(stub_file):
                with open(stub_file, "w") as f:
                    f.write(stub_content)

    def generate(self):
        task_containers = self.processor.get_tasks()
        self.create_role_structure()

        tasks_dir = os.path.join(self.processor.get_output_dir(), "tasks")
        os.makedirs(tasks_dir, exist_ok=True)
        main_tasks = []
        variables = []
        for task_container in task_containers:
            if not task_container.get_tasks():
                continue
            variables += task_container.variables
            tasks_name = task_container.name
            tasks = task_container.get_tasks()
            output = (
                json.dumps(tasks, indent=2)
                if self.output_format == "json"
                else yaml.dump(
                    tasks,
                    sort_keys=False,
                    Dumper=IndenterDumper,
                    default_flow_style=False,
                )
            )
            ofile_name = os.path.join(
                self.processor.get_output_dir(), "tasks", f"{tasks_name}.yml"
            )
            with open(ofile_name, "w") as f:
                f.write(output)
            main_tasks.append({'include_tasks': f"{tasks_name}.yml"})
        output = (
                json.dumps(main_tasks, indent=2)
                if self.output_format == "json"
                else yaml.dump(
                    main_tasks,
                    sort_keys=False,
                    Dumper=IndenterDumper,
                    default_flow_style=False,
                )
        )
        ofile_name = os.path.join(
            self.processor.get_output_dir(), "tasks", "main.yml"
        )
        with open(ofile_name, "w") as f:
            f.write(output)
        if len(variables):
            vars_filename = os.path.join(self.processor.get_output_dir(), "vars","vars.yml")
            with open(vars_filename, 'w') as outfile:
                yaml.dump(variables, outfile, default_flow_style=False)

class GeneratorRoleTasks:
    def __init__(self, processor, output_format="yaml"):
        self.processor = processor
        self.output_format = output_format

    def generate(self):
        task_containers = self.processor.get_tasks()
        for task_container in task_containers:
            if not task_container.get_tasks():
                continue
            tasks = task_container.get_tasks()
            output = (
                json.dumps(tasks, indent=2)
                if self.output_format == "json"
                else yaml.dump(
                    tasks,
                    sort_keys=False,
                    Dumper=IndenterDumper,
                    default_flow_style=False,
                )
            )
            with open(self.processor.output_file, "w") as f:
                f.write(output)


class GeneratorPlaybook:
    def __init__(self, processor, output_format="yaml"):
        self.processor = processor
        self.output_format = output_format

    def generate(self):
        task_containers = self.processor.get_tasks()
        playbook = [
            {
                "name": "Execute translated shell commands",
                "hosts": "all",
                "become": True,
                "tasks": task_containers[0].get_tasks() if task_containers else [],
            }
        ]
        output = (
            json.dumps(playbook, indent=2)
            if self.output_format == "json"
            else yaml.dump(
                playbook,
                sort_keys=False,
                Dumper=IndenterDumper,
                default_flow_style=False,
            )
        )
        with open(self.processor.output_file, "w") as f:
            f.write(output)


class GeneratorFactory:
    @staticmethod
    def build_generator(type, processor, output_format="yaml"):
        if type == "role_tasks":
            return GeneratorRoleTasks(processor, output_format)
        elif type == "role":
            return GeneratorRole(processor, output_format)
        elif type == "playbook":
            return GeneratorPlaybook(processor, output_format)
        else:
            raise ValueError(f"Unknown generator type: {type}")
