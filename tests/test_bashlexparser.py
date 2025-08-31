import unittest
import os
from script2ansible.BashLexParser import BashLexParser, BashScriptVisitor

class TestBashLexParser(unittest.TestCase):
    def setUp(self):
        self.test_script_path = "/tmp/test_bashlex_script.sh"
        self.test_script_content = (
            'MYVAR=wibble\n'
            'umask 0077\n'
            'mkdir -p $MYVAR\n'
            'touch /tmp/foo.txt\n'
            'ln -s /tmp/foo.txt /tmp/bar.txt\n'
            'cp /tmp/foo.txt /tmp/bar.txt\n'
            'ldconfig\n'
            'gunzip /tmp/archive.gz\n'
            'chmod 755 /tmp/foo.txt\n'
            'apt update\n'
            'apt install -y foo bar\n'
            'yum install -y baz\n'
            'echo "hello" > /tmp/hello.txt\n'
            'echo "append" >> /tmp/hello.txt\n'
            'if [ $? -eq 0 ]; then\n'
            '  touch /tmp/ok.txt\n'
            'fi\n'
            'if [ "$MYVAR" -eq "wibble" ]; then\n'
            '  echo "matched" >> /tmp/ok.txt\n'
            'fi\n'
            'scp /path/to/local/file.txt username@remote_host:/path/to/remote/directory/\n'
        )
        with open(self.test_script_path, "w") as f:
            f.write(self.test_script_content)

    def tearDown(self):
        os.remove(self.test_script_path)

    def test_parse_basic_commands(self):
        parser = BashLexParser(file_path=self.test_script_path, config={})
        tasks = parser.parse()
        # Check mkdir task
        self.assertTrue(any(t.get("ansible.builtin.file", {}).get("state") == "directory" for t in tasks))
        # Check touch task
        self.assertTrue(any(t.get("ansible.builtin.file", {}).get("state") == "touch" for t in tasks))
        # Check ln task
        self.assertTrue(any(t.get("ansible.builtin.file", {}).get("state") in ("link", "hard") for t in tasks))
        # Check cp task
        self.assertTrue(any("ansible.builtin.copy" in t for t in tasks))
        # Check scp task hahahahaha
        self.assertTrue(any("ansible.builtin.copy" in t for t in tasks))        
        # Check ldconfig
        self.assertTrue(any(t.get("ansible.builtin.command") == "ldconfig" for t in tasks))
        # Check gunzip
        self.assertTrue(any("ansible.builtin.unarchive" in t for t in tasks))
        # Check chmod
        self.assertTrue(any(t.get("ansible.builtin.file", {}).get("mode") == "755" for t in tasks))
        # Check apt/yum install
        self.assertTrue(any("ansible.builtin.apt" in t or "ansible.builtin.yum" in t for t in tasks))
        # Check echo with redirect
        self.assertTrue(any("ansible.builtin.copy" in t or "ansible.builtin.lineinfile" in t for t in tasks))

    def test_if_result_code(self):
        parser = BashLexParser(file_path=self.test_script_path, config= {})
        tasks = parser.parse()
        # Find the touch task with a 'when' condition
        touch_tasks = [t for t in tasks if t.get("ansible.builtin.file", {}).get("path") == "/tmp/ok.txt"]
        self.assertTrue(any("when" in t for t in touch_tasks))
        # The 'when' should reference a register and 'is succeeded' or 'is failed'
        self.assertTrue(any("is succeeded" in t.get("when", "") or "is failed" in t.get("when", "") for t in touch_tasks))

    def test_if_result_code_inline(self):
        config = {}
        parser = BashLexParser(script_string="""
echo "append" >> /tmp/hello.txt
if [ $? -eq 0 ]; then
  touch /tmp/ok.txt
fi
        """, config=config)   
        tasks = parser.parse()
        # Find the echo task with a 'when' condition for variable comparison
        echo_tasks = [t for t in tasks if t.get("ansible.builtin.file", {}).get("path") == "/tmp/ok.txt"]
        self.assertTrue(any("when" in t for t in echo_tasks))
        # The 'when' should reference MYVAR == 'wibble'
        self.assertTrue(any("echo_redirect_append_1" in str(t.get("when", "")) and "succeeded" in str(t.get("when", "")) for t in echo_tasks))

    def test_if_variable_comparison_inline(self):
        config = {}
        parser = BashLexParser(script_string="""
MYVAR=wibble
if [ "$MYVAR" -eq "wibble" ]; then
  touch /tmp/ok.txt
fi
        """, config=config)   
        tasks = parser.parse()
        # Find the echo task with a 'when' condition for variable comparison
        echo_tasks = [t for t in tasks if t.get("ansible.builtin.file", {}).get("path") == "/tmp/ok.txt"]
        self.assertTrue(any("when" in t for t in echo_tasks))
        # The 'when' should reference MYVAR == 'wibble'
        self.assertTrue(any("MYVAR" in str(t.get("when", "")) and "wibble" in str(t.get("when", "")) for t in echo_tasks))
    
    def test_for_loop_simple(self):
        config = {}
        parser = BashLexParser(script_string="""
for s in server1 server2 server3
do
    cp /tmp/${s}.txt /tmp/bar_${s}
    ln /tmp/${s}_dest.txt /tmp/bar_${s}_src
done
            """, config=config)   
        tasks = parser.parse()
        self.assertTrue(len(tasks),6)
        # Find the echo task with a 'when' condition for variable comparison
        #echo_tasks = [t for t in tasks if t.get("ansible.builtin.debug", {}).get("msg") == "matched"]
        #self.assertTrue(any("when" in t for t in echo_tasks))
        # The 'when' should reference MYVAR == 'wibble'
        #self.assertTrue(any("MYVAR" in str(t.get("when", "")) and "wibble" in str(t.get("when", "")) for t in echo_tasks))
    def test_scp_simple_push_and_pull(self):
        config = {"pull" : True,
                  "push" : True,}
        parser = BashLexParser(script_string="""
scp -i ~/.ssh/id_rsa -P 2200 -r ./dir /var/tmp/
scp /path/to/local/file.txt username@remote_host:/path/to/remote/directory/ 
scp -r ./myfolder user@host:/remote/path/
scp -r ./myfolder user@host:/remote/path/
scp -P 2222 file.txt user@10.0.0.1:/home/user/
scp -i ~/.ssh/id_rsa -P 2200 -r ./dir host:/var/tmp/

            """, config=config)   
        tasks = parser.parse()
        self.assertTrue(len(tasks),5)
        self.assertEqual(tasks[1]['ansible.builtin.copy']['dest'] ,'/path/to/remote/directory/',"dest dir")
        self.assertEqual(tasks[2]['ansible.builtin.copy']['dest'] ,'/remote/path/',"dest dir")

        # Find the echo task with a 'when' condition for variable comparison
        #echo_tasks = [t for t in tasks if t.get("ansible.builtin.debug", {}).get("msg") == "matched"]
        #self.assertTrue(any("when" in t for t in echo_tasks))
        # The 'when' should reference MYVAR == 'wibble'
        #self.assertTrue(any("MYVAR" in str(t.get("when", "")) and "wibble" in str(t.get("when", "")) for t in echo_tasks))

    def test_scp_simple_just_push(self):
        config = {"pull" : False,
                  "push" : True,}
        parser = BashLexParser(script_string="""
scp -i ~/.ssh/id_rsa -P 2200 -r  ./dir                   /var/tmp/
scp                              user@rh:/local/file.txt /path/to/remote/directory/ 
scp -r                           ./myfolder              user@host:/remote/path2/
scp -r                           ./myfolder              user@host:/remote/path/
scp -P 2222                      file.txt                user@10.0.0.1:/home/user/
scp -i ~/.ssh/id_rsa -P 2200 -r ./dir                    host:/var/tmp2/
            """, config=config)   
        tasks = parser.parse()
        self.assertEqual(len(tasks),5)
        self.assertEqual(tasks[1]['ansible.builtin.copy']['dest'] ,'/remote/path2/',"dest dir")
        self.assertEqual(tasks[2]['ansible.builtin.copy']['dest'] ,'/remote/path/',"dest dir")

    def test_scp_simple_just_pull(self):
        config = {"pull" : True,
                  "push" : False,}
        parser = BashLexParser(script_string="""
scp -i ~/.ssh/id_rsa -P 2200 -r  ./dir                   /var/tmp/
scp                              user@rh:/local/file.txt /path/to/remote/directory/ 
scp -r                           ./myfolder              user@host:/remote/path2/
scp -r                           ./myfolder              user@host:/remote/path/
scp -P 2222                      file.txt                user@10.0.0.1:/home/user/
scp -i ~/.ssh/id_rsa -P 2200 -r ./dir                    host:/var/tmp2/
            """, config=config)   
        tasks = parser.parse()
        self.assertEqual(len(tasks),2)
        self.assertEqual(tasks[0]['ansible.builtin.copy']['dest'] ,'/var/tmp/',"dest dir")
        self.assertEqual(tasks[1]['ansible.builtin.copy']['dest'] ,'/path/to/remote/directory/',"dest dir")


    def test_split_host(self):
        bv = BashScriptVisitor(tasks=None,parser=None)
        
        splits = bv.split_host('wibble@a:/floob/')
        self.assertEqual(splits,{'host': 'a',
                                 'path': '/floob/', 
                                 'recursive': True, 
                                 'user': 'wibble'})
        
        splits = bv.split_host('wibble@a:/floob')
        self.assertEqual(splits,{'host': 'a',
                                 'path': '/floob', 
                                 'recursive': False, 
                                 'user': 'wibble'})
        
        splits = bv.split_host('wibble@127.0.0.1:/floob')
        self.assertEqual(splits,{'host': '127.0.0.1',
                                 'path': '/floob', 
                                 'recursive': False, 
                                 'user': 'wibble'})


if __name__ == "__main__":
    unittest.main()
