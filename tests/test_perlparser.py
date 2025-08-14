import unittest
from script2ansible.PerlParser import PerlParser

class TestPerlParser(unittest.TestCase):
    def setUp(self):
        self.parser = PerlParser(file_path="/tmp/fake.pl", config={})

    def test_file_open_touch(self):
        ops = [{"type": "file_open", "file": "/tmp/foo.txt", "mode": "w"}]
        tasks = self.parser.ops_to_ansible_tasks(ops)
        self.assertEqual(tasks[0]["ansible.builtin.file"]["path"], "/tmp/foo.txt")
        self.assertEqual(tasks[0]["ansible.builtin.file"]["state"], "touch")

    def test_mkdir(self):
        ops = [{"type": "mkdir", "dir": "/tmp/bar"}]
        tasks = self.parser.ops_to_ansible_tasks(ops)
        self.assertEqual(tasks[0]["ansible.builtin.file"]["path"], "/tmp/bar")
        self.assertEqual(tasks[0]["ansible.builtin.file"]["state"], "directory")

    def test_file_delete(self):
        ops = [{"type": "file_delete", "files": ["/tmp/foo.txt"]}]
        tasks = self.parser.ops_to_ansible_tasks(ops)
        self.assertEqual(tasks[0]["ansible.builtin.file"]["path"], "/tmp/foo.txt")
        self.assertEqual(tasks[0]["ansible.builtin.file"]["state"], "absent")

    def test_file_rename(self):
        ops = [{"type": "file_rename", "from": "/tmp/a", "to": "/tmp/b"}]
        tasks = self.parser.ops_to_ansible_tasks(ops)
        self.assertIn("mv /tmp/a /tmp/b", tasks[0]["ansible.builtin.command"])

    def test_system_call_mkdir(self):
        ops = [{"type": "system_call", "args": ["mkdir", "/tmp/dir"]}]
        tasks = self.parser.ops_to_ansible_tasks(ops)
        self.assertEqual(tasks[0]["ansible.builtin.file"]["path"], "/tmp/dir")
        self.assertEqual(tasks[0]["ansible.builtin.file"]["state"], "directory")

    def test_external_call_copy(self):
        ops = [{"type": "external_call", "module": "File::Copy", "method": "copy", "args": ["/tmp/a", "/tmp/b"]}]
        tasks = self.parser.ops_to_ansible_tasks(ops)
        self.assertEqual(tasks[0]["ansible.builtin.copy"]["src"], "/tmp/a")
        self.assertEqual(tasks[0]["ansible.builtin.copy"]["dest"], "/tmp/b")

    def test_external_call_make_path(self):
        ops = [{"type": "external_call", "module": "File::Path", "method": "make_path", "args": ["/tmp/dir1", "/tmp/dir2"]}]
        tasks = self.parser.ops_to_ansible_tasks(ops)
        self.assertEqual(tasks[0]["ansible.builtin.file"]["path"], "/tmp/dir1")
        self.assertEqual(tasks[1]["ansible.builtin.file"]["path"], "/tmp/dir2")

    def test_parser(self):
        parser = PerlParser(script_string="use File::Path qw(make_path); make_path('/tmp/dir1', '/tmp/dir2');", config={})
        tasks = parser.parse()
        self.assertIsInstance(tasks, list)
        #breakpoint()  # For debugging purposes
        self.assertEqual(tasks[0]["ansible.builtin.file"]["path"], "/tmp/dir1")
        self.assertEqual(tasks[1]["ansible.builtin.file"]["path"], "/tmp/dir2")

if __name__ == "__main__":
    unittest.main()
