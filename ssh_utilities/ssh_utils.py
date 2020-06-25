import os
import shutil
import sys
import time
from abc import ABC, abstractclassmethod, abstractmethod, abstractstaticmethod
from contextlib import contextmanager, redirect_stdout
from functools import wraps
from os.path import join as jn
from stat import S_ISDIR
from typing import TYPE_CHECKING, Optional, Union
from pathlib import Path
from types import MethodType

import getpass
import paramiko
from colorama import Back, Fore, init

from .utils import FakeLog, N_lines_up, parse_ssh_config
from .utils import bytes_2_human_readable as b2h

if TYPE_CHECKING:
    from logging import Logger

init(autoreset=True)
G = Fore.GREEN
LG = Fore.LIGHTGREEN_EX
R = Fore.RESET
RD = Fore.RED
C = Fore.LIGHTCYAN_EX
Y = Fore.YELLOW


def lprint(text, quiet=False):
    """ Function that limits print output. """
    if quiet is True:
        pass
    else:
        print(text)


def for_all_methods(decorator, exclude=[]):
    def decorate(cls):
        for attr in cls.__dict__:
            if callable(getattr(cls, attr)) and attr not in exclude:
                setattr(cls, attr, decorator(getattr(cls, attr)))
        return cls
    return decorate


def check_connections(function):
    ''' A decorator to check SSH connections. '''
    @wraps(function)
    def connect_wrapper(self, *args, **kwargs):

        def negotiate():
            try:
                self.c.close()
            except Exception as e:
                self.log.exception(f"Couldn't close connection: {e}")

            self.auth_tries = 1
            success = self.__get_ssh__()
            if success is True:
                if self.sftp_open is True:
                    success = self.openSftp()
            else:
                return False

            self.log.exception(f"Relevant variables:\n"
                               f"success:    {success}\n"
                               f"password:   {self.password}\n"
                               f"address:    {self.address}\n"
                               f"username:   {self.username}\n"
                               f"ssh class:  {type(self.c)}\n"
                               f"auth tries: {self.auth_tries}\n"
                               f"sftp class: {type(self.sftp)}")
            if self.sftp_open is True:
                self.log.exception(f"{self.remote_home}")

            return success

        n = function.__name__
        err = None
        try:
            return function(self, *args, **kwargs)
        except paramiko.ssh_exception.NoValidConnectionsError as e:
            err = e
            self.log.exception(f"Caught paramiko error in {n}: {e}")
        except paramiko.ssh_exception.SSHException as e:
            err = e
            self.log.exception(f"Caught paramiko error in {n}: {e}")
        except AttributeError as e:
            err = e
            self.log.exception(f"Caught attribute error in {n}: {e}")
        except OSError as e:
            err = e
            self.log.exception(f"Caught OS error in {n}: {e}")
        except paramiko.SFTPError as e:
            # garbage packets,
            # see: https://github.com/paramiko/paramiko/issues/395
            self.log.exception(f"Caught paramiko error in {n}: {e}")
        except Exception as e:
            self.log.exception(f"Caught unclassified exception in {n}: {e}")
        finally:
            if err is not None:
                s = False
                while s is False:
                    self.log.warning("Connection is down, trying to reconnect")
                    s = negotiate()
                    if s is False:
                        self.log.warning("Unsuccessful, wait 60 seconds "
                                         "before next try")
                        time.sleep(60)
                    else:
                        self.log.info("Connection restablished, continuing ..")

                connect_wrapper(self, *args, **kwargs)

    return connect_wrapper


