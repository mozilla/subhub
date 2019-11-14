# Debugging

This document describes the process to run either the sub or hub components under
the GNU project debugger (GDB).

## GDB

1. Start the application via the run-local script, `./bin/run-local.sh "${APPLICATION}"`
2. In another terminal, start the attach-gdb script, `sudo ./bin/attach-gdb.sh "${APPLICATION}"`
3. Set some break points (reference 2) and debug.

Where the APPLICATION variable is a member of the set:
* `src/sub/app.py`
* `src/hub/app.py`

### Verifying Python Version with GDB

```
gdb -ex r -ex quit --args python3 -c "import sys ; print(sys.version)"
...
3.7.5 (default, Oct 15 2019, 21:38:37)
[GCC 5.4.0 20160609]
```

## References
1. [Exploring Python Using GDB](https://stripe.com/blog/exploring-python-using-gdb)
2. [GDB Cheat Sheet](https://gist.github.com/rkubik/b96c23bd8ed58333de37f2b8cd052c30)
