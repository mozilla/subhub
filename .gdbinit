# Persistent history:
set history save
set history filename ~/.gdb_history

set auto-load python-scripts on
show auto-load python-scripts on
info auto-load python-scripts

# Pretty Print Output
set print pretty

# Print the full stack trace when it crashes:
set python print-stack full

# Colored prompt:
set prompt \001\033[1;32m\002(gdb)\001\033[0m\002\040

# When displaying a pointer to an object, identify the actual (derived) type of the object rather than the declared type, using the virtual function table.
set print object on

# Print using only seven-bit characters
set print sevenbit-strings off

# Convert GDB to interpret in Python
python
import sys
import os
import subprocess
# Execute a Python using the user's shell and pull out the sys.path
#  from that version
sys.path.insert(0, join(dirname(realpath(__file__)), 'src'))
paths = eval(subprocess.check_output('python -c "import sys;print(sys.path)"',
                                     shell=True).strip())
print(paths)
# Extend the current GDB instance's Python paths
sys.path.extend(paths)
end

# References
#   1. https://chezsoi.org/lucas/blog/gdb-python-macros.html
#   2. https://interrupt.memfault.com/blog/using-pypi-packages-with-GDB
#   3. https://ftp.gnu.org/old-gnu/Manuals/gdb/html_node/gdb_57.html
