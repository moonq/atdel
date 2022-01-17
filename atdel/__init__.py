__version__ = "2022.0"


def get_version():
    return __version__


def main():
    from atdel.atdel import AtDel

    AtDel()
