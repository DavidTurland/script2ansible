# script2ansible
# Work-in-progress 

Converts all operations in:
- bash scripts
- perl scripts

to Ansible tasks, which in turn are used to generate 
- Ansible playbooks or
- Ansible role task-files


Also knows how to translate slack (https://github.com/jeviolle/slack) roles into new Ansible roles
- 'scripts' can be either bash or perl
- 'files' and their required movement are correctly translated to role files, with the corresponding task to copy


# Bugs/ Feature requests / Pull Requests

Bugs and feature Request should be raised with the assumption that they may be pasted into CoPilot verbatim. 


Pull Requests are also likely better expressed as a chat to copilot which would have it respond similarily.

# Supported Script Operations

## bash
Bash scripts are visited using bashlex, they are not run

variable assignment and reference
```bash
wibble=hello
echo "$wibble wobble $wibblewobble"
```

success of commands are used as when parameters for constrained tasks
```bash
echo "hello" >> bert.txt
if [[ $? -eq 0 ]]; then
   echo "that worked so goodbye" >> floob.txt
fi
```

commands, an ever-increasing set:
```bash
umask
mkdir
touch
ln
cp
ldconfig
gunzip
chmod
apt update
apt upgrade
apt install
yum update
yum upgrade
yum install
echo ( with redirectiob)
```

## Perl
The script is run, and intrinsics, and selected package methods are intercepted, or mocked

```perl
```

$NOTE$: custom package methods can be added to ./.scrip2ansible.yaml
```yaml
perl_custom: |
  BEGIN {
      package Org::Turland::Helpers;
      sub my_sub{
          ::log_task("my_sub", args => \@_);
          return;
      }
  }
```

```perl
use Org::Turland::Helpers;
my %args = (path => '/tmp/wibble.txt', state => 'absent');
Org::Turland::Helpers::my_sub(%args);
```



# Install Locally for Development
```bash
# From the root directory
pip install -e .
```
# Permutations of type, generator, input and output
Work in progress

|            | slack<br/> roles/foo  | script <br/> floob.sh |  
|------------|:------------:|:---------:|
| **role** <br/> ~/roles      | ~/roles/foo/*     | TODO  |  
| **role_task** <br/> ~/wibble  |    N/A        |  ~/wibble/floob.yaml |  
| **playbook**  <br/> ~/wibble  |    N/A        |  ~/wibble/floob.yaml |  



# Usage

```bash
script2ansible --type slack --generator role  tests/slack/roles/bar  /tmp/rolly
```

## How to Run Without Installing

From the root directory (where setup.py is), run:
```bash
python -m script2ansible.cli --type slack --generator role  tests/slack/roles/bar  /tmp/rolly
```
```bash
python -m script2ansible.cli input.sh output.json --json
```

# Unit Tests
```python
python -m unittest discover -s tests
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
python -m script2ansible.cli myscript.sh playbook.yaml --type script --generator playbook
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
python3 -m script2ansible.cli --type slack --generator role examples/slack/roles/bar /tmp
```


```bash
python3 -m script2ansible.cli --type slack -generator role_tasks examples/slack/roles/bar /tmp
```

```bash
python3 -m script2ansible.cli --type script --generator playbook examples/bash/sample1.sh /tmp/floob.yaml
```