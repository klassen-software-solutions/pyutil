"""Tools for running command line programs and dealing with their results.

This is essentially high level API around `subprocess`.
"""

import logging
import subprocess


def run(command: str, directory: str = None):
    """Run a command.

    Note that anything written to the standard output or error devices, will be
    echoed to that device.

    Args:
       command: the command, complete with arguments, to be run
       directory: if specified, the command will be run in that directory. If not
                  specified, the command will be run in the current directory.

    Raises:
       FileNotFoundError: if a non-existant directory is specified
       subprocess.CalledProcessError: if there is a problem running the command.

    If the directory is not specified, then it will run in the current directory.
    """
    logging.debug("Running command: %s", command)
    subprocess.run("%s" % command, shell=True, check=True, cwd=directory)


def get_run(command: str, directory: str = None) -> str:
    """Run a command and return its standard output as a string.

    Note that anything written to the standard error device will still be written
    to the standard error device.

    Args:
       command: the command, complete with arguments, to be run
       directory: if specified, the command will be run in that directory. If not
                  specified, the command will be run in the current directory.

    Raises:
       FileNotFoundError: if a non-existant directory is specified
       subprocess.CalledProcessError: if there is a problem running the command.

    If the directory is not specified, then it will run in the current directory.
    """
    logging.debug("Running command: %s", command)
    res = subprocess.run("%s" % command, shell=True, check=True, cwd=directory,
                         stdout=subprocess.PIPE)
    return res.stdout.decode('utf-8').strip()


def process(command: str, directory: str = None, as_string: bool = True):
    """Run a command and return the standard output as a pipe for processing.

    Note that anything written to the standard error device will still be written
    to the standard error device. At present our API does not allow you to determine
    if the command returned an error result or not. If you need to do that, you
    will need to call subprocess.Popen manually.

    Args:
       command: the command, complete with arguments, to be run
       directory: if specified, the command will be run in that directory. If not
                  specified, the command will be run in the current directory.
       as_string: if true, each line will be decoded as a utf-8 string. Otherwise
                  each line will be passed as binary data.

    Raises:
       FileNotFoundError: if a non-existant directory is specified
       subprocess.CalledProcessError: if there is a problem running the command

    Example:
        for line in command.process('ls -l'):
            print("found: %s" % command.decode(line))

    If the directory is not specified, then it will run in the current directory.
    """
    logging.debug("Processing command: %s", command)
    with subprocess.Popen("%s" % command,
                          shell=True,
                          cwd=directory,
                          stdout=subprocess.PIPE) as pipe:
        for line in pipe.stdout:
            if as_string:
                yield line.decode('utf-8').rstrip()
            else:
                yield line
        pipe.communicate()
        if pipe.returncode != 0:
            raise subprocess.CalledProcessError(pipe.returncode, command)
