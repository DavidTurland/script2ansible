import unittest
import os
from script2ansible.BashLexParser import BashLexParser, BashScriptVisitor


class TestBashLexParser(unittest.TestCase):
    def setUp(self):
        self.test_script_path = "/tmp/test_bashlex_script.sh"
        self.test_script_content = """
MYVAR=wibble
umask 0077
mv foo.txt bar.txt
mkdir -p $MYVAR
touch /tmp/foo.txt
ln -s /tmp/foo.txt /tmp/bar.txt
cp /tmp/foo.txt /tmp/bar.txt
ldconfig
gunzip /tmp/archive.gz
chmod 755 /tmp/foo.txt
chmod -R 755 /tmp/*
chown foo:bar /tmp/foo.txt
chown -R foo:bar /tmp/*
apt update
apt upgrade
apt install -y foo bar
yum install -y baz
echo "hello" > /tmp/hello.txt
echo "hello"
echo "append" >> /tmp/hello.txt
if [ $? -eq 0 ]; then
  touch /tmp/ok.txt
fi
if [ 0 -eq $? ]; then
  touch /tmp/ok.txt
fi
if [ "$MYVAR" -eq "wibble" ]; then
  echo "matched" >> /tmp/ok.txt
fi
scp /path/to/local/file.txt username@remote_host:/path/to/remote/directory/
ssh foo@bar ls -l
       """
        with open(self.test_script_path, "w") as f:
            f.write(self.test_script_content)

    def tearDown(self):
        os.remove(self.test_script_path)

    def test_parse_basic_commands(self):
        parser = BashLexParser(file_path=self.test_script_path, config={})
        taskcontainer = parser.parse()
        # Check mkdir task
        self.assertTrue(
            any(
                t.get("ansible.builtin.file", {}).get("state") == "directory"
                for t in taskcontainer.tasks
            )
        )
        # Check touch task
        self.assertTrue(
            any(
                t.get("ansible.builtin.file", {}).get("state") == "touch"
                for t in taskcontainer.tasks
            )
        )
        # Check ln task
        self.assertTrue(
            any(
                t.get("ansible.builtin.file", {}).get("state") in ("link", "hard")
                for t in taskcontainer.tasks
            )
        )
        # Check cp task
        self.assertTrue(any("ansible.builtin.copy" in t for t in taskcontainer.tasks))
        # Check scp task hahahahaha
        self.assertTrue(any("ansible.builtin.copy" in t for t in taskcontainer.tasks))
        # Check ldconfig
        self.assertTrue(
            any(
                t.get("ansible.builtin.command") == "ldconfig"
                for t in taskcontainer.tasks
            )
        )
        # Check gunzip
        self.assertTrue(
            any("ansible.builtin.unarchive" in t for t in taskcontainer.tasks)
        )
        # Check chmod
        self.assertTrue(
            any(
                t.get("ansible.builtin.file", {}).get("mode") == "755"
                for t in taskcontainer.tasks
            )
        )
        # Check apt/yum install
        self.assertTrue(
            any(
                "ansible.builtin.apt" in t or "ansible.builtin.yum" in t
                for t in taskcontainer.tasks
            )
        )
        # Check echo with redirect
        self.assertTrue(
            any(
                "ansible.builtin.copy" in t or "ansible.builtin.lineinfile" in t
                for t in taskcontainer.tasks
            )
        )

    def test_echo_redirect(self):
        config = {}
        parser = BashLexParser(
            script_string="""
echo "hello" > /tmp/hello.txt
echo "append" >> /tmp/hello.txt
cat < output.txt
wc -l < users
        """,
            config=config,
        )
        taskcontainer = parser.parse()
        # ignore cat and wc
        self.assertEqual(len(taskcontainer.tasks), 2)

    def test_if_result_code(self):
        parser = BashLexParser(file_path=self.test_script_path, config={})
        taskcontainer = parser.parse()
        # Find the touch task with a 'when' condition
        touch_tasks = [
            t
            for t in taskcontainer.tasks
            if t.get("ansible.builtin.file", {}).get("path") == "/tmp/ok.txt"
        ]
        self.assertTrue(any("when" in t for t in touch_tasks))
        # The 'when' should reference a register and 'is succeeded' or 'is failed'
        self.assertTrue(
            any(
                "is succeeded" in t.get("when", "") or "is failed" in t.get("when", "")
                for t in touch_tasks
            )
        )

    def test_if_result_code_inline(self):
        config = {}
        parser = BashLexParser(
            script_string="""
echo "append" >> /tmp/hello.txt
if [ $? -eq 0 ]; then
  touch /tmp/ok.txt
fi
        """,
            config=config,
        )
        taskcontainer = parser.parse()
        # Find the echo task with a 'when' condition for variable comparison
        echo_tasks = [
            t
            for t in taskcontainer.tasks
            if t.get("ansible.builtin.file", {}).get("path") == "/tmp/ok.txt"
        ]
        self.assertTrue(any("when" in t for t in echo_tasks))
        # The 'when' should reference MYVAR == 'wibble'
        self.assertTrue(
            any(
                "echo_redirect_append_1" in str(t.get("when", ""))
                and "succeeded" in str(t.get("when", ""))
                for t in echo_tasks
            )
        )

    def test_if_variable_comparison_inline(self):
        config = {}
        parser = BashLexParser(
            script_string="""
MYVAR=wibble
if [ "$MYVAR" -eq "wibble" ]; then
  touch /tmp/ok.txt
fi
        """,
            config=config,
        )
        taskcontainer = parser.parse()
        # Find the echo task with a 'when' condition for variable comparison
        echo_tasks = [
            t
            for t in taskcontainer.tasks
            if t.get("ansible.builtin.file", {}).get("path") == "/tmp/ok.txt"
        ]
        self.assertTrue(any("when" in t for t in echo_tasks))
        # The 'when' should reference MYVAR == 'wibble'
        self.assertTrue(
            any(
                "MYVAR" in str(t.get("when", "")) and "wibble" in str(t.get("when", ""))
                for t in echo_tasks
            )
        )

    def test_if_ne_inline(self):
        config = {}
        parser = BashLexParser(
            script_string="""
MYVAR=wibble
if [ "$MYVAR" -ne "wibble" ]; then
  touch /tmp/ok.txt
fi
if [ "$MYVAR" -lt "wibble" ]; then
  touch /tmp/ok.txt
fi
if [ "$MYVAR" -le "wibble" ]; then
  touch /tmp/ok.txt
fi
if [ "$MYVAR" -gt "wibble" ]; then
  touch /tmp/ok.txt
fi
if [ "$MYVAR" -ge "wibble" ]; then
  touch /tmp/ok.txt
fi
        """,
            config=config,
        )
        taskcontainer = parser.parse()
        self.assertEqual(len(taskcontainer.tasks), 5)
        self.assertEqual(taskcontainer.tasks[0]["when"], "$MYVAR != wibble", "dest dir")
        self.assertEqual(taskcontainer.tasks[1]["when"], "$MYVAR < wibble", "dest dir")
        self.assertEqual(taskcontainer.tasks[2]["when"], "$MYVAR <= wibble", "dest dir")
        self.assertEqual(taskcontainer.tasks[3]["when"], "$MYVAR > wibble", "dest dir")
        self.assertEqual(taskcontainer.tasks[4]["when"], "$MYVAR >= wibble", "dest dir")
        # Find the echo task with a 'when' condition for variable comparison
        echo_tasks = [
            t
            for t in taskcontainer.tasks
            if t.get("ansible.builtin.file", {}).get("path") == "/tmp/ok.txt"
        ]
        self.assertTrue(any("when" in t for t in echo_tasks))
        # The 'when' should reference MYVAR == 'wibble'
        self.assertTrue(
            any(
                "MYVAR" in str(t.get("when", "")) and "wibble" in str(t.get("when", ""))
                for t in echo_tasks
            )
        )

    def test_for_loop_simple(self):
        config = {}
        parser = BashLexParser(
            script_string="""
for s in server1 server2 server3
do
    cp /tmp/${s}.txt /tmp/bar_${s}
    ln /tmp/${s}_dest.txt /tmp/bar_${s}_src
done
            """,
            config=config,
        )
        taskcontainer = parser.parse()
        self.assertTrue(len(taskcontainer.tasks), 6)
        # Find the echo task with a 'when' condition for variable comparison
        # echo_tasks = [t for t in tasks if t.get("ansible.builtin.debug", {}).get("msg") == "matched"]
        # self.assertTrue(any("when" in t for t in echo_tasks))
        # The 'when' should reference MYVAR == 'wibble'
        # self.assertTrue(any("MYVAR" in str(t.get("when", "")) and "wibble" in str(t.get("when", "")) for t in echo_tasks))

    def test_scp_simple_push_and_pull(self):
        config = {
            "pull": True,
            "push": True,
        }
        parser = BashLexParser(
            script_string="""
scp -i ~/.ssh/id_rsa -P 2200 -r ./dir /var/tmp/
scp /path/to/local/file.txt username@remote_host:/path/to/remote/directory/
scp -r ./myfolder user@host:/remote/path/
scp -r ./myfolder user@host:/remote/path/
scp -P 2222 file.txt user@10.0.0.1:/home/user/
scp -i ~/.ssh/id_rsa -P 2200 -r ./dir host:/var/tmp/
            """,
            config=config,
        )
        taskcontainer = parser.parse()
        self.assertTrue(len(taskcontainer.tasks), 5)
        self.assertEqual(
            taskcontainer.tasks[1]["ansible.builtin.copy"]["dest"],
            "/path/to/remote/directory/",
            "dest dir",
        )
        self.assertEqual(
            taskcontainer.tasks[2]["ansible.builtin.copy"]["dest"],
            "/remote/path/",
            "dest dir",
        )

        # Find the echo task with a 'when' condition for variable comparison
        # echo_tasks = [t for t in tasks if t.get("ansible.builtin.debug", {}).get("msg") == "matched"]
        # self.assertTrue(any("when" in t for t in echo_tasks))
        # The 'when' should reference MYVAR == 'wibble'
        # self.assertTrue(any("MYVAR" in str(t.get("when", "")) and "wibble" in str(t.get("when", "")) for t in echo_tasks))

    def test_scp_simple_just_push(self):
        config = {
            "pull": False,
            "push": True,
        }
        parser = BashLexParser(
            script_string="""
scp -i ~/.ssh/id_rsa -P 2200 -r  ./dir                   /var/tmp/
scp                              user@rh:/local/file.txt /path/to/remote/directory/
scp -r                           ./myfolder              user@host:/remote/path2/
scp -r                           ./myfolder              user@host:/remote/path/
scp -P 2222                      file.txt                user@10.0.0.1:/home/user/
scp -i ~/.ssh/id_rsa -P 2200 -r ./dir                    host:/var/tmp2/
            """,
            config=config,
        )
        taskcontainer = parser.parse()
        self.assertEqual(len(taskcontainer.tasks), 5)
        self.assertEqual(
            taskcontainer.tasks[1]["ansible.builtin.copy"]["dest"],
            "/remote/path2/",
            "dest dir",
        )
        self.assertEqual(
            taskcontainer.tasks[2]["ansible.builtin.copy"]["dest"],
            "/remote/path/",
            "dest dir",
        )

    def test_scp_simple_just_pull(self):
        config = {
            "pull": True,
            "push": False,
        }
        parser = BashLexParser(
            script_string="""
scp -i ~/.ssh/id_rsa -P 2200 -r  ./dir                   /var/tmp/
scp                              user@rh:/local/file.txt /path/to/remote/directory/
scp -r                           ./myfolder              user@host:/remote/path2/
scp -r                           ./myfolder              user@host:/remote/path/
scp -P 2222                      file.txt                user@10.0.0.1:/home/user/
scp -i ~/.ssh/id_rsa -P 2200 -r ./dir                    host:/var/tmp2/
            """,
            config=config,
        )
        taskcontainer = parser.parse()
        self.assertEqual(len(taskcontainer.tasks), 2)
        self.assertEqual(
            taskcontainer.tasks[0]["ansible.builtin.copy"]["dest"],
            "/var/tmp/",
            "dest dir",
        )
        self.assertEqual(
            taskcontainer.tasks[1]["ansible.builtin.copy"]["dest"],
            "/path/to/remote/directory/",
            "dest dir",
        )

    def test_split_host(self):
        bv = BashScriptVisitor(tasks=None, parser=None)

        splits = bv.split_host("wibble@a:/floob/")
        self.assertEqual(
            splits,
            {"host": "a", "path": "/floob/", "recursive": True, "user": "wibble"},
        )

        splits = bv.split_host("wibble@a:/floob")
        self.assertEqual(
            splits,
            {"host": "a", "path": "/floob", "recursive": False, "user": "wibble"},
        )

        splits = bv.split_host("wibble@127.0.0.1:/floob")
        self.assertEqual(
            splits,
            {
                "host": "127.0.0.1",
                "path": "/floob",
                "recursive": False,
                "user": "wibble",
            },
        )

    def test_export(self):
        config = {}
        parser = BashLexParser(
            script_string="""
BAR=squawk
export FOO=wibble_${BAR}
touch /tmp/${FOO}.txt
touch /tmp/${BAR}.txt
BAR=squeal
touch /tmp/${BAR}.txt
        """,
            config=config,
        )
        taskcontainer = parser.parse()
        self.assertEqual(len(taskcontainer.tasks), 3)
        self.assertEqual(
            taskcontainer.tasks[0]["ansible.builtin.file"]["path"],
            "/tmp/{{ FOO }}.txt",
            "path from export var",
        )
        self.assertEqual(
            taskcontainer.tasks[1]["ansible.builtin.file"]["path"],
            "/tmp/squawk.txt",
            "path from export var",
        )
        self.assertEqual(
            taskcontainer.tasks[2]["ansible.builtin.file"]["path"],
            "/tmp/squeal.txt",
            "path from export var",
        )

    def test_umask(self):
        config = {}
        parser = BashLexParser(
            script_string="""
umask 0077
touch /tmp/foo.txt
umask 0022
touch /tmp/bar.txt
MY_UMASK=0027
umask $MY_UMASK
touch /tmp/bar_foo.txt
export EXPORTED_UMASK=0777
umask $EXPORTED_UMASK
touch /tmp/bar_groob.txt
        """,
            config=config,
        )
        taskcontainer = parser.parse()
        self.assertEqual(len(taskcontainer.tasks), 4)
        self.assertEqual(
            taskcontainer.tasks[0]["ansible.builtin.file"]["mode"], "0600", "dest dir"
        )
        self.assertEqual(
            taskcontainer.tasks[1]["ansible.builtin.file"]["mode"], "0644", "dest dir"
        )
        self.assertEqual(
            taskcontainer.tasks[2]["ansible.builtin.file"]["mode"], "0640", "dest dir"
        )
        # until we can compute mode from umask as a jinja template this
        # will be interpreted
        self.assertEqual(
            taskcontainer.tasks[3]["ansible.builtin.file"]["mode"], "0000", "dest dir"
        )

    def test_variables(self):
        tasks = []
        parser = None
        bsv = BashScriptVisitor(tasks, parser)
        # export FOO="-foo-"
        # rendered(jinja)     : "-foo-"
        # rendered(interpret) : "-foo-"
        bsv.set_variable("FOO", "-foo-", export=True)
        value = bsv.get_variable("FOO")
        rendered = bsv.interpret_variable(value)
        self.assertEqual(rendered, "-foo-", "rendered FOO")

        # BAR="flannel_${FOO}"
        # rendered(jinja)     : "flannel_{{ FOO }}"
        # rendered(interpret) : "flannel_-foo-"
        bsv.set_variable("BAR", "flannel_${FOO}")
        value = bsv.get_variable("BAR")
        rendered = bsv.interpret_variable(value, type="jinja")
        self.assertEqual(rendered, "flannel_-foo-", "rendered BAR")
        # all non-exported variables are non-jinja
        # self.assertEqual(rendered,"flannel_{{ FOO }}","rendered BAR")
        rendered = bsv.interpret_variable(value)
        self.assertEqual(rendered, "flannel_-foo-", "rendered BAR")
        # all non-exported variables are non-jinja
        # self.assertEqual(rendered,"flannel_{{ FOO }}","rendered BAR")


if __name__ == "__main__":
    unittest.main()  # pragma: no cover
