#!/usr/bin/env python3
from datetime import datetime, timedelta
import argparse
import os
import shutil
import sqlite3
import sys


class AtDel:
    def __init__(self):
        self.config_file = os.path.expanduser("~/.cache/atdel")
        self.parse_opts()
        self.db_init()

        if self.options.days is not None:
            self.set_file_status()

        if self.options.days is None and not self.options.delete:
            self.db_list()

        if self.options.delete:
            self.del_due_files()

    def db_init(self):

        with sqlite3.connect(self.config_file) as con:
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS atdel (
                    id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    inode INTEGER NOT NULL,
                    added TEXT NOT NULL,
                    due TEXT NOT NULL
                );
            """
            )
            con.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS idx_name ON atdel (name);
            """
            )

    def parse_opts(self):
        """Options parser"""
        parser = argparse.ArgumentParser(
            description="Automatically delete files after due date. Note: file must have same inode to be deleted",
            epilog="Automate deletion by adding cron '0 0 * * * atdel --delete'",
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
            "--delete",
            action="store_true",
            dest="delete",
            default=False,
            help="Delete all due files",
        )
        parser.add_argument(
            "-d",
            action="store",
            type=int,
            help="Days to keep files. 0 to remove deletion tag",
            default=None,
            dest="days",
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
        if self.options.days is None and len(self.options.files) > 0:
            parser.error("If files set, must give -d for retain length")

    def set_file_status(self):

        to_remove = self.options.days == 0
        now = datetime.now()
        del_delta = timedelta(days=self.options.days)
        del_time = (now + del_delta).isoformat()
        now_time = now.isoformat()

        with sqlite3.connect(self.config_file) as con:
            for f in self.options.files:
                path = os.path.abspath(f)
                inode = os.stat(f).st_ino

                if to_remove:
                    rows = con.execute("SELECT name FROM atdel WHERE name = ?", (path,))
                    if len(rows.fetchall()) == 0:
                        print("No such file in database: '{}'".format(path))
                    else:
                        con.execute(
                            "DELETE FROM atdel WHERE name = ?;",
                            (path,),
                        )
                        print("Removed: {}".format(path))
                else:
                    con.execute(
                        "INSERT OR REPLACE INTO atdel (name, due, added, inode) values(?, ?, ?, ?);",
                        (path, del_time, now_time, inode),
                    )
                    print(f)
        if not to_remove:
            print(
                "To be deleted in {} days, or on {}".format(self.options.days, del_time)
            )

    def db_list(self):

        data = []
        with sqlite3.connect(self.config_file) as con:
            rows = con.execute("SELECT added, due, name FROM atdel ORDER BY added;")
            for row in rows:
                due = (datetime.fromisoformat(row[1]) - datetime.now()).days
                rel = os.path.relpath(row[2])
                if rel.startswith(".."):
                    rel = row[2]
                data.append([row[0][0:10], row[1][0:10], due, rel])
        print("{:10s} {:10s} {:4s} {}".format("Added", "Due", "Days", "File"))
        for row in data:
            print("{:10s} {:10s} {:4d} {}".format(*row))

    def del_due_files(self):
        """Delete files where due date has passed"""

        paths = []
        with sqlite3.connect(self.config_file) as con:
            rows = con.execute(
                "SELECT added, due, name, inode FROM atdel ORDER BY added;"
            )
            for row in rows:
                due = (datetime.fromisoformat(row[1]) - datetime.now()).days
                exists = os.path.exists(row[2])
                if due < 0 or not exists:
                    paths.append([row[2], row[3]])

        for (p, inode) in paths:
            try:
                if not os.path.exists(p):
                    print("File {} doesnt exist, removing from DB".format(p))
                else:
                    curr_inode = os.stat(p).st_ino
                    if curr_inode != inode:
                        print(
                            "Path has different inode, possible security issue: {}".format(
                                p
                            ),
                            file=sys.stderr,
                        )
                        continue
                    if os.path.isdir(p):
                        print("Deleting folder {}".format(p))
                        shutil.rmtree(p)
                    else:
                        print("Deleting file {}".format(p))
                        os.remove(p)

                # ~ self.db_remove(p)
            except Exception as e:
                print(e, file=sys.stderr)

    def db_remove(self, path):
        with sqlite3.connect(self.config_file) as con:
            con.execute(
                """
                DELETE FROM atdel WHERE name = ?;
                """,
                (path,),
            )


if __name__ == "__main__":
    atdel = AtDel()