class ActualSpeed:

    def __init__(self, total=0):
        self.average_speed = 0.0
        self.total = total
        self.done = 0

    def start(self, total_size):
        self.__init__(total=total_size)

    @contextmanager
    def update(self, size, quiet):
        t_start = time.time()
        yield
        cp_time = time.time() - t_start

        self.average_speed = (self.average_speed + (size / cp_time)) / 2
        self.done += size

        percent_done = int(100 * (self.done / self.total))

        if percent_done < 10:
            progress_bar = f"{' ' * 49}{percent_done}%{' ' * 49}"
        elif percent_done == 100:
            progress_bar = f"{' ' * 47}{percent_done}%{' ' * 49}"
        else:
            progress_bar = f"{' ' * 48}{percent_done}%{' ' * 49}"

        progress_bar_1 = progress_bar[:percent_done]
        progress_bar_2 = progress_bar[percent_done:]

        lprint(f"|{Back.LIGHTGREEN_EX}{progress_bar_1}{Back.RESET}"
               f"{progress_bar_2}| {b2h(self.average_speed)}/s", quiet)


class _ConnectionABC(ABC):

    @abstractmethod
    def close(self):
        pass

    @abstractmethod
    def ssh_log(self, log_file=""):
        pass

    @abstractmethod
    def openSftp(self, quiet=False):
        pass

    @abstractmethod
    def downloadTree(self, src, dst, include="all", remove_after=True,
                     quiet=False):
        pass

    @abstractmethod
    def uploadTree(self, src, dst, remove_after=True, quiet=False):
        pass

    @abstractmethod
    def isfile(self, path):
        pass

    @abstractmethod
    def isdir(self, path):
        pass

    @abstractmethod
    def mkdir(self, path, mode=511, quiet=True):
        pass

    @abstractmethod
    def rmtree(self, path, ignore_errors=False, quiet=True):
        pass

    @abstractmethod
    def listdir(self, path):
        pass

    def measure(self, position, quiet=False):

        if position:
            self.start = time.time()
        else:
            self.end = time.time()
            if not quiet:
                print(f"CPU time: {(self.end - self.start):.2f}s")
            else:
                pass

    @contextmanager
    def context_measure(self, quiet=False):
        start = time.time()
        yield
        end = time.time()
        if not quiet:
            print(f"CPU time: {(end - start):.2f}s")
        else:
            pass

    @abstractmethod
    @contextmanager
    def open_file(self, filename, mode, encoding):
        pass


@for_all_methods(check_connections, exclude=["__init__", "__get_ssh__",
                                             "ssh_log", "open"])
