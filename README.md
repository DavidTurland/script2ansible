# bash_2ansible


Install Locally for Development
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
