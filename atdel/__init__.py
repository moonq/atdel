__version__ = "20220109.1"


def get_version():
    return __version__


def main():
    from atdel.atdel import AtDel

    AtDel()
