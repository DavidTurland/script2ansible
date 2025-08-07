import json
import yaml
import os

def generator_role(processor, output_format="yaml"):
    """Generates the tasks and files directories for a role
    Args:
        processor (Processor): The processor instance containing task information.
        output_format (str): Output format, either 'json' or 'yaml'.

        Assumes 
         config['output'] is the ansible roles directory
         task_container.name is the name of the task file
         processor.output_file is the path to the output file
    """
    task_containers = processor.get_tasks()
    tasks_dir = os.path.join(processor.get_output_dir(), 'tasks')
    os.makedirs(tasks_dir, exist_ok=True)
    for task_container in task_containers:
        if not task_container.get_tasks():
            continue
        tasks_name = task_container.name
        tasks = task_container.get_tasks()
        output = json.dumps(tasks, indent=2) if output_format == "json" else yaml.dump(tasks, sort_keys=False)
        ofile_name = os.path.join(processor.get_output_dir(), 'tasks', f"{tasks_name}.yml")
        with open(ofile_name, 'w') as f:
            f.write(output)
    
def generator_role_tasks(processor, output_format="yaml"):
    """Generates a task file as seen in the role/tasks directory.
    Args:
        processor (Processor): The processor instance containing task information.
        output_format (str): Output format, either 'json' or 'yaml'.
    """
    task_containers = processor.get_tasks()

    for task_container in task_containers:
        if not task_container.get_tasks():
            continue
        task_name = task_container.name
        tasks = task_container.get_tasks()
        output = json.dumps(tasks, indent=2) if output_format == "json" else yaml.dump(tasks, sort_keys=False)
        with open(processor.output_file, 'w') as f:
            f.write(output)

def generator_playbook(processor, output_format="yaml"):
    task_containers = processor.get_tasks()
    playbook = [{
        'name': 'Execute translated shell commands',
        'hosts': 'all',
        'become': True,
        'tasks': task_containers[0].get_tasks() if task_containers else []
    }]
    output = json.dumps(playbook, indent=2) if output_format == "json" else yaml.dump(playbook, sort_keys=False)
    with open(processor.output_file, 'w') as f:
        f.write(output)


def build_generator(type):
    if type == "role_tasks":
        return generator_role_tasks
    elif type == "role":    
        return generator_role    
    elif type == "playbook":
        return generator_playbook
    else:
        raise ValueError(f"Unknown generator type: {type}")
