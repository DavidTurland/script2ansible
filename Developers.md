# TODO
- [ ] Nailing down push, vs pull logic
- [ ] Variables: define and/or interpret
- [ ] Environment Variables
- [ ] sub roles in slack (webserver.main, webserver.failover)
- [x] Parse for loops in bash
- [ ] what to do with Perl open,print,close 
- [ ] support for new pragmas to guide translation




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


```bash
python3 -m script2ansible.cli --type slack --generator role examples/slack/roles/bar /tmp
```


```bash
python3 -m script2ansible.cli --type slack -generator role_tasks examples/slack/roles/bar /tmp
```

```bash
python3 -m script2ansible.cli --type script --generator playbook examples/bash/sample1.sh /tmp/floob.yaml
```


# Bugs/ Feature requests / Pull Requests

Bugs and feature Request should be raised with the assumption that they may be pasted into CoPilot verbatim. 


Pull Requests are also likely better expressed as a chat to copilot which would have it respond similarily.
