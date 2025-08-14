import unittest
import os
from script2ansible.BashParser import BashParser

class TestBashParser(unittest.TestCase):
    def setUp(self):
        self.test_script_path = "/tmp/test_bash_script.sh"
        self.test_script_content = (
            'MYVAR=/tmp/foo\n'
            'umask 0077\n'
            'mkdir -p $MYVAR\n'
            'touch /tmp/bar.txt\n'
            'ln -s /tmp/bar.txt /tmp/link.txt\n'
            'cp /tmp/bar.txt /tmp/copy.txt\n'
            'ldconfig\n'
            'gunzip /tmp/archive.gz\n'
            'chmod 755 /tmp/bar.txt\n'
            'apt update\n'
            'apt install -y foo bar\n'
            'yum install -y baz\n'
            'echo "hello" > /tmp/hello.txt\n'
            'echo "append" >> /tmp/hello.txt\n'
            'grep "foo" /tmp/bar.txt\n'
            'if [[ $? -eq 0 ]]; then\n'
            '  touch /tmp/ok.txt\n'
            'fi\n'
        )
        with open(self.test_script_path, "w") as f:
            f.write(self.test_script_content)

    def tearDown(self):
        os.remove(self.test_script_path)

    def test_parse_basic_commands(self):
        parser = BashParser(self.test_script_path, {})
        tasks = parser.parse()
        self.assertTrue(any(t.get("ansible.builtin.file", {}).get("state") == "directory" for t in tasks))
        self.assertTrue(any(t.get("ansible.builtin.file", {}).get("state") == "touch" for t in tasks))
        self.assertTrue(any(t.get("ansible.builtin.file", {}).get("state") in ("link", "hard") for t in tasks))
        self.assertTrue(any("ansible.builtin.copy" in t for t in tasks))
        self.assertTrue(any(t.get("ansible.builtin.shell") == "ldconfig" for t in tasks))
        self.assertTrue(any("ansible.builtin.unarchive" in t for t in tasks))
        self.assertTrue(any(t.get("ansible.builtin.file", {}).get("mode") == "755" for t in tasks))
        self.assertTrue(any("ansible.builtin.apt" in t or "ansible.builtin.yum" in t for t in tasks))
        self.assertTrue(any("ansible.builtin.copy" in t or "ansible.builtin.lineinfile" in t for t in tasks))
        self.assertTrue(any("register" in t for t in tasks))

    def test_if_result_code(self):
        parser = BashParser(self.test_script_path, {})
        tasks = parser.parse()
        touch_tasks = [t for t in tasks if t.get("ansible.builtin.file", {}).get("path") == "/tmp/ok.txt"]
        self.assertTrue(any("when" in t for t in touch_tasks))
        self.assertTrue(any("is succeeded" in t.get("when", "") or "is failed" in t.get("when", "") for t in touch_tasks))

if __name__ == "__main__":
    unittest.main()
