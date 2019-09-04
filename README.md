Learning languages by watching movies without translation.
======

This app is originally written to help my girlfriend study English.
I think it is more productive to glance at the list of words used in the movie beforehand
and look at the translation of unfamiliar ones, instead of stopping in the middle to lookup
some word. App provides a list of unique words with they ubiquity and the context in a phrase.
![app_screenshot]

LICENSE
-------
This is free software, distributed under the GPL v.3. If you want to discuss
a release under another license, please open an issue on Github

NOTES
-----
As usual with this kind of software :
This software is provided "AS-IS", without any guarantees. It should not do
any harm to your system, but if it does, the author, github, etc... cannot
be held responsible. Use at your own risk. You have been warned.

Icons were taken from [KDE/breeze-icons](https://github.com/KDE/breeze-icons)

USAGE
-----
Simply enter movie name or some TV series identifier, like `mash s11e06`. Or you could select
a local file with subtitles in SRT format.
Words are arranged by they frequency. 

REQUIREMENTS
-------------
App requires **python>=3.5**, **PyQt5** and **srt**.

TODO
----
* [ ] Embed some local dictionary.
* [ ] Use nltk to retrieve original lemmas which would eliminate redundant words.
* [ ] Add ability to save already remembered words to exclude it from further searches.
* [ ] Embed video player, to be able to load video files with subtitles and jump to
the moment when a phrase is being spoken at the click on selected word.
* [ ] Localization.
* [ ] Package for Android.

CONTRIBUTING
------------
Here's how you can help : 
* You can clone the git repository and start hacking with the code. Pull requests are most welcome

[app_screenshot]: screenshot.jpg "Usage illustration"
