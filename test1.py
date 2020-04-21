from ssh_utils import SSHConnection

c = SSHConnection.open("rynik", "158.195.19.229",
                       "~/.ssh/id_rsa_hartree", "schrodinger")

c.openSftp()
print(c.listdir("/home/rynik/Raid/dizertacka/tmp_folder_300_test"))

out = c.sendCommand("ls -l /home/rynik && ls -l /home/rynik", suppres_out=False,
                    make_error=True)