# bash2ansible

## 
Converts bash scripts, or perl scripts to Ansible tasks which can be used to 
generate Playbooks or Role 'task' files

## 
Converts slack 'roles' into Ansible Roles



# Install Locally for Development
```bash
# From the root directory
pip install -e .
```

Then run:

```bash
bash2ansible --type slack --generator role  tests/slack/roles/bar  /tmp/rolly
```

Or override config:
```bash
bash2ansible myscript.sh output.json --json --strict
```

## How to Run Without Installing

From the root directory (where setup.py is), run:
```bash
python -m bash2ansible.cli --type slack --generator role  tests/slack/roles/bar  /tmp/rolly
```
```bash
python -m bash2ansible.cli input.sh output.json --json
```

## Example: Bash to Ansible Playbook

Suppose you have a simple bash script:

**myscript.sh**
```bash
#!/bin/bash
touch /tmp/example.txt
cp /tmp/example.txt /tmp/example2.txt
yum install -y httpd
```

Run the converter:
```bash
python -m bash2ansible.cli myscript.sh playbook.yaml --yaml --type bash --generator playbook
```

**Resulting playbook.yaml:**
```yaml
- name: Execute translated shell commands
  hosts: all
  become: true
  tasks:
    - name: Ensure file /tmp/example.txt exists
      ansible.builtin.file:
        path: /tmp/example.txt
        state: touch
    - name: Copy /tmp/example.txt to /tmp/example2.txt
      ansible.builtin.copy:
        src: /tmp/example.txt
        dest: /tmp/example2.txt
        remote_src: true
    - name: Install packages: httpd
      ansible.builtin.yum:
        name:
          - httpd
        state: present
```

## testing
```bash
python3 -m bash2ansible.cli --type slack tests/slack/roles/bar /tmp
```

```bash
python3 -m bash2ansible.cli --type bash tests/bash/sample1.sh /tmp/floob.yaml
```