class SSHConnection(_ConnectionABC):
    """Self keeping ssh connection class, able to execute commands and
       file operations.
    """

    def __init__(self, address, username, password=None, rsa_key_file=None,
                 line_rewrite=True, no_warn=False, server_name=None,
                 logger=None):

        lprint(f"{C}Connecting to server:{R} {username}@{address}")
        if no_warn is True:
            lprint(f"{R}When running an executale on server always make"
                   "sure that full path is specified!!!\n")

        # set login credentials
        self.password = password
        self.address = address
        self.username = username
        self.rsa_key = paramiko.RSAKey.from_private_key_file(rsa_key_file)

        # negotiate connection
        self.auth_tries = 1
        success = self.__get_ssh__()
        if success is False:
            sys.exit()

        # misc
        self.sftp_open = False
        self.line_rewrite = line_rewrite
        if server_name is None:
            self.server_name = address
        else:
            self.server_name = server_name.upper()

        self.speed = ActualSpeed()

        if logger is None:
            self.log = FakeLog
        else:
            self.log = logger

        self.local = False

    def __get_ssh__(self):

        try:
            self.c = paramiko.client.SSHClient()
            self.c.set_missing_host_key_policy(paramiko.client.AutoAddPolicy())

            if self.password is not None:
                self.c.connect(self.address, username=self.username,
                               password=self.password, look_for_keys=False)
            else:
                self.c.connect(self.address, username=self.username,
                               pkey=self.rsa_key)

        except paramiko.ssh_exception.AuthenticationException as e:
            self.log.warning(f"Error in authentication {e}. Trying again ...")
            self.__get_ssh__()
            self.auth_tries += 1
            if self.auth_tries > 3:
                return False
        except paramiko.ssh_exception.NoValidConnectionsError as e:
            self.log.warning(f"Error in connecting {e}. Trying again ...")
            self.__get_ssh__()
            self.auth_tries += 1
            if self.auth_tries > 3:
                return False
        else:
            return True

    def close(self):
        """ Close SSH connection """

        lprint(f"{G}Closing ssh connection to:{R} {self.server_name}")
        self.c.close()

    @staticmethod
    def ssh_log(log_file="paramiko.log", level="WARN"):
        """Initialize paramiko logging functionality

           arguments:
           log_file: location of the log file (default: paramiko.log)
        """

        if os.path.isfile(log_file):
            os.remove(log_file)
        lprint(f"{Y}Logging ssh session to file:{R} {log_file}\n")
        paramiko.util.log_to_file(log_file, level=level)

    def sendCommand(self, command, suppres_out, quiet=True, make_error=False):

        commands = command.split(" && ")
        if len(commands) == 1:
            lprint(f"{Y}Executing command on remote:{R} {command}\n", quiet)
        else:
            lprint(f"{Y}Executing commands on remote:{R} {commands[0]}", quiet)
            for c in commands[1:]:
                lprint(" "*30 + c, quiet)

        # vykonat prikaz
        # stdin, stdout, stderr
        stdout = self.c.exec_command(command, get_pty=True)[1]

        while not stdout.channel.exit_status_ready():
            # print data when available
            if stdout.channel.recv_ready():
                alldata = stdout.channel.recv(1024)
                prevdata = b"1"
                while prevdata:
                    prevdata = stdout.channel.recv(1024)
                    alldata += prevdata

                if not suppres_out:
                    lprint(f"{C}Printing remote output\n{'-' * 111}{R}", quiet)
                    lprint(str(alldata, "utf8"), quiet)
                    lprint(f"{C}{'-' * 111}{R}\n", quiet)

                return str(alldata, "utf8")

    def openSftp(self, quiet=False):
        self.sftp = self.c.open_sftp()
        self.sftp_open = True
        self.local_home = os.path.expanduser("~")

        for _ in range(3):  # niekedy zlyha preto sa opakuje viackrat
            try:
                self.remote_home = (self.sendCommand("echo $HOME", True,
                                                     quiet=True).strip())
            except AttributeError:
                e = Exception
                lprint(f"{RD}Cannot establish remote home, trying again...",
                       quiet)
            else:
                e = None
                break

        if e is not None:
            lprint(f"{RD}Remote home could not be found, exiting...", quiet)
            return False
        else:
            return True

    def sendFiles(self, files, remote_path, local_path, direction,
                  quiet=False):

        with super().context_measure(quiet):
            for f in files:
                file_remote = jn(remote_path, f)
                file_local = jn(local_path, f)

                if direction == "get":
                    lprint(f"{G}Copying from remote:{R} {self.server_name}@"
                           f"{file_remote}{LG}\n   --> local:{R} {file_local}",
                           quiet)

                    self.sftp.get(file_remote, file_local)

                if direction == "put":
                    lprint(f"{G}Copying from local:{R} {file_local}"
                           f"\n{LG} --> remote: {self.server_name}@"
                           f"{file_remote}", quiet)

                    self.sftp.put(file_remote, file_local)

    def __sftp_walk__(self, remote_path):
        path = remote_path
        files = []
        folders = []
        for f in self.sftp.listdir_attr(remote_path):
            if S_ISDIR(f.st_mode):
                folders.append(f.filename)
            else:
                files.append(f.filename)
        if files:
            yield path, files
        for folder in folders:
            new_path = jn(remote_path, folder)
            for x in self.__sftp_walk__(new_path):
                yield x

    def downloadTree(self, remote_path, local_path, include="all",
                     remove_after=True, quiet=False):

        sn = self.server_name

        local_copy = []
        remote_copy = []
        local_dirs = []
        size = []  # velkost suboru v byte-och

        # vytvorit zoznam priecinkov do ktorych sa bude kopitovat
        lprint(f"{C}Building directory structure "
               f"for download from remote... {R}\n\n", quiet)

        super().measure(True)

        # vymedzenie priecinkov ktore sa maju kopirovat
        for root, files in self.__sftp_walk__(remote_path):

            if include != "all":
                outer_continue = True
                for inc in include:
                    if inc in root:
                        outer_continue = False
                        break
                if outer_continue is True:
                    continue

            if self.line_rewrite is True:
                N_lines_up(1, quiet)
            lprint(f"{G}Searching remote directory:{R} {sn}@{root}", quiet)

            # zaznamenat priecinky ktore treba vytvorit na lokalnej strane
            directory = root.replace(remote_path, "")
            local_dirs.append(jn(local_path, directory))

            for f in files:
                local_copy.append(jn(local_path, directory, f))
                remote_copy.append(jn(root, f))
                size.append(self.sftp.lstat(jn(root, f)).st_size)

        # statistika kolko suborov sa bude kopirovat a ich objem
        n_files = len(remote_copy)
        total = sum(size)
        self.speed.start(total)
        lprint(f"\n|--> {C}Total number of files to copy:{R} {n_files}", quiet)
        lprint(f"|--> {C}Total size of files to copy:{R} {b2h(total)}", quiet)

        super().measure(False, quiet)

        # vytvorit priecinky na lokalnej strane do ktorych sa bude kopirovat
        lprint(f"\n{C}Creating directory structure on local side..{R} ", quiet)
        with super().context_measure(quiet):
            for d in local_dirs:
                if not os.path.exists(d):
                    os.makedirs(d)

        # prekopirovat
        lprint(f"\n{C}Copying...{R}\n", quiet)

        with super().context_measure(quiet):
            for i, (lc, rc, s) in enumerate(zip(local_copy, remote_copy,
                                                size)):

                lprint(f"{G}Copying remote:{R} {sn}@{rc}\n"
                       f"{G}   --> local:{R} {lc}", quiet)

                with self.speed.update(s, quiet):
                    self.sftp.get(rc, lc)

                if i < len(local_copy) - 1 and self.line_rewrite is True:
                    N_lines_up(3, quiet)

        lprint("", quiet)

        if remove_after is True:
            self.rmtree(remote_path)

    def uploadTree(self, local_path: str, remote_path: str,
                   remove_after: bool = True, quiet: bool = False):
        sn = self.server_name

        local_copy = []
        remote_copy = []
        remote_dirs = []
        size = []

        # vytvorit zoznam priecinkov na kopirovanie
        lprint(f"{C}Building directory structure for "
               f"upload to remote...{R} \n\n", quiet)

        super().measure(True)

        for root, _, files in os.walk(local_path):
            if self.line_rewrite is True:
                N_lines_up(1, quiet)
            lprint(f"{G}Searching local directory:{R} {root}", quiet)

            # skip hidden dirs
            if root[0] == ".":
                continue

            # zaznamenat priecinky ktore treba vytvorit na vzdialenej strane
            directory = root.replace(local_path, "")
            remote_dirs.append(remote_path + directory)

            for f in files:
                local_copy.append(jn(root, f))
                remote_copy.append(jn(remote_path, directory, f))
                size.append(os.path.getsize(jn(root, f)))

        # statistika kolko suborov sa bude kopirovat a ich objem
        n_files = len(local_copy)
        total = sum(size)
        self.speed.start(total)

        lprint(f"\n|--> {C}Total number of files to copy:{R} {n_files}", quiet)
        lprint(f"|--> {C}Total size of files to copy: {R} {b2h(total)}", quiet)

        super().measure(False, quiet)

        # vytvorit strukturu priecinkov na vzdialenej strane
        lprint(f"\n{C}Creating directory structure on remote side..{R}", quiet)
        with super().context_measure(quiet):
            for i, rd in enumerate(remote_dirs):
                self.mkdir(rd)

        # prekopirovat
        lprint(f"\n{C}Copying...{R} \n", quiet)
        with super().context_measure(quiet):
            for i, (lc, rc, s) in enumerate(zip(local_copy, remote_copy,
                                                size)):
                lprint(f"{G}Copying local:{R} {lc}\n"
                       f"{G}--> remote:{R} {sn}@{rc}", quiet)

                with self.speed.update(s, quiet):
                    self.sftp.put(lc, rc)

                if i < len(local_copy) - 1 and self.line_rewrite is True:
                    N_lines_up(3, quiet)

        lprint("", quiet)

        if remove_after is True:
            shutil.rmtree(local_path)

    def isfile(self, path):
        try:
            return self.sftp.stat(path)
        except IOError:
            return False

    def isdir(self, path):
        return self.isfile(path)

    def mkdir(self, path, mode=511, quiet=True):
        if not self.isdir(path):
            lprint(f"{G}Creating directory:{R} {self.server_name}@{path}",
                   quiet)

            to_make = []
            actual = path

            while True:
                actual = os.path.dirname(actual)
                if not self.isdir(actual):
                    to_make.append(actual)
                else:
                    break

            for tm in reversed(to_make):
                try:
                    self.sftp.mkdir(tm, mode)
                except OSError as e:
                    raise OSError(f"Couldn't make dir {tm},\n probably "
                                  f"permission error: {e}")

            self.sftp.mkdir(path, mode)
        else:
            lprint(f"{G}Directory already exists:{R} "
                   f"{self.server_name}@{path}", quiet)

    def rmtree(self, path, ignore_errors=False, quiet=True):
        sn = self.server_name

        with super().context_measure(quiet):
            lprint(f"{G}Recursively removing dir:{R} {sn}@{path}", quiet)

            try:
                for root, files in self.__sftp_walk__(path):
                    for f in files:
                        f = jn(root, f)
                        lprint(f"{G}removing file:{R} {sn}@{f}", quiet)
                        if self.isfile(f):
                            self.sftp.remove(f)
                    if self.isdir(root):
                        self.sftp.rmdir(root)

                if self.isdir(path):
                    self.sftp.rmdir(path)
            except FileNotFoundError as e:
                if ignore_errors is True:
                    self.log.warning("Directory does not exist")
                else:
                    raise FileNotFoundError(e)

    def listdir(self, path):
        return self.sftp.listdir(path)

    def change_dir(self, path):
        self.sftp.chdir(path)

    # TODO not ready yet
    @contextmanager
    def open_file(self, filename: Union[str, Path], mode: str = "r",
                  encoding: str = "utf-8"):

        def _read_decode(self, size=None, encoding=encoding):
            data = self.read_and_decode(size=size)

            if isinstance(data, bytes):
                data = data.decode("utf-8")

            return data

        file_obj = self.sftp.open(filename)

        # rename old read method
        setattr(file_obj, "read_and_decode", getattr(file_obj, "read"))

        # repalce it with new that automatically decodes
        file_obj.read = MethodType(_read_decode, file_obj)

        try:
            yield file_obj
        finally:
            file_obj.close()


