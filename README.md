# script2ansible


Converts all operations in:
- bash scripts
- perl scripts

to Ansible tasks, which in turn are used to generate 
- Ansible playbooks or
- Ansible role task-files


Also knows how to translate slack (https://github.com/jeviolle/slack) roles into new Ansible roles
- 'scripts' can be either bash or perl
- 'files' and their required movement are correctly translated to role files, with the corresponding task to copy
# This is a Work-in-progress 
Because many reasons, including:
## Operation locality: push vs pull 

The scripts:

-  **A** could be intended to be run on the target(remote) host, with all files local to the target host, or maybe pulled from the server
```bash
cp /foo.txt /bar.txt
```

- **B** or they could be intended to run on the server ( probably hosting the files), and targetting a remote host
```bash
scp /foo.txt remote.host:/bar.txt
```

slack assumes **A**, with the role scripts run on the target host (required files are pulled in an earlier operation)

Ansible assumes **B**, is run on the server,  but is flexible:
- file-related tasks assume a src on the server, dest on the target, but the src can be remote
- All task are run on the target host (simplistic)

NOTE: It is assumed that standalone scripts (ie not slack scripts) are intended to be run (pulling) on the target

This makes interpreting the pullng of files interesting:
```bash
scp remote.host:/bar.txt /foo.txt 
```
which should probably map to the ansible task( run from remote.host):
```yaml
- name: Copy server bar.txt
  ansible.builtin.copy:
    src: <somewhere>/bar.txt
    dest: /foo.txt
```




# Supported Script Operations

## bash
note:

Bash scripts are `visited` using [bashlex](https://github.com/idank/bashlex/blob/master/README.md) so:
-  scripts are not run
- environment variables need to be simulated


## Operatiions:
variable assignment and reference
variables are currently updated and interpreted on the fly

This is ok, as a flex, but not so good if those variables derive from something run-dependant
```bash
output=$HOME/outputdir
wibble=hello
echo "$wibble wobble $wibblewobble"
```

The success of a command is used as a `when` parameter for constrained tasks
```bash
echo "hello" >> bert.txt
if [[ $? -eq 0 ]]; then
   echo "that worked so goodbye" >> floob.txt
fi
```

commands are an ever-increasing set:
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
echo ( with redirection: '>', and '>>' )
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

# Slack Support
Not that slack, this slack

# Usage

```bash
script2ansible --type slack --generator role  examples/slack/roles/bar  /tmp/rolly
```

# Permutations of type, generator, input and output
Work in progress

|            | slack<br/> roles/foo  | script <br/> floob.sh |  
|------------|:------------:|:---------:|
| **role** <br/> ~/roles      | ~/roles/foo/*     | TODO  |  
| **role_task** <br/> ~/wibble  |    N/A        |  ~/wibble/floob.yaml |  
| **playbook**  <br/> ~/wibble  |    N/A        |  ~/wibble/floob.yaml |  



## How to Run Without Installing

From the root directory (where setup.py is), run:
```bash
python -m script2ansible.cli --type slack --generator role  tests/slack/roles/bar  /tmp/rolly
```
```bash
python -m script2ansible.cli input.sh output.json --json
```


# Examples

## Bash script to Ansible Playbook

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
