# bash2ansible

## 
Converts bash scripts to Ansible tasks which can be used to 
generate Playboos or Role 'task' files

## 
Converts slack 'roles' into Ansible Roles

# Thanks to
ChatGPT 4.1 for turning a whim into code, and helping in the evolution.


# Install Locally for Development
```bash
# From the root directory
pip install -e .
```

Then run:

```bash
bash2ansible myscript.sh output.yml
```

Or override config:
```bash
bash2ansible myscript.sh output.json --json --strict
```

## How to Run Without Installing

From the root directory (where setup.py is), run:
```bash
python -m bash2ansible.cli input.sh output.yml
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