class LocalConnection(_ConnectionABC):
    """Emulates SSHConnection class on local PC"""

    def __init__(self, address, username, password=None, sshKey=None,
                 line_rewrite=True, no_warn=False, server_name=None,
                 logger=None):

        if server_name is None:
            from socket import gethostname
            self.server_name = gethostname().upper()
        else:
            self.server_name = server_name.upper()

        if logger is None:
            self.log = FakeLog
        else:
            self.log = logger

        self.local = True

    def close(self):
        """ Close emulated local connection """
        lprint(f"{G}Closing local connection")

    def ssh_log(self, log_file="paramiko.log", level="WARN"):
        lprint(f"{Y}Local sessions are not logged!")

    def openSftp(self, quiet=False):
        pass

    def downloadTree(self, src, dst, include="all", remove_after=True,
                     quiet=False):
        # TODO include parameter is not used!!!
        shutil.move(src, dst)

    def uploadTree(self, src, dst, remove_after=True, quiet=False):
        shutil.move(src, dst)

    def isfile(self, path):
        return os.path.isfile(path)

    def isdir(self, path):
        return os.path.isdir(path)

    def mkdir(self, path, mode=511, quiet=True):
        return os.mkdir(path, mode)

    def rmtree(self, path, ignore_errors=False, quiet=True):
        return shutil.rmtree(path, ignore_errors=ignore_errors)

    def listdir(self, path):
        return os.listdir(path)

    @contextmanager
    def open_file(self, filename: Union[str, Path], mode: str = "r",
                  encoding: str = "utf-8"):

        f = open(filename, mode)

        try:
            yield f
        finally:
            f.close()


