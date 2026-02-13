This script is for use under MSYS2/Cygwin on Windows.  It has been tested for over 8 hours under MSYS2 on Windows 11 without any issues and maintains all the features of
the Linux version of nrsc5-dui. To achieve this, I used Claude Code to remove any dependencies on tty since Windows does not have native, Unix-style TTY device files.

I'm assuming you already have a working knowledge of how to install and build NRSC5 and also how to install the python dependencies under MSYS2 for this script so I won't go thru that here.  Just 
install the dependencies via the MSYS2 pacman as you normally would.  For the final dependecy which is musicbranz, I got lazy when I couldn't find quick instructions to install it, so I went the 
pip route. Initially pip reported that I was under a managed environment so I just installed it like so:  pip install musicbrainzngs --break-system-packages

This worked perfectly for me but your mileage may vary.  Typically the dependencies are added via pacman like so:  pacman -S mingw-w64-x86_64-python-numpy


For those who wish to create a quick-launch CMD file for use under Windows, create a CMD file and add the following line:

C:\msys64\msys2_shell.cmd -defterm -no-start -mingw64 -here -c   /c/msys64/home/your_user_name_here/nrsc5-dui-msys2/nrsc5-dui-msys2.py

Insert your own user name where it says "your_user_name_here" and modify paths accordingly.  You can then double-click this CMD file or invoke it from the command line to launch the script.

