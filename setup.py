from distutils.core import setup
import os, sys, glob, py2exe

# Find GTK+ installation path
__import__('gtk')
m = sys.modules['gtk']
gtk_base_path = m.__path__[0]

def get_files_recursive(directory):
    paths = []
    for (path, directories, filenames) in os.walk(directory):
        for filename in filenames:
            paths.append(os.path.join('..', path, filename))
    return paths

gtk_package_files = []
gtk_package_files.append([os.path.join('share','themes'), get_files_recursive(os.path.join(gtk_base_path,'..','runtime','share','themes'))])
gtk_package_files.append([os.path.join('lib','gtk-2.0','2.10.0'), get_files_recursive(os.path.join(gtk_base_path,'..','runtime','lib','gtk-2.0','2.10.0'))])
gtk_package_files.append([os.path.join('lib','gtk-2.0','modules'), get_files_recursive(os.path.join(gtk_base_path,'..','runtime','lib','gtk-2.0','modules'))])
# TODO: make script copy empty dirs so this works
gtk_package_files.append([os.path.join('share','icons'), get_files_recursive(os.path.join(gtk_base_path,'..','runtime','share','icons'))])

setup(
    name = 'nrsc5-gui',
    description = 'Graphical frontend for nrsc5 cli utility',
    version = '1.0',

    windows = [
                  {
                      'script': 'nrsc5-gui.py',
                      'icon_resources': [(1, os.path.join("res","nrsc5-gui.ico"))],
                  }
              ],

    options = {
                  'py2exe': {
                      'packages':'encodings',
                      'includes': 'gtk, gtk.cairo, gio, pango, pangocairo, atk, gobject, datetime, numpy',
                      'dll_excludes': [
                          'CRYPT32.DLL',  # required by ssl
                          'DNSAPI.DLL',
                          'IPHLPAPI.DLL',  # psutil
                          'MPR.dll',
                          'MSIMG32.DLL',
                          'MSWSOCK.dll',
                          'NSI.dll',  # psutil
                          'PSAPI.DLL',
                          'POWRPROF.dll',
                          'USP10.DLL',
                          'WTSAPI32.DLL',  # psutil
                          'api-ms-win-core-apiquery-l1-1-0.dll',
                          'api-ms-win-core-crt-l1-1-0.dll',
                          'api-ms-win-core-crt-l2-1-0.dll',
                          'api-ms-win-core-debug-l1-1-1.dll',
                          'api-ms-win-core-delayload-l1-1-1.dll',
                          'api-ms-win-core-errorhandling-l1-1-1.dll',
                          'api-ms-win-core-file-l1-2-1.dll',
                          'api-ms-win-core-handle-l1-1-0.dll',
                          'api-ms-win-core-heap-l1-2-0.dll',
                          'api-ms-win-core-heap-obsolete-l1-1-0.dll',
                          'api-ms-win-core-io-l1-1-1.dll',
                          'api-ms-win-core-libraryloader-l1-2-0.dll',
                          'api-ms-win-core-localization-l1-2-1.dll',
                          'api-ms-win-core-memory-l1-1-2.dll',
                          'api-ms-win-core-processenvironment-l1-2-0.dll',
                          'api-ms-win-core-processthreads-l1-1-2.dll',
                          'api-ms-win-core-profile-l1-1-0.dll',
                          'api-ms-win-core-registry-l1-1-0.dll',
                          'api-ms-win-core-string-l1-1-0.dll',
                          'api-ms-win-core-string-obsolete-l1-1-0.dll',
                          'api-ms-win-core-synch-l1-2-0.dll',
                          'api-ms-win-core-sysinfo-l1-2-1.dll',
                          'api-ms-win-core-threadpool-l1-2-0.dll',
                          'api-ms-win-core-timezone-l1-1-0.dll',
                          'api-ms-win-core-util-l1-1-0.dll',
                          'api-ms-win-security-base-l1-2-0.dll',
                          'w9xpopen.exe',  # not needed after Windows 9x
                      ],
                      'compressed': True  # create a compressed zipfile
                  },
              },

    data_files=[
        'README.md',
        "aas"+os.path.sep+"placeholder.txt",
        "map"+os.path.sep+"placeholder.txt",
        ("bin", glob.glob("bin/*")),
        ("res", glob.glob("res/*")),
        ("cfg", glob.glob("cfg/*")),
        gtk_package_files[0],
        gtk_package_files[1],
        gtk_package_files[2],
        gtk_package_files[3],
    ]
)