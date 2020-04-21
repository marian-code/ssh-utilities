# Paramiko wrapper
Simple paramiko wrapper that aims to facilitate easy remote file operations
and command execution. They API vaguely follows python os library. Has also
local variant that mimics the remote API on local machine. The connection is
resilient to interruptions. 

## Installation
1. `git clone git@gitlab.dep.fmph.uniba.sk:rynik/ssh-utils.git`
2. `cd ssh_utilities`
3. `pip install -e .`
Use -e only to install in editable mode

If you encounter some import errors try installing from requirements.txt file
`pip install requirements.txt`

## Usage
API exposes three main classes:
`from .ssh_utils import SSHConnection, Connection, LocalConnection`
`Connection` is the main class that initializes other two as needed according
to input parameters. It supports dict-like indexing by values that are in
your ~/.ssh/config file


## Contributing
1. Fork it
2. Create your feature branch: `git checkout -b my-new-feature`
3. Commit your changes: `git commit -am 'Add some feature'`
4. Push to the branch: `git push origin my-new-feature`
5. Submit a pull request

## License
MIT
