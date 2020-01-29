import subprocess
import time
import unittest

import kss.util.command as command

class CommandTestCase(unittest.TestCase):
    def test_run(self):
        # The only "assertion" for the next lines is that no exception is thrown.
        command.run("pwd")
        command.run("pwd", directory="Tests")
        with self.assertRaises(subprocess.CalledProcessError):
            command.run("no-such-command")
        with self.assertRaises(FileNotFoundError):
            command.run("pwd", directory="/no/such/directory")
        with self.assertRaises(ValueError):
            command.run(None)
        with self.assertRaises(ValueError):
            command.run("")

    def test_get_run(self):
        self.assertEqual(command.get_run("echo 'hello world'"), "hello world")
        self.assertTrue(command.get_run("pwd", directory="Tests").endswith("Tests"))
        self.assertEqual(command.get_run("echo 'hi' ; >&2 echo 'there'"), "hi")
        with self.assertRaises(subprocess.CalledProcessError):
            command.get_run("no-such-command")
        with self.assertRaises(FileNotFoundError):
            command.get_run("pwd", directory="/no/such/directory")
        with self.assertRaises(ValueError):
            command.get_run(None)
        with self.assertRaises(ValueError):
            command.get_run("")

    def test_process(self):
        line_count = 0
        for line in command.process('ls -l'):
            line_count += 1
        self.assertTrue(line_count >= 14)

        test_count = 0
        for line in command.process("ls -l | awk '{print $9}'", directory="Tests"):
            if line.startswith("test_"):
                test_count += 1
        self.assertTrue(test_count >= 2)

        for line in command.process("echo 'hi'"):
            self.assertTrue(line == "hi")

        for line in command.process("echo 'hi'", as_string=False):
            self.assertTrue(line == b'hi\n')

        with self.assertRaises(subprocess.CalledProcessError):
            for line in command.process("no-such-command"):
                self.fail("Should never see this: %s" % line)

        with self.assertRaises(FileNotFoundError):
            for line in command.process("ls -l", directory="/no/such/directory"):
                self.fail("Should never see this: %s" % line)

        with self.assertRaises(ValueError):
            for line in command.process(None):
                self.fail("Should never see this: %s" % line)

        with self.assertRaises(ValueError):
            for line in command.process(""):
                self.fail("Should never see this: %s" % line)
