# zundernet
Python3 wallet gui for Pirate Chain

Before you start - backup your wallet.dat file just in case.

Zundernet is new proof of concept wallet, with features not available in other wallets.
It is new experimental software.

It should work on Windows and Linux as long as user has python3 installed with following libraries: tk, ttk, psutil, pycryptodome and some other standard libraries.

Some linux distributions may be missing so for example you may need to run:

sudo apt-get install python3-tk 

sudo apt-get install python3-psutil

sudo apt-get install python3-pip

sudo pip3 install pycryptodome

To use the app you also need Komodo deamon and zcash params.

Zcash params for Windows and Linux may be downloaded using attached scripts (komodo-win, komodo-lin) containing also komodo deamons.

When all above conditions are met you should run:

1. Windows, cmd:
python zundernet.py

2. Linux, terminal:
python3 zundernet.py

Then you point the app to komodo-cli and wallet file to be able to use it.
