import json
import yaml
import os

class GeneratorRole:
    def __init__(self, processor, output_format="yaml"):
        self.processor = processor
        self.output_format = output_format

    def generate(self):
        task_containers = self.processor.get_tasks()
        tasks_dir = os.path.join(self.processor.get_output_dir(), 'tasks')
        os.makedirs(tasks_dir, exist_ok=True)
        for task_container in task_containers:
            if not task_container.get_tasks():
                continue
            tasks_name = task_container.name
            tasks = task_container.get_tasks()
            output = json.dumps(tasks, indent=2) if self.output_format == "json" else yaml.dump(tasks, sort_keys=False)
            ofile_name = os.path.join(self.processor.get_output_dir(), 'tasks', f"{tasks_name}.yml")
            with open(ofile_name, 'w') as f:
                f.write(output)

class GeneratorRoleTasks:
    def __init__(self, processor, output_format="yaml"):
        self.processor = processor
        self.output_format = output_format

    def generate(self):
        task_containers = self.processor.get_tasks()
        for task_container in task_containers:
            if not task_container.get_tasks():
                continue
            task_name = task_container.name
            tasks = task_container.get_tasks()
            output = json.dumps(tasks, indent=2) if self.output_format == "json" else yaml.dump(tasks, sort_keys=False)
            with open(self.processor.output_file, 'w') as f:
                f.write(output)

class GeneratorPlaybook:
    def __init__(self, processor, output_format="yaml"):
        self.processor = processor
        self.output_format = output_format

    def generate(self):
        task_containers = self.processor.get_tasks()
        playbook = [{
            'name': 'Execute translated shell commands',
            'hosts': 'all',
            'become': True,
            'tasks': task_containers[0].get_tasks() if task_containers else []
        }]
        output = json.dumps(playbook, indent=2) if self.output_format == "json" else yaml.dump(playbook, sort_keys=False)
        with open(self.processor.output_file, 'w') as f:
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