class _ConnectionMeta(type):

    def __new__(cls, classname, bases, dictionary):
        dictionary["available_hosts"] = dict()
        for key, value in parse_ssh_config().items():
            dictionary["available_hosts"][key] = value
        return type.__new__(cls, classname, bases, dictionary)

    def __getitem__(cls, key):

        try:
            credentials = cls.available_hosts[key]
        except KeyError as e:
            raise ValueError(f"No such host({key}) available: {e}")
        else:
            return cls.open(credentials["name"], credentials["address"],
                            credentials["rsa_key"], server_name=key)


class Connection(metaclass=_ConnectionMeta):
    """ Class with self-keeping SSH or local connection.

    Main purpose is to have SSH connection with convenience methods which can
    be easily used. Connection is resiliet to errors and will reinitialize
    itself if for some reason it fails. It also has a local wariant which is
    mirroring its API but uses os and shutil modules under the hood.

    Upon import this class automatically reads ssh configuration file in:
    ~/.ssh/config if it is present. The class is then indexable by keys in
    config file so calling:

    >>> from ssh_utilities import Connection
    >>> Connection[<server_name>]
    >>> <ssh_utilities.ssh_utils.SSHConnection at 0x7efedff4fb38>

    returns an initialized connection instance.
    """

    @staticmethod
    def open(sshUsername: str, sshServer: Optional[str] = None,
             sshKey: Optional[str] = None, server_name: Optional[str] = None,
             logger: Optional["Logger"] = None) -> _ConnectionABC:
        """Initialize SSH or loacl connection.

        Local connection is only a wrapper around os and shutil module methods
        and its purpose is to mirror API of the SSHConnection class

        Parameters
        ----------
        sshUsername: str
            login name, only used for remote connections
        sshServer: str
            server address, numeric address or normal address
        sshKey: Optional[str]
            path to file with private rsa key. If left empty script will ask
            for password.
        server_name: str
            server name (default:None) only for id purposes, if it is left
            default than it will be replaced with address.
        logger: logging.Logger
            logger instance, If argument is left default than than logging
            messages will be rerouted to stdout/stderr.
        """

        if not sshServer:
            return LocalConnection(sshServer, sshUsername, sshKey=sshKey,
                                   server_name=server_name, logger=logger)
        else:
            if sshKey is None:
                lprint(f"Will login as {sshUsername} to {sshServer}")
                sshPassword = getpass.getpass(prompt="Enter password: ")

                c = SSHConnection(sshServer, sshUsername, password=sshPassword,
                                  line_rewrite=True, server_name=server_name,
                                  logger=logger)
            else:
                sshKey = os.path.expanduser(sshKey)
                lprint(f"Will login with private RSA key located in {sshKey}")

                c = SSHConnection(sshServer, sshUsername, rsa_key_file=sshKey,
                                  line_rewrite=True, server_name=server_name,
                                  logger=logger)

            return c
