import sys
import yaml
import os
import re

def parse_bash_script(file_path):
    tasks = []
    with open(file_path, 'r') as file:
        lines = file.readlines()

    current_command = ""
    for line in lines:
        line = line.strip()

        if not line or line.startswith("#"):
            continue

        if line.endswith("\\"):
            current_command += line[:-1] + " "
            continue
        else:
            current_command += line

        task = translate_to_ansible(current_command.strip())
        tasks.append(task)
        current_command = ""

    return tasks

def translate_to_ansible(command):
    # mkdir -p /some/path
    if match := re.match(r'mkdir\s+(-p\s+)?(?P<path>\S+)', command):
        return {
            "name": f"Ensure directory {match.group('path')} exists",
            "ansible.builtin.file": {
                "path": match.group("path"),
                "state": "directory"
            }
        }

    # chmod 755 /some/file
    if match := re.match(r'chmod\s+(?P<mode>\d+)\s+(?P<path>\S+)', command):
        return {
            "name": f"Set permissions of {match.group('path')} to {match.group('mode')}",
            "ansible.builtin.file": {
                "path": match.group("path"),
                "mode": match.group("mode")
            }
        }

    # apt install -y
    if match := re.match(r'apt(-get)?\s+install\s+(-y\s+)?(?P<packages>.+)', command):
        packages = match.group("packages").split()
        return {
            "name": f"Install packages: {' '.join(packages)}",
            "ansible.builtin.apt": {
                "name": packages,
                "state": "present",
                "update_cache": True
            }
        }

    # md5sum
    if match := re.match(r'md5sum\s+(?P<path>\S+)', command):
        return {
            "name": f"Check MD5 checksum of {match.group('path')}",
            "ansible.builtin.stat": {
                "path": match.group("path"),
                "checksum_algorithm": "md5"
            }
        }

    # wget with -O
    if match := re.match(r'wget\s+(?P<url>\S+)\s+-O\s+(?P<dest>\S+)', command):
        return {
            "name": f"Download {match.group('url')} to {match.group('dest')}",
            "ansible.builtin.get_url": {
                "url": match.group("url"),
                "dest": match.group("dest")
            }
        }

    # wget URL only
    if match := re.match(r'wget\s+(?P<url>\S+)', command):
        filename = match.group("url").split("/")[-1]
        return {
            "name": f"Download {match.group('url')} to ./{filename}",
            "ansible.builtin.get_url": {
                "url": match.group("url"),
                "dest": f"./{filename}"
            }
        }

    # touch file
    if match := re.match(r'touch\s+(?P<path>\S+)', command):
        return {
            "name": f"Ensure file {match.group('path')} exists",
            "ansible.builtin.file": {
                "path": match.group("path"),
                "state": "touch"
            }
        }

    # cp src dest
    if match := re.match(r'cp\s+(?P<src>\S+)\s+(?P<dest>\S+)', command):
        return {
            "name": f"Copy {match.group('src')} to {match.group('dest')}",
            "ansible.builtin.copy": {
                "src": match.group("src"),
                "dest": match.group("dest"),
                "remote_src": True
            }
        }

    # mv src dest
    if match := re.match(r'mv\s+(?P<src>\S+)\s+(?P<dest>\S+)', command):
        return {
            "name": f"Move {match.group('src')} to {match.group('dest')}",
            "ansible.builtin.command": f"mv {match.group('src')} {match.group('dest')}"
        }

    # systemctl start service
    if match := re.match(r'systemctl\s+start\s+(?P<svc>\S+)', command):
        return {
            "name": f"Start service {match.group('svc')}",
            "ansible.builtin.service": {
                "name": match.group("svc"),
                "state": "started"
            }
        }

    # systemctl enable service
    if match := re.match(r'systemctl\s+enable\s+(?P<svc>\S+)', command):
        return {
            "name": f"Enable service {match.group('svc')}",
            "ansible.builtin.service": {
                "name": match.group("svc"),
                "enabled": True
            }
        }

    # echo "..." > file (basic)
    if match := re.match(r'echo\s+"(?P<content>.*)"\s*>\s*(?P<dest>\S+)', command):
        return {
            "name": f"Write content to {match.group('dest')}",
            "ansible.builtin.copy": {
                "dest": match.group("dest"),
                "content": match.group("content") + "\n"
            }
        }

    # Fallback
    return {
        "name": f"Run shell command: {command}",
        "ansible.builtin.shell": command
    }

def generate_ansible_playbook(tasks, output_file):
    playbook = [{
        'name': 'Execute translated shell commands',
        'hosts': 'all',
        'become': True,
        'tasks': tasks
    }]

    with open(output_file, 'w') as f:
        yaml.dump(playbook, f, default_flow_style=False, sort_keys=False)

    print(f"Ansible playbook written to {output_file}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python bash_to_ansible.py <input_bash_script.sh> <output_playbook.yml>")
        sys.exit(1)

    input_bash_script = sys.argv[1]
    output_ansible_playbook = sys.argv[2]

    if not os.path.exists(input_bash_script):
        print(f"Error: {input_bash_script} does not exist.")
        sys.exit(1)

    tasks = parse_bash_script(input_bash_script)
    generate_ansible_playbook(tasks, output_ansible_playbook)
