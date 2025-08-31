# TODO
General/common
- [ ] Nailing down push, vs pull logic
- [x] sub roles in slack (webserver.main, webserver.failover)

Bash
- [ ] Variables: define and/or interpret/template
- [ ] Environment Variables 
- [x] Parse for loops
- [ ] Parse while loops
- [ ] support for new pragmas to guide translation (unlikely)

Perl
- [ ] Variables: define and/or interpret/template
- [ ] Environment Variables
- [ ] what to do with Perl open,print,close 
- [ ] support for new pragmas to guide translation (unlikely)



# Installing Locally for Development
```bash
# From the root directory
pip install -e .
```

# Testing

## Unit Tests
```python
python -m unittest discover -s tests
```
## Coverage
```bash
pip install coverage
coverage run -m unittest discover -s tests
coverage report -m
```

# Bugs/ Feature requests / Pull Requests

Bugs and feature Request should be raised with the assumption that they may be pasted verbatim into CoPilot. 


Pull Requests are also likely better expressed as a chat to copilot which would have it respond similarily.


# Errata

## Thoughts on for loop

Could, for simple cases be implemented as

```yaml
- name: Add several users
  ansible.builtin.user:
    name: "{{ item }}"
    state: present
    groups: "wheel"
  loop:
     - testuser1
     - testuser2
```