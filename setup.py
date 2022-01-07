from distutils.core import setup

setup(
    name="atdel",
    packages=["atdel"],
    include_package_data=True,
    classifiers=[],
    entry_points={
        "console_scripts": [
            "atdel=atdel:main",
        ],
    },
)
