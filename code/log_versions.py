"""Record the software versions of the environment that ran the experiments.
Run on the compute host: python -I code/log_versions.py > facts/software_versions.json"""
import json
import platform
import sys

import numba
import numpy
import pandas
import scipy

info = {"python": platform.python_version(), "numpy": numpy.__version__, "numba": numba.__version__,
        "pandas": pandas.__version__, "scipy": scipy.__version__, "platform": platform.platform(),
        "executable": sys.executable}
try:
    info["os_release"] = dict(l.rstrip().split("=", 1) for l in open("/etc/os-release") if "=" in l)["PRETTY_NAME"].strip('"')
except OSError:
    pass
print(json.dumps(info, indent=1))
