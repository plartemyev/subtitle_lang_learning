Learning languages by watching movies without translation.
======

This app was originally written as a helper tool to study English.
I think it is more productive to glance at the list of words used in the movie beforehand
and look at the translation of unfamiliar ones, instead of stopping in the middle to look up
some word. App provides a list of unique words with they ubiquity and the context in a phrase.
![app_screenshot]

LICENSE
-------
This is free software, distributed under the GPL v.3. If you want to discuss
a release under another license, please open an issue on GitHub

NOTES
-----
As usual with this kind of software :
This software is provided "AS-IS", without any guarantees. It should not do
any harm to your system, but if it does, the author, GitHub, etc... cannot
be held responsible. Use at your own risk. You have been warned.

Icons were taken from [KDE/breeze-icons](https://github.com/KDE/breeze-icons)

USAGE
-----
Simply enter movie name or some TV series identifier, like `mash s11e06`. Or you could select
a local file with subtitles in SRT format.
Words are arranged by they frequency. 

REQUIREMENTS
-------------
App requires **python>=3.5**, **PyQt5**, **PyQtWebEngine**, **chardet** and **srt**.

INSTALLATION
------------
### On Linux:
* Install Python 3.x and PIP via your distribution package manager.
* Clone or download this repository. 
* Try to install requirements also with package manager. And only if some
requirements are still missing - install them with PIP:  
**pip3 install --user -r subtitle_lang_learning/requirements.txt**

### On Windows:
* Install x86-64 Python 3.x: From [https://www.python.org/downloads/windows/]  
select "Download Windows x86-64 executable installer".  
When installing, check "Add Python to PATH";
* Download this program from this page by clicking on the "Clone or download" button
and selecting "Download ZIP". Then unpack the archive.
* Install requirements with PIP, E. G. Open a command prompt and execute:  
**pip3 install --user -r Downloads/subtitle_lang_learning-master/requirements.txt**
* Run the program by double-clicking on **sub_language_learning.py**

### On macOS 10.9 and later
* Download and install the latest **macOS 64-bit universal2 installer** from the official website
[https://www.python.org/downloads/macos/] 
* Check that you have Git installed [https://github.com/git-guides/install-git/] 
* Open the command prompt "terminal" and execute `git clone git@github.com:plartemyev/subtitle_lang_learning.git`
* Then execute `pip3 install --user -r subtitle_lang_learning/requirements.txt`
* And run the program by executing `python3 subtitle_lang_learning/sub_language_learning.py`


TODO
----
* [ ] Embed some local dictionary.
* [ ] Use nltk to retrieve original lemmas which would eliminate redundant words.
* [ ] Add ability to save already remembered words to exclude it from further searches.
* [ ] Embed video player, to be able to load video files with subtitles and jump to
the moment when a phrase is being spoken at the click on selected word.
* [ ] Localization.
* [ ] Package for Android.
* [ ] Package for Windows.
* [ ] Package for macOS.

CONTRIBUTING
------------
Here's how you can help : 
* You can clone the git repository and start hacking with the code. Pull requests are most welcome

[app_screenshot]: screenshot.jpg "Usage illustration"
