[![Documentation Status](https://readthedocs.org/projects/ssh-utilities/badge/?version=latest)](https://ssh-utilities.readthedocs.io/en/latest/?badge=latest)

# Paramiko wrapper

Simple paramiko wrapper that aims to facilitate easy remote file operations
and command execution. The API vaguely follows python os library. Has also
local variant that mimics the remote API on local machine. The connection is resilient to interruptions. Everything is well documented by dostrings and
typed.

## Installation

1. `git clone https://github.com/marian-code/ssh-utilities.git`
2. `cd ssh_utilities`
3. `pip install -e .`
Use -e only to install in editable mode

If you encounter some import errors try installing from requirements.txt file
`pip install requirements.txt`

## Usage

API exposes three main classes:
`from .ssh_utils import SSHConnection, Connection, LocalConnection`
`Connection` is the main class that initializes other two as needed according to input parameters.

Connection supports dict-like indexing by values that are in
your ~/.ssh/config file

```python
>>> from ssh_utilities import Connection
>>> Connection[<server_name>]
>>> <ssh_utilities.ssh_utils.SSHConnection at 0x7efedff4fb38>
```

There is also a specific get method which is safer and with better typing
support than dict-like indexing

```python
>>> from ssh_utilities import Connection
>>> Connection.get(<server_name>)
>>> <ssh_utilities.ssh_utils.SSHConnection at 0x7efedff4fb38>
```

Class can be also used as a context manager.

```python
>>> from ssh_utilities import Connection
>>> with Connection(<server_name>) as conn:
>>>     conn.something(...)
```

Connection can also be initialized from appropriately formated string.
Strings are used mainly for underlying connection classes persistance to
disk

```python
>>> from ssh_utilities import Connection
>>> Connection.from_str(<string>)
```

All these return connection with preset reasonable parameters if more
customization is required, use open method, this also allows use of passwords

```python
>>> from ssh_utilities import Connection
>>> with Connection.open(<sshUsername>, <sshServer>, <sshKey>, <server_name>,
                         <logger>, <share_connection>):
```

Module API also exposes powerfull SSHPath object with identical API as
`pathlib.Path` only this one works for remote files

## API documentation

Can be found at readthedocs: https://ssh-utilities.readthedocs.io/en/latest/

## Contributing

1. Fork it
2. Create your feature branch: `git checkout -b my-new-feature`
3. Commit your changes: `git commit -am 'Add some feature'`
4. Push to the branch: `git push origin my-new-feature`
5. Submit a pull request

## License

MIT
