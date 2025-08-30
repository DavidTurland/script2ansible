# support for slack subroles

the scripts part:
https://github.com/jeviolle/slack/wiki/Subroles

## Example slack files

```
roles/foo/files.wibble/etc/blah.conf
roles/foo/files.wibble/etc/blah_wibble.conf
roles/foo/files/etc/blah.conf
```

Do we want:
- or mainly just a main role with a sub_role variable?
- subroles as distinct roles?




# Most of the work in main role with a sub_role variable

Each Ansible 'subrole' role will just :
- depend on the main role 
- and define a sub_role variable

This is more the slack-way: scripts in main role can use the sub_role
var with somewhat similar file locality

Ansible File Structure:
```
roles/foo/
            /files/etc/blah.conf
            /files/foo.wibble/etc/blah.conf
            /files/foo.wibble/etc/blah_wibble.conf
            /tasks/main.yaml
            - copy files/* /
            
            - copy files/.wibble/* /
                when: sub_role == "wibble"  
roles/foo.wibble/
                /meta/main.yaml
                    ---
                    dependencies:
                    - role: foo
                        vars:
                            sub_role: wibble
site.yaml
```                    

# Distinct Roles for subroles


Ansible File Structure:
```
roles/foo.wibble/
                /files/etc/blah.conf
                /tasks/main.yaml
                    - copy files/* /
                /meta/main.yaml
                    ---
                    dependencies:
                    - role: foo
roles/foo/
        /files/etc/blah.conf
        /tasks/main.yaml
            - copy files/*  /       
```        