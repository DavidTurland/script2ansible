#!/usr/bin/env python3
import json
import os
import subprocess
import sys
import yaml
from pathlib import Path
import logging
from .Parser import Parser


class PerlParser(Parser):
    # ---------- Perl instrumentation template ----------
    INSTRUMENTATION_CODE_PREFIX = r"""
use strict;
use warnings;
use JSON;
use IO::File;

my @OPS;
sub log_op {
    my ($type, %data) = @_;
    push @OPS, { type => $type, %data };
}

# Wrap file operations
BEGIN {
    no warnings 'redefine';
    *CORE::GLOBAL::open = sub (*;$@) {
        my ($fh, $mode, $file, @rest) = @_;
        log_op("file_open", file => $file, mode => $mode, rest => \@rest);
        # If $fh is a string, convert to symbol ref
        if (!ref $fh) {
            no strict 'refs';
            return CORE::open(*{$fh},  $mode, $file, @rest);
        } else {
            return CORE::open($fh,  $mode, $file, @rest);
        }
    };
    *CORE::GLOBAL::rename = sub {
        my ($from, $to) = @_;
        log_op("file_rename", from => $from, to => $to);
        return CORE::rename($from, $to);
    };
    *CORE::GLOBAL::unlink = sub {
        my @files = @_;
        log_op("file_delete", files => \@files);
        return CORE::unlink(@files);
    };
    *CORE::GLOBAL::system = sub {
        my @args = @_;
        log_op("system_call", args => \@args);
        return CORE::system(@args);
    };
    *CORE::GLOBAL::exec = sub {
        my @args = @_;
        log_op("exec_call", args => \@args);
        return CORE::exec(@args);
    };
}
"""
    INSTRUMENTATION_CODE_SUFFIX = r"""

# Wrap require to log external package usage
BEGIN {
    no warnings 'redefine';
    *CORE::GLOBAL::require = sub {
        my ($module) = @_;
        #my $res = CORE::require($module);
        log_op("module_load", module => $module);
        #return $res;
    };
}

END {
    my $json = encode_json(\@OPS);
    my $fh = IO::File->new("/tmp/ops_log.json", "w");
    print $fh $json;
    $fh->close;
}
"""

    def __init__(self, file_path, config):
        super().__init__(file_path, config)

        original = Path(self.file_path)
        self.instrumented_path = original.parent / "instrumented.pl"
        self.log_path = original.parent / "ops_log.json"
        self.log_path = "/tmp/ops_log.json"
        self.INSTRUMENTATION_CODE_CUSTOM = (
            config["perl_custom"] if "perl_custom" in config else ""
        )

    def parse(self):
        logging.info("Generating instrumented Perl script...")
        self.generate_instrumented_perl()
        logging.info("Running instrumented Perl script...")
        output_lines = self.run_instrumented(sys.argv[2:])

        logging.info("Perl script output:")
        for line in output_lines:
            logging.debug(line)

        ops = self.load_ops_log()
        self.tasks = self.ops_to_ansible_tasks(ops)
        logging.info(f"Parsed {len(self.tasks)} Ansible tasks from Perl ops log.")
        return self.tasks
        # Save JSON and YAML
        with open("ansible_tasks.json", "w") as f:
            json.dump(self.tasks, f, indent=2)
        with open("ansible_tasks.yml", "w") as f:
            yaml.safe_dump(self.tasks, f, sort_keys=False)

    # ---------- Step 1: Generate instrumented.pl ----------
    def generate_instrumented_perl(self):
        with open(self.file_path, "r") as f:
            original_code = f.read()

        instrumented_code = (
            self.INSTRUMENTATION_CODE_PREFIX
            + "\n"
            + self.INSTRUMENTATION_CODE_CUSTOM
            + "\n"
            + self.INSTRUMENTATION_CODE_SUFFIX
            + "\n"
            + original_code
        )

        with open(self.instrumented_path, "w") as f:
            f.write(instrumented_code)

    # ---------- Step 2: Run instrumented.pl and capture output ----------
    def run_instrumented(self, args):
        cmd = ["perl", self.instrumented_path] + args
        result = subprocess.run(cmd, capture_output=True, text=True)
        stdout_lines = result.stdout.splitlines()
        return stdout_lines

    # ---------- Step 3: Load JSON log ----------
    def load_ops_log(self):
        if not os.path.exists(self.log_path):
            raise FileNotFoundError(f"Log file {self.log_path} not found")
        with open(self.log_path, "r") as f:
            return json.load(f)

    # ---------- Step 4: Map ops to Ansible tasks ----------
    def ops_to_ansible_tasks(self, ops):
        tasks = []
        for op in ops:
            t = op.get("type")
            d = op

            if t == "file_open":
                mode = "".join(str(m) for m in d.get("mode", []))
                if any(m in mode for m in ["w", "a", "+"]):
                    tasks.append(
                        {
                            "name": f"Ensure file {d.get('file')} exists",
                            "ansible.builtin.file": {
                                "path": d.get("file"),
                                "state": "touch",
                            },
                        }
                    )

            elif t == "mkdir":
                tasks.append(
                    {
                        "name": f"Create directory {d.get('dir')}",
                        "ansible.builtin.file": {
                            "path": d.get("dir"),
                            "state": "directory",
                            **({"mode": str(oct(d["mode"]))} if d.get("mode") else {}),
                        },
                    }
                )

            elif t == "rmdir":
                tasks.append(
                    {
                        "name": f"Remove directory {d.get('dir')}",
                        "ansible.builtin.file": {
                            "path": d.get("dir"),
                            "state": "absent",
                        },
                    }
                )

            elif t == "file_delete":
                for f in d.get("files", []):
                    tasks.append(
                        {
                            "name": f"Delete file {f}",
                            "ansible.builtin.file": {"path": f, "state": "absent"},
                        }
                    )

            elif t == "file_rename":
                tasks.append(
                    {
                        "name": f"Rename {d.get('from')} to {d.get('to')}",
                        "ansible.builtin.command": f"mv {d.get('from')} {d.get('to')}",
                    }
                )

            elif t in ("system_call", "exec_call"):
                args = d.get("args", [])
                if not args:
                    continue
                cmd = args[0]
                cmd_str = " ".join(str(a) for a in args)

                if cmd == "mkdir" and len(args) > 1:
                    tasks.append(
                        {
                            "name": f"Create directory {args[1]}",
                            "ansible.builtin.file": {
                                "path": args[1],
                                "state": "directory",
                            },
                        }
                    )
                elif cmd == "rm" and len(args) > 1:
                    tasks.append(
                        {
                            "name": f"Delete file {args[1]}",
                            "ansible.builtin.file": {
                                "path": args[1],
                                "state": "absent",
                            },
                        }
                    )
                elif cmd == "mv" and len(args) > 2:
                    tasks.append(
                        {
                            "name": f"Rename {args[1]} to {args[2]}",
                            "ansible.builtin.command": f"mv {args[1]} {args[2]}",
                        }
                    )
                else:
                    tasks.append(
                        {
                            "name": f"Run command: {cmd_str}",
                            "ansible.builtin.command": cmd_str,
                        }
                    )

            elif t == "external_call":
                mod = d.get("module")
                meth = d.get("method")
                if mod == "File::Copy" and meth == "copy":
                    src, dst = d.get("args", [None, None])[:2]
                    if src and dst:
                        tasks.append(
                            {
                                "name": f"Copy {src} to {dst}",
                                "ansible.builtin.copy": {"src": src, "dest": dst},
                            }
                        )
                elif mod == "File::Path" and meth == "make_path":
                    for dir_path in d.get("args", []):
                        tasks.append(
                            {
                                "name": f"Create directory {dir_path}",
                                "ansible.builtin.file": {
                                    "path": dir_path,
                                    "state": "directory",
                                },
                            }
                        )
                elif mod == "File::Path" and meth == "remove_tree":
                    for dir_path in d.get("args", []):
                        tasks.append(
                            {
                                "name": f"Remove directory {dir_path}",
                                "ansible.builtin.file": {
                                    "path": dir_path,
                                    "state": "absent",
                                },
                            }
                        )
                else:
                    tasks.append(
                        {
                            "name": f"Call Perl method {meth} in {mod}",
                            "debug": {
                                "msg": f"{mod}::{meth} called with args {d.get('args', [])}"
                            },
                        }
                    )

        return tasks


# ---------- Main ----------
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    if len(sys.argv) < 2:
        logging.error("Usage: process_perl.py <perl_script> [args...]")
        sys.exit(1)

    original = Path(sys.argv[1])
    instrumented = original.parent / "instrumented.pl"
    log_file = original.parent / "ops_log.json"
    perl_parser = PerlParser(original, {})
    perl_parser.generate_instrumented_perl(instrumented)
    output_lines = perl_parser.run_instrumented(instrumented, sys.argv[2:])

    logging.info("Perl script output:")
    for line in output_lines:
        logging.debug(line)

    ops = perl_parser.load_ops_log(log_file)
    tasks = perl_parser.ops_to_ansible_tasks(ops)

    # Save JSON and YAML
    with open("ansible_tasks.json", "w") as f:
        json.dump(tasks, f, indent=2)
    with open("ansible_tasks.yml", "w") as f:
        yaml.safe_dump(tasks, f, sort_keys=False)

    logging.info("Captured operations saved to ansible_tasks.json / ansible_tasks.yml")
