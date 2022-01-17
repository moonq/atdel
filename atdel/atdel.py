#!/usr/bin/env python3
from datetime import datetime, timedelta
import argparse
import os
import shutil
import sys
import tempfile
import time
import subprocess



class AtDel:
    def __init__(self):
        self.script = sys.argv[0]
        self.queue = "q"
        self.due = None
        self.spool_folder = "/var/spool/atjobs/"
        self.parse_opts()

        if self.options.delete:
            self.remove_file()
            return

        if self.options.remove:
            self.remove_job()
            return

        if self.due is not None:
            self.add_job()

        if self.due is None and not self.options.delete:
            self.list_jobs()

    def parse_opts(self):
        """Options parser"""
        parser = argparse.ArgumentParser(
            description="Automatically delete files after due date. Note: file must have same inode to be deleted",
            epilog="",
        )
        parser.add_argument(
            "--verbose",
            "-v",
            action="store_true",
            dest="verbose",
            default=False,
            help="Increase verbosity",
        )

        parser.add_argument(
            "-D",
            action="store",
            dest="remove",
            default=None,
            type=int,
            help="Remove deletion job ID",
        )
        parser.add_argument(
            "-d",
            action="store",
            type=float,
            help="Days to keep files.",
            default=None,
            dest="days",
        )
        parser.add_argument(
            "-t",
            action="store",
            type=str,
            help="Timespec when to delete, using date -d command. Example '02/01 15:00'",
            default=None,
            dest="time",
        )
        parser.add_argument(
            "--delete-file",
            action="store",
            dest="delete",
            default=None,
            type=str,
            help="Delete file with ID. Normally this is only called from at job.",
        )
        parser.add_argument(
            "--inode",
            action="store",
            dest="inode",
            default=None,
            type=int,
            help="Inode of file stored in jobspec. Normally this is only called from at job.",
        )
        parser.add_argument(
            "files",
            action="store",
            type=str,
            help="Files/folders to delete after N days",
            default=[],
            nargs="*",
        )
        self.options = parser.parse_args()
        if (self.options.days is None and self.options.time is None) and len(
            self.options.files
        ) > 0:
            parser.error("If files set, must give -d or -t")

        if self.options.days and self.options.time:
            parser.error("Only -t OR -d")

        if self.options.days:
            self.due = datetime.now().replace(microsecond=0) + timedelta(days=self.options.days)

        if self.options.time:
            self.due = datetime.fromtimestamp(
                    int(
                        subprocess.run(
                            ["date", "-d", self.options.time, "+%s"],
                            capture_output=True,
                        ).stdout
                    )
            )

        if self.options.delete:
            if self.options.inode is None:
                parser.error("--inode is required with --delete-file")

    def add_job(self):

        now = datetime.now().replace(microsecond=0)
        diff = self.due - now
        script = """
#ADDED {added}
#DELETE {due}
#INODE {inode}
#FILE {path}
{script} --inode {inode} --delete-file '{path_quoted}'
        """

        print("To be deleted in {} days, or on {}".format(diff.days, self.due))

        for f in self.options.files:
            path = os.path.abspath(f)
            inode = os.stat(f).st_ino

            commands = script.format(
                added=now.isoformat(),
                due=self.due.isoformat(),
                inode=inode,
                path=path,
                script=self.script,
                path_quoted=path.replace("'", "\\'"),
            )

            with tempfile.NamedTemporaryFile(delete=False) as fp:
                fp.write(commands.encode("utf-8"))
                fp.close()
                p = subprocess.run(
                    [
                        "at",
                        "-q",
                        self.queue,
                        "-f",
                        fp.name,
                        "-t",
                        self.due.strftime("%Y%m%d%H%M"),
                    ],
                    capture_output=True
                )
                for row in p.stderr.decode('utf-8').split("\n"):
                    if row.startswith("job "):
                        print(" ".join(row.split(" ")[0:2]))
                os.remove(fp.name)


    def list_jobs(self):

        p = subprocess.run(["atq", "-q", self.queue], capture_output=True)
        jobs = []
        for row in p.stdout.decode("utf-8").split("\n"):
            try:
                id = int(row.split("\t")[0],10)
                jobs.append(self.parse_job(id))
            except Exception as e:
                # ~ print(e)
                continue
        jobs.sort(key=lambda x: x['due'])
        if self.options.verbose:
            print("{:4s} {:14s} {:14s} {:4s} {}".format("ID", "Added", "Due", "Days", "File"))
            for job in jobs:
                job['added_str'] = job['added'].strftime("%y-%m-%d %H:%M")
                job['due_str'] = job['due'].strftime("%y-%m-%d %H:%M")
                print("{id:4d} {added_str} {due_str} {days:4.0f} {path}".format(
                    **job
                ))
        else:
            print("{:4s} {:4s} {}".format("ID", "Days", "File"))
            for job in jobs:
                print("{id:4d} {days:4.0f} {path}".format(
                    **job
                ))

    def parse_job(self, id):

        p = subprocess.run(["at", "-c", str(id)], capture_output=True)
        jobspec = {
            "id": id,
            "path": None,
            "added": None,
            "due": None,
            "inode": None,
            "days": None
        }

        for row in p.stdout.decode("utf-8").split("\n"):
            try:
                if row.startswith("#FILE "):
                    jobspec["path"] = row.strip()[6:]
                if row.startswith("#ADDED "):
                    jobspec["added"] = datetime.fromisoformat(row.strip()[7:27])
                if row.startswith("#DELETE "):
                    jobspec["due"] = datetime.fromisoformat(row.strip()[8:28])
                    jobspec["days"] = round((jobspec["due"] - datetime.now()).total_seconds()/86400,2)
                if row.startswith("#INODE "):
                    jobspec["inode"] = int(row.strip()[7:])

            except Exception as e:
                # ~ print("Error parsing ID: {} - {}".format(id, str(e)))
                raise e

        return jobspec

    def remove_file(self):
        """Delete files where due date has passed"""

        inode = self.options.inode
        path = self.options.delete

        try:
            if not os.path.exists(path):
                print("File {} doesnt exist.".format(path),
                        file=sys.stderr
                )
            else:
                curr_inode = os.stat(path).st_ino
                if curr_inode != inode:
                    print(
                        "Path has different inode, possible security issue: {}".format(
                            path
                        ),
                        file=sys.stderr,
                    )
                    return
                if os.path.isdir(path):
                    print("Deleting folder {}".format(path))
                    shutil.rmtree(path)
                else:
                    print("Deleting file {}".format(path))
                    os.remove(path)
        except Exception as e:
            print(e, file=sys.stderr)

    def remove_job(self):

        p = subprocess.run(
            ["atrm", str(self.options.remove)],
        )


if __name__ == "__main__":
    atdel = AtDel()
