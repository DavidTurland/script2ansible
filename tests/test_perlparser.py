import unittest
import os
import subprocess
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
        ops = [{"type": "system_call", "args": ["mkdir '/tmp/dir'"]}]
        tasks = self.parser.ops_to_ansible_tasks(ops)
        self.assertEqual(tasks[0]["ansible.builtin.file"]["path"], "'/tmp/dir'")
        self.assertEqual(tasks[0]["ansible.builtin.file"]["state"], "directory")

    def test_external_call_copy(self):
        ops = [
            {
                "type": "external_call",
                "module": "File::Copy",
                "method": "copy",
                "args": ["/tmp/a", "/tmp/b"],
            }
        ]
        tasks = self.parser.ops_to_ansible_tasks(ops)
        self.assertEqual(tasks[0]["ansible.builtin.copy"]["src"], "/tmp/a")
        self.assertEqual(tasks[0]["ansible.builtin.copy"]["dest"], "/tmp/b")

    def test_external_call_make_path(self):
        ops = [
            {
                "type": "external_call",
                "module": "File::Path",
                "method": "make_path",
                "args": ["/tmp/dir1", "/tmp/dir2"],
            }
        ]
        tasks = self.parser.ops_to_ansible_tasks(ops)
        self.assertEqual(tasks[0]["ansible.builtin.file"]["path"], "/tmp/dir1")
        self.assertEqual(tasks[1]["ansible.builtin.file"]["path"], "/tmp/dir2")

    def test_parser(self):
        parser = PerlParser(
            script_string="use File::Path qw(make_path); make_path('/tmp/dir1', '/tmp/dir2');",
            config={},
        )
        taskcontainer = parser.parse()
        self.assertIsInstance(taskcontainer.tasks, list)
        # breakpoint()  # For debugging purposes
        self.assertEqual(
            taskcontainer.tasks[0]["ansible.builtin.file"]["path"], "/tmp/dir1"
        )
        self.assertEqual(
            taskcontainer.tasks[1]["ansible.builtin.file"]["path"], "/tmp/dir2"
        )

    def test_parser_from_file(self):
        script_string = (
            "use File::Path qw(make_path); make_path('/tmp/dir1', '/tmp/dir2');"
        )
        test_file_path = "/tmp/test_parser_from_file.pl"
        with open(test_file_path, "w") as f:
            f.write(script_string)
        parser = PerlParser(file_path=test_file_path, config={})
        taskcontainer = parser.parse()
        self.assertIsInstance(taskcontainer.tasks, list)
        self.assertEqual(
            taskcontainer.tasks[0]["ansible.builtin.file"]["path"], "/tmp/dir1"
        )
        self.assertEqual(
            taskcontainer.tasks[1]["ansible.builtin.file"]["path"], "/tmp/dir2"
        )

    def test_parser_from_broke_file(self):
        script_string = """
use File::Path qw(make_path);
NOPE make_path('/tmp/dir1', '/tmp/dir2');
"""
        test_file_path = "/tmp/test_parser_from_file.pl"
        with open(test_file_path, "w") as f:
            f.write(script_string)
        parser = PerlParser(file_path=test_file_path, config={})
        with self.assertRaises(RuntimeError) as context:
            taskcontainer = parser.parse()
        self.assertTrue("Bareword found" in str(context.exception))

    def test_calls_various(self):
        script_string = """
rmdir '/tmp/fooby/doo';
"""
        test_file_path = "/tmp/test_calls_various.pl"
        with open(test_file_path, "w") as f:
            f.write(script_string)
        parser = PerlParser(file_path=test_file_path, config={})
        taskcontainer = parser.parse()
        self.assertIsInstance(taskcontainer.tasks, list)
        self.assertEqual(
            taskcontainer.tasks[0]["ansible.builtin.file"]["path"], "/tmp/fooby/doo"
        )
        self.assertEqual(
            taskcontainer.tasks[0]["ansible.builtin.file"]["state"], "absent"
        )

    # def test_parser_use(self):
    #     parser = PerlParser(script_string="use Org::Turland::Helpers; \n Org::Turland::Helpers::do_that_thing((a => 'b'));", config={})
    #     self.assertEqual(parser.instrumentation_packages,{'Org::Turland::Helpers'})
    #     parser.generate_instrumented_perl()
    #     contains_commented_use = any('# use Org::Turland::Helpers' in s for s in parser.instrumented_code.splitlines())
    #     self.assertTrue(contains_commented_use,'commented use in generated code')
    #     tasks = parser.parse()

    def test_parser_file_path(self):
        parser = PerlParser(
            script_string="""
            system(\"rm '/tmp/foo.txt'\");
            use File::Path qw();
            File::Path::remove_tree('/tmp/wibble');
            """,
            config={},
        )
        self.assertEqual(parser.instrumentation_packages, {"Org::Turland::Custom"})
        taskcontainer = parser.parse()
        self.assertEqual(len(taskcontainer.tasks), 2, "just the two tasks")
        # self.assertEqual(tasks[0]["ansible.builtin.file"]["path"], "/tmp/wibble.txt")
        # self.assertEqual(tasks[1]["ansible.builtin.file"]["path"], "/tmp/wobble.txt")

    def test_parser_system_various(self):
        parser = PerlParser(
            script_string="""
            system();
            system('mv "a" "b"');
            system('uptime');
            """,
            config={},
        )
        taskcontainer = parser.parse()
        self.assertEqual(len(taskcontainer.tasks), 2, "just the two tasks")
        # self.assertEqual(tasks[0]["ansible.builtin.file"]["path"], "/tmp/wibble.txt")
        # self.assertEqual(tasks[1]["ansible.builtin.file"]["path"], "/tmp/wobble.txt")

    def test_subprocess_env_variables_simple(self):
        script_string_file = "/tmp/script_string_file.pl"
        script_string = """
        use Env qw( $ROOT $VERBOSE HOSTNAME);
        system("echo ${ROOT} ${VERBOSE} $HOSTNAME $ENV{STAGE} ");
        # system('uptime');
            """
        with open(script_string_file, "w") as f:
            f.write(script_string)

        cmd = ["perl", script_string_file]

        env = os.environ | {
            "ROOT": "/",
            "STAGE": "/tmp/foo",
            "HOSTNAME": "foo",
            "VERBOSE": "1",
        }
        result = subprocess.run(cmd, capture_output=True, text=True, env=env)
        self.assertEqual("/ 1 foo /tmp/foo\n", result.stdout)
        os.remove(script_string_file)

    def test_parser_env_variables(self):
        parser = PerlParser(
            script_string="""
        use Env qw( $ROOT $VERBOSE STAGE);
        system("mv ${ROOT}foo_${VERBOSE} $STAGE/bar ");
        system('uptime');
            """,
            config={},
        )
        taskcontainer = parser.parse()
        self.assertEqual(len(taskcontainer.tasks), 2, "just the two tasks")
        self.assertEqual(
            taskcontainer.tasks[0]["ansible.builtin.command"],
            "mv /foo_1 /tmp/s2a_stage/bar",
        )
        self.assertEqual(taskcontainer.tasks[1]["ansible.builtin.command"], "uptime")

    def test_parser_env_variables_two(self):
        parser = PerlParser(
            script_string="""
        system("mv $ENV{ROOT}/foo.pl $STAGE/wibble_$ENV{VERBOSE}");
        system('uptime');
        """,
            config={},
        )
        taskcontainer = parser.parse()
        # breakpoint()
        self.assertEqual(len(taskcontainer.tasks), 2, "just the two tasks")
        # self.assertEqual(tasks[0]["ansible.builtin.file"]["path"], "/tmp/wibble.txt")
        # self.assertEqual(tasks[1]["ansible.builtin.file"]["path"], "/tmp/wobble.txt")

    def test_parser_custom(self):
        parser = PerlParser(
            script_string="""
            use Org::Turland::Custom qw(file_state);
            Org::Turland::Custom::file_state((path => '/tmp/wibble.txt'));
            file_state((path => '/tmp/wobble.txt'));
            """,
            config={},
        )
        self.assertEqual(parser.instrumentation_packages, {"Org::Turland::Custom"})
        taskcontainer = parser.parse()
        # breakpoint()
        self.assertEqual(len(taskcontainer.tasks), 2, "just the two tasks")
        self.assertEqual(
            taskcontainer.tasks[0]["ansible.builtin.file"]["path"], "/tmp/wibble.txt"
        )
        self.assertEqual(
            taskcontainer.tasks[1]["ansible.builtin.file"]["path"], "/tmp/wobble.txt"
        )

    def test_parser_local_package(self):
        config = {
            "perl_custom": """
BEGIN {
        package Org::Turland::Local;
        # sample package which need not exist at parse-time
        no warnings 'redefine';
        use Exporter qw(import);
        our @EXPORT_OK = qw(file_state);
        *Org::Turland::Local::file_state = sub {
            my (%args) = @_;
            my $path = $args{path};
            my $state = $args{state} // 'absent';
            my $params = $args{params} // { sudo => 1 };
            my $task = { name => 'file_state',
                         task => 'ansible.builtin.file',
                         task_params => {
                                path => $path ,
                                state => $state,
                            },
                         params => $params,
                    };
            ::log_task("custom", $task);
            return;
        };
    }
"""
        }
        parser = PerlParser(
            script_string="""
            use Org::Turland::Local qw(file_state);
            Org::Turland::Local::file_state((path => '/tmp/wibble.txt'));
            file_state((path => '/tmp/wobble.txt'));
            """,
            config=config,
        )
        self.assertEqual(
            parser.instrumentation_packages,
            {"Org::Turland::Local", "Org::Turland::Custom"},
        )
        taskcontainer = parser.parse()
        # breakpoint()
        self.assertEqual(len(taskcontainer.tasks), 2, "just the two tasks")
        self.assertEqual(
            taskcontainer.tasks[0]["ansible.builtin.file"]["path"], "/tmp/wibble.txt"
        )
        self.assertEqual(
            taskcontainer.tasks[1]["ansible.builtin.file"]["path"], "/tmp/wobble.txt"
        )


if __name__ == "__main__":
    unittest.main()  # pragma: no cover
