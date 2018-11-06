# DrySync
DrySync copies source files/directories into a destination, asking the user for confirmation before actually doing it.

DrySync tries to solve two problems that come up when doing a classic rsync (or other file sync tools):
* With rsync it's never clear if you are copying the top directory, so you always have to make sure the destination has the right structure (and some times copy the tree again), which usually ends up in doing trying more than once.
* Automatic sync (scheduled to be done in the background) is not a good idea for copying delicate files, such as binaries/scripts that you run often, or ssh keys and the like... which is relevant if you use OwnCloud, Dropbox or other cloud sync tools for such things.

This tool solves these problems by spliting the copy process in two: 
1. it first generates a list of actions to be done to make source and destination to be in sync, 
2. and then asks the user for confirmation to execute these actions.

DrySync comes in two flavors: one CLI to use from the command line (much like rsync with a confirmation step) and an "App" that has a graphical interface, with config files, for scheduling automatic sync of directories for regular use. With the App you can have your binaries, config files and keys in your home cloud storage and have DrySync keep the actual (e.g. ~/bin/ or ~/.ssh/) directories in sync with the cloud storage so, when a change arrives from outside, you always get a confirmation screen before putting the files in their final location.

Everything is written in python and kept in single-file fashion for maximal portability.

## drysync

This is the command-line tool, but it also includes the basic classes for the App. It does not require installattion and can be run like this:
```./drysync sourcedir/ destinationdir/```
This will copy the contents of sourcedir into destinationdir, asking for confirmation before doing it. In the confirmation screen you will see an ordered list of actions to be performed, where you can explore the details of the sync operation. For those files that already exist in the destination but are different, the tool can show you a diff between the two if you tell it to (by typing the number of the action).

You can type ```./drysync -h``` for the full instructions. This CLI usage does not use any config files. It works with python 2 and 3 and does not need any special packages.

## drysyncapp

This is the graphical interface for DrySync. It requires the drysync file to be in the same directory, because it contains the base classes for the sync operations.

DrySyncApp works only with python 2.7, and kivy >= 1.09 is also needed as a dependency (```apt-get install python-kivy```) for all the GUI widgets.

If you invoke ```./drysyncapp``` without parameters, it will open a configuration screen where you can define any number of sync tasks, enable/disable them, simulate a sync (drysync) and do the actual execution. 

If you invoke the tool with the auto parameter, with ```./drysyncapp auto```, the tool will try to perform a sync operation of all the tasks that are defined and enabled, and only launch the GUI interface if there are things to do, to ask for confirmation. This is well suited for running the tool in this mode from a task scheduler (such as cron).

There are many ways to schedule these tasks. If you want to use cron (in any linux flavors) you can run:
```crontab -e``` as your own user and then add the line:
```0 8,16 * * * /home/<myself>/bin/drysyncapp auto >> /tmp/drysync-cron.log```
This will make the app run twice per day, at 8 and 16 hours. You can verify it's active by running ```crontab -l``` or looking at the logs in ```/tmp/drysync-cron.log```

The App uses a config directory in ```~/.drysync``` to store the list of tasks and PID files.

## Development

DrySync is under development and has a number of interesting things in the "TODO" list:
* Support for --delete parameter, to make the tool remove those files in the destination directory that are not in the source.
* Add pagination in the GUI, as it currently shows only 100 actions. All the other actions are now shown because Kivy is very inefficient when handling large number of widgets. Using the RecyclerView is not desirable, because Kivy 1.11 is not present in most linux distributions (complex installations are against the filosophy of this app).
* Add a progress bar in the GUI for long tasks
* Support linux hard links
* Windows and Mac support. Kivy potentially support iOS and Android, but I wonder if that's ever a use case for this app.
* Automated testing to avoid breaking the code with new features
* More beautiful GUI (while still fitting in a single file)
* Step-by-step sync
* Support for multiple goals (beyond the default one)

If you are willing to contribute on any of the above features (or new features) please drop me a line before doing a lot of work on your own.

Hope you enjoy the app!
