import json
import yaml

def generate_role_tasks(tasks, output_format="yaml"):
    return json.dumps(tasks, indent=2) if output_format == "json" else yaml.dump(tasks, sort_keys=False)

def generate_playbook(tasks, output_format="yaml"):
    playbook = [{
        'name': 'Execute translated shell commands',
        'hosts': 'all',
        'become': True,
        'tasks': tasks
    }]
    return json.dumps(playbook, indent=2) if output_format == "json" else yaml.dump(playbook, sort_keys=False)
