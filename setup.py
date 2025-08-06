from setuptools import setup, find_packages

setup(
    name="bash2ansible",
    version="0.1.0",
    packages=find_packages(),
    install_requires=["PyYAML"],
    entry_points={
        "console_scripts": [
            "bash2ansible = bash2ansible.cli:main"
        ]
    },
    author="Your Name",
    description="Convert bash scripts into Ansible playbooks using built-in modules",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License"
    ],
    python_requires='>=3.7'
)
