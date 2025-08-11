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

## testing
```bash
python3 -m bash2ansible.cli --type slack tests/slack/roles/bar /tmp
```

```bash
python3 -m bash2ansible.cli --type bash tests/bash/sample1.sh /tmp/floob.yaml
```