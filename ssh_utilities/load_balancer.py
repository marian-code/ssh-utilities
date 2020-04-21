import os
import sys


class AbstractPbsRun:

    def __init__(self, da, remote_clusters, settings, lammpses, connections,
                 log, qstat_command="/opt/pbs/bin/qstat",
                 qsub_command="/opt/pbs/bin/qsub"):
        self.qstat_command = qstat_command
        self.qsub_command = qsub_command
        self.log = log
        if isinstance(remote_clusters, str):
            remote_clusters = [remote_clusters]
        self.remote_clusters = remote_clusters
        self.set = settings
        self.local = None  # pos of the local cluster in PBSes list
        self.c = connections  # ssh connections
        self.lammpses = lammpses

        # pbs objects
        N = self.__set_number_of_jobs__(start=True)
        self.PBSes = self.__setup__(da, N)

        self.try_close = False

        # runs in infinite loop and checks for changes to settings
        job_runner = InfiniteTimer(target=self.__set_number_of_jobs__,
                                   seconds=15)
        job_runner.daemon = True
        job_runner.start()

    def __setup__(self, da, N):
        """ initialize pbs interface computation classes """

        job_pref = f'{self.set["job_prefix"]}'

        if len(job_pref) > 10:
            inpt = input("\nJob prefix is longer than 10 chars, "
                         "continue? (y/n[default]): ").casefold()

            if inpt == "n" or inpt == "no":
                sys.exit()

        p = dict()
        for server, lammps in self.lammpses.items():

            if self.set[server]["address"] is False:
                self.local = server

            tmp_folder = os.path.join(self.set[server]["tmp_folder"],
                                      f"tmp_folder_{self.set['job_prefix']}")

            # remove temp dirs from previous calculations
            # should not run when restarting
            """
            self.c[server].rmtree(tmp_folder, ignore_errors=True)
            """

            p[server] = (
                PBSQueueRun_alt(
                    da, tmp_folder=tmp_folder, job_prefix=job_pref,
                    n_simul=N[server],
                    job_template_generator=lammps.job_template_generator,
                    calculator=lammps, connection=self.c[server], log=self.log,
                    qsub_command=self.qsub_command,
                    qstat_command=self.qstat_command
                                )
                    )

            self.log.info(f"Set PBS interface class for: {server}")

        return p

    def enough_jobs_running(self):

        enough = []
        for server, PBS in self.PBSes.items():
            if self.c[server] is not None:
                enough.append(PBS.enough_jobs_running(server))

        if False in set(enough):
            return False
        else:
            return True

    def number_of_jobs_running(self):

        jobs = 0
        for server, PBS in self.PBSes.items():
            if self.c[server] is not None:
                jobs += PBS.number_of_jobs_running(server)

        return jobs

    def __set_number_of_jobs__(self, start=False):

        # relies on hard limit set in settings file for each machine
        if self.set["remote_resources"] == "hard":
            N = read_settings(only_n_simul=True,
                              remote_clusters=self.remote_clusters)
            self.log.debug(f"free: {N}")

        # use all cores on all machines - pools qstat for free resources
        elif self.set["remote_resources"] == "adaptive":
            N = self.__get_remote_free_jobs__()
            if N is None:
                return 1

        # relies on hard limit set in settings file common for all machines
        elif self.set["remote_resources"] == "common":
            _set = read_settings(only_n_simul=True)
            N = dict()
            for r in self.remote_clusters:
                N[r] = _set

        else:
            raise NotImplementedError("Unknown resources management setting")

        if start is False:
            self.__change_jobs__(N)
            self.free = N

            # finally set number of jobs
            for server, PBS in self.PBSes.items():
                PBS.set_number_of_jobs(N[server])
        else:
            self.free = N
            return N

    def __get_remote_free_jobs__(self):

        while True:
            ind = randint(0, len(self.PBSes) - 1)
            if (ind != self.local and self.c[ind] is not None):
                break

        # TODO doesn't work if no jobs are in PBS
        out = self.c[ind].sendCommand(f"{self.qstat_command} -f", True,
                                      quiet=True)
        try:
            lines = qstat_repair(out.splitlines())
        except AttributeError:
            free = None
        else:
            # int server load dict
            free = dict()
            for r in self.remote_clusters:
                free[r] = self.set[r]["available_cpus"]

            # TODO check this doesnt always have to be fifth line
            for l in lines[5:]:
                cpus, status, server = itemgetter(6, 9, 11)(l.split())

                server = server.split("/")[0].casefold().capitalize()

                if status.casefold() == "q":
                    continue

                try:
                    free[server] = free[server] - int(cpus)
                except KeyError:
                    self.log.warning(f"No server {server} in settings file")

            # accout for jobs running locally with multiprocessing
            jobs = self.PBSes[self.local].number_of_jobs_running()
            free[self.local] -= jobs

        finally:
            return free

    def __change_jobs__(self, N):

        for r in self.remote_clusters:

            # check if number of jobs have changed
            if self.free[r] != N[r]:
                print(f"{G}Number of jobs on{R} {r.upper()} {G}"
                      f"changed from{R} {self.free[r]} {G}to{R} {N[r]}")
                self.log.info(f"Number of jobs on {r.upper()} changed "
                              f"from {self.free[r]} to {N[r]}")

            # open new connection if change is from 0 -> n
            if self.free[r] == 0 and N[r] >= 1:
                self.c.open(r)
                self.lammpses[r].start_remote(self.c[r])
                self.PBSes[r].start_remote(self.c[r])

            # set switch to close existing connection if change is from n -> 0
            elif self.free[r] >= 1 and N[r] == 0:
                self.try_close = r

        # attempt to close connection if no files are present in remote tmp dir
        if self.try_close is not False:
            tc = self.try_close
            print(f"{G}Trying to close connection to:{R} {tc}")
            self.log.info(f"Trying to close connection to: {tc}")

            jobs_left = self.PBSes[tc].number_of_jobs_running(tc)

            if jobs_left == 0:
                self.lammpses[r].end_remote()
                self.PBSes[r].end_remote()
                self.c.close(tc)
                self.try_close = False
            else:
                self.log.info(f"Couldn't close connection. {jobs_left} job(s)"
                              f"still running")

    def relax(self, a):

        for server, PBS in self.PBSes.items():
            if self.c[server] is not None:
                if not PBS.enough_jobs_running(server):
                    PBS.relax(a)
                    break

    def remote_cleanup(self):

        for connection, PBS in zip(self.c, self.PBSes.values()):
            if connection is not None:
                connection.rmtree(PBS.tmp_folder)


class ConnectionManager:

    def __init__(self, host, remote_clusters, settings, log):

        self.log = log

        self.connections = dict()
        for r in remote_clusters:
            if settings[r]["n_simul"] > 0:
                self.connections[r] = self.__get_connection__(r, settings)
            elif settings[r]["n_simul"] == 0:
                self.connections[r] = None
            else:
                raise ValueError(f"n_simul setting for {r} is not =< 0")

    def __get_connection__(self, server, settings):

        sshServer = settings[server]["address"]
        sshUsername = settings["login_name"]
        sshKey = settings[server]["key_file"]

        if sshUsername is None or sshServer is None or sshKey is None:
            self.log.exception("ssh credentials not specified!")
            raise AssertionError("ssh credentials not specified!")

        connection = Connection.open(sshUsername, sshServer, sshKey=sshKey,
                                     server_name=server, logger=self.log)
        connection.openSftp(quiet=True)
        connection.ssh_log(f"logs/paramiko_{server}.log")

        return connection

    def __getitem__(self, key):
        return self.connections[key]

    def __iter__(self):
        return iter(self.connections.values())

    def open(self, server):
        settings = read_settings()
        self.connections[server] = self.__get_connection__(server, settings)

    def close(self, server):

        self.connections[server].close()
        self.connections[server] = None
        self.log.info(f"Close connection to {server} successful")
