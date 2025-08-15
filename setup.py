from setuptools import setup, find_packages

setup(
    name="script2ansible",
    version="0.1.0",
    packages=find_packages(),
    install_requires=["PyYAML", "bashlex"],
    entry_points={
        "console_scripts": [
            "script2ansible = script2ansible.cli:main"
        ]
    },
    author="David Turland",
    description="Convert Perl,Bash scripts into Ansible playbooks, or Roles, using built-in modules",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License"
    ],
    python_requires='>=3.7'
)
