__version__ = "20220107.1"


def get_version():
    return __version__


def main():
    from atdel.atdel import AtDel

    AtDel()
