#!/usr/bin/env python
# -*- coding: utf-8 -*-

#    DrySync copies source files/directories into a destination, asking the 
#      user for confirmation before actually doing it. 
#    Copyright (C) 2018 - Pablo Fernandez - naevtamarkus@gmail.com
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
# You can find instructions here: https://github.com/naevtamarkus/drysync
# 

import os, sys
import shutil  # for copy2
import difflib
import filecmp

# This program consists of three main classes: DryRun(), Task() and Action()
# It can be used directly (has a main function) or imported (e.g. from the GUI)

class Task:
  # Task() definition of the source and target files/directories, and generates the list of Action()
  #  (CLI only has one, GUI can have many)
  def __init__(self, *initial_data, **kwargs):
    # set default attributes
    self.description= ''
    self.inputPaths=[]   # List of strings with input files/directories (e.g. [u'/dir', u'/file2'])
    self.recursive=True  # True = Recursive sync (include subdirectories)
    self.skipTopDir=True # True = Do not sync top directories, just its contents (/dir --> /dir/*)
    self.outputPath=''   # String with output Path (e.g. "/tmp")
    self.errorGenerateActions=None   # String with the error when trying to generate the actions
    # And then overwrite them with the given params
    for dictionary in initial_data:
      for key in dictionary:
        setattr(self, key, dictionary[key])
    for key in kwargs:
      setattr(self, key, kwargs[key])

  def generateActions(self):
    # Returns a list of Action() with all the actions to perform to have this Task done
    actions = []
    self.errorGenerateActions=None
    # Convert ~/ into /home/x/
    outFullPath = os.path.expanduser(self.outputPath)
    try:
      for inputPath in self.inputPaths:
        inFullPath = os.path.expanduser(inputPath)
        if os.path.isfile(inFullPath) or os.path.islink(inFullPath):
          actions.extend(self.__copyFile(inFullPath, outFullPath) )
        if os.path.isdir(inFullPath):
          actions.extend(self.__copyDirectory(inFullPath, outFullPath, includeTop=(not self.skipTopDir), recursive=self.recursive))
    except Exception as e: 
      self.errorGenerateActions = e
    return actions

  def __diffAndCopy(self, src, dst, actions):
    # Expands a list of actions with a simple copy of a file if they are different
    # Add necesary actions to copy file if needed (may be no action at all)
    # Exceptions should be catched in the caller of this function
    isNew = not os.path.lexists(dst)
    if os.path.islink(src) and (isNew or not os.path.islink(dst) or os.readlink(src) != os.readlink(dst)):
      # It's a symlink, make sure dst points to the same place as src
      actions.append(Action(command='ln', source=dst, target=os.readlink(src), isNew=isNew))

    elif os.path.isfile(src) and (isNew or not filecmp.cmp(src, dst)):
      actions.append(Action(command='cp', source=src, target=dst, isNew=isNew))
    # TODO we could check also permissions are the same and do only an Action(chmod) if not

  def __copyFile(self, src, dst):
    # Generates an action for a simple copy of a file
    # Returns a list of Actions
    # src is a file and dst is a directory
    # Exceptions should be catched in the caller of this function
    # If the destination dir does not exist, create it
    #print "__copyFile (%s, %s)" % (src, dst)
    actions = []  # local var
    name = os.path.basename(src)
    if not os.path.isdir(dst): 
      actions.append(Action(command='mkdir', source=src, target=dst, isNew=True))
    dstname = os.path.join(dst, name)
    self.__diffAndCopy(src, dstname, actions)
    return actions

  def __copyDirectory(self, src, dst, includeTop=False, recursive=True):
    # Walks through directories generating actions
    # Returns a list of Actions
    # src and dst must be directories (absolute paths)
    # Exceptions should be catched in the caller of this function
    #print "__copyDirectory (%s, %s)" % (src, dst)
    if os.path.islink(src):
      a=1/0 # we should never get in here, links are treated as files not directories TODO replace with an actual exception
    allFiles = os.listdir(src)
    dirName = os.path.basename(src)
    actions = []
    # first mkdir target dir if does not exist
    if not os.path.isdir(dst): 
      actions.append(Action(command='mkdir', source=src, target=dst, isNew=True))
    # Ascend an extra level on target dir (only the first recursive call, includeTop should be false afterwards)
    if includeTop:
      dst = os.path.join(dst, dirName)
      if not os.path.isdir(dst): 
        actions.append(Action(command='mkdir', source=src, target=dst, isNew=True))
    # At this point, we can go file by file   
    for name in allFiles:
      srcname = os.path.join(src, name)
      dstname = os.path.join(dst, name)
      # If it's a link, treat it like a file
      if os.path.isdir(srcname) and not os.path.islink(srcname):
        # It's a directory, recurse if we're asked to
        if recursive:
          # TODO we may want to this at the end of the loop, to avoid coming up and down 
          actions.extend(self.__copyDirectory(srcname, dstname))
      else: 
        # It's a file, diff and copy if necessary
        self.__diffAndCopy(srcname, dstname, actions)
    return actions


# Action() defines each individual sync action to make progress on a Task (e.g. file A copies to B)
class Action:
  def __init__(self, *initial_data, **kwargs):
    # set default attributes
    self.command = ''     # Can be one of [cp,ln,mkdir]
    self.target = ''      # String with the target of the action
    self.source = ''      # String with the source of the action
    self.isNew = False    # True = the target does not exist
    self.errorMsg = None  # None = success, otherwise String with error message
    self.hasExecuted = False   
    # And then overwrite them with the given params
    for dictionary in initial_data:
      for key in dictionary:
        setattr(self, key, dictionary[key])
    for key in kwargs:
      setattr(self, key, kwargs[key])

  def showDetail(self):
    # Explains the actual action. If src and dst exist and are files, shows a diff
    # Returns a String with all details
    text = self.toString() + '\n'
    if self.isNew:
      text += 'Target does not yet exist, it shall be created'
    elif self.command == 'ln':
      # May be different targets or file types, just show that
      try:
        if os.path.islink(self.source):
          text += "Source link points to: %s \nTarget link points to: %s" % (self.target, self.source)
        else:
          text += "Source link points to: %s \nTarget is a real file, not a link" % (self.target)
      except Exception as e: 
        text += 'ERROR in showDetail\n%s' % e
    elif self.command == 'cp':
      # They are files
      # Check if files are binary
      textchars = bytearray({7,8,9,10,12,13,27} | set(range(0x20, 0x100)) - {0x7f})
      is_binary_string = lambda bytes: bool(bytes.translate(None, textchars))
      isBinSource = is_binary_string(open(self.source, 'rb').read(4096))
      isBinTarget = is_binary_string(open(self.target, 'rb').read(4096))
      try:
        sizeSource = os.path.getsize(self.source)
        sizeTarget = os.path.getsize(self.target)
        text += 'Source file: %s\n' % self.source
        text += 'Size: %s bytes\n' % sizeSource
        text += 'Binary: %s\n---\n' % isBinSource
        text += 'Target file: %s\n' % self.target
        text += 'Size: %s bytes\n' % sizeTarget
        text += 'Binary: %s\n---\n' % isBinTarget
        if isBinSource or isBinTarget:
          text += 'Not comparing binary files'
        elif sizeSource > 40000 or sizeTarget > 40000:
          text += 'Not comparing files over 40 KB' 
        else:
          f1=open(self.source,'r')  #open a file
          f2=open(self.target,'r') #open another file to compare
          str1=f1.readlines()
          str2=f2.readlines()
          diff = difflib.unified_diff(str1, str2, fromfile=self.source, tofile=self.target, n=0 )
          text += '\n'.join(diff)
      except Exception as e: 
        text += 'ERROR in showDetail\n%s' % e
    else:
      text += "Nothing else to highlight"
    if self.hasExecuted:
      if self.errorMsg == None:
        text += '\nThis operation has already been executed successfully'
      else:
        text += '\nThis operation has been executed with errors:\n%s' % self.errorMsg
    return text

  def toString(self):
    # Returns a one-line string with the action to do (only for brief info)
    if self.command == 'cp':
      return "cp -a %s %s" % (action.source, action.target)
    if self.command == 'mkdir':
      return "mkdir %s" % (action.target)
    if self.command == 'ln':
      return "ln -sf %s %s" % (action.source, action.target)

  def getExecutionLog(self):
    # Returns a one-line string with the execution log, plus extra lines if there were errors
    if self.hasExecuted:
      if self.errorMsg == None:
        return '[OK] %s' % action.toString()
      if action.errorMsg != None:
        return '[ERROR] %s\n%s' % (action.toString(), action.errorMsg)
    else:
      return '[PENDING] %s' % action.toString()



# DryRun() is the top class, which contains one or more Task(), one single list of Action()
#  and does the actual execution
class DryRun:
  def __init__(self, *initial_data, **kwargs):
    # set default attributes
    self.tasks = []     # List of Task() 
    self.actions = []   # List of Action()
    self.errorGenerateActions = None  # String wit the error while generating actions
    self.summaryErrors=0      # maintained for performance
    self.summarySuccesses=0   # maintained for performance
    self.lastExecutedAction = None
    # Lambdas for pre/post execution of each action
    self.preActionLambda = None
    self.postActionLambda = None
    # And then overwrite them with the given params
    for dictionary in initial_data:
      for key in dictionary:
        setattr(self, key, dictionary[key])
    for key in kwargs:
      setattr(self, key, kwargs[key])

  def setPreAction(self, cb=None):
    # Assign a function that is called BEFORE executing an action
    # The lambda must accept two params: index and action
    # Param 1: index of the action in the list of all actions
    # Param 2: the actual Action() object 
    self.preActionLambda = cb

  def setPostAction(self, cb=None):
    # Assign a function that is called AFTER executing an action
    # The lambda must accept two params: index and action
    # Param 1: index of the action in the list of all actions
    # Param 2: the actual Action() object 
    self.postActionLambda = cb

  def addTask(self, task):
    # Adds a task to the List of Task()
    self.tasks.append(task)

  def dryRun(self):
    # Does the actual Dry Run with selected tasks (generates the actions, does not execute them)
    self.actions = []
    self.errorGenerateActions = None
    self.summaryErrors=0 
    self.summarySuccesses=0 
    self.lastExecutedAction = None
    for task in self.tasks:
      #print "Generating actions for task %s" % task.description
      self.actions.extend(task.generateActions())
      if task.errorGenerateActions != None:
        self.errorGenerateActions = task.errorGenerateActions
        break

  def execute(self, force=False):
    # Does the real execution of the generated Actions
    # Param 1: if force = True, the execution will continue even if it finds errors
    self.summaryErrors=0 
    self.summarySuccesses=0 
    for index, action in enumerate(self.actions):
      if self.preActionLambda != None: self.preActionLambda(index, action)
      try:
        if action.command == 'cp':
          shutil.copy2(action.source, action.target)
        if action.command == 'mkdir':
          os.mkdir(action.target)
          shutil.copystat(action.source, action.target) # copy also the permissions
        if action.command == 'ln':
          if not action.isNew:  
            os.remove(action.source) # Python does not overwrite links, need to remove first if existed
          os.symlink(action.target, action.source) # target may be relative path # TODO windows requires an extra param
        self.summarySuccesses += 1 # if we got to this point, no errors occurred 
      except Exception as e: 
        action.errorMsg = e
        self.summaryErrors += 1
      # Action has finished (errors or not)
      action.hasExecuted = True
      self.lastExecutedAction = index
      if self.postActionLambda != None: self.postActionLambda(index, action)
      # Exit the loop if there has been an error, unless we're in force mode
      if not force and action.errorMsg != None:
        break

  def getExecutionLog(self, onlySummary=False, onlyErrors=False, limit=None):
    # Returns a string with the execution log. 
    txt = ''
    count = 0
    if not onlySummary:
      for index, action in enumerate(self.actions):
        # Consider only Executed actions
        if index > self.lastExecutedAction:
          break  
        # We print if onlyErrors=False or if the action has an error
        if not onlyErrors or action.errorMsg != None:
          txt += '%s\n' % action.getExecutionLog()
          count += 1
          continue
        if limit != None and count == limit:
          txt += '[...] (truncated to %d actions)\n' % limit
          break
    if self.lastExecutedAction != None:
      txt += '%d actions executed (of %d) with %d errors' % (self.lastExecutedAction + 1, len(self.actions), self.summaryErrors)
    else:
      txt += 'Execution has not yet begun'
    return txt


# ******** BEGIN *********
if __name__ == '__main__':
  # Running CLI
  # Catch interrupts  
  import signal
  def signal_term_handler(signal, frame):
    print('User Keyboard interrupt')
    sys.exit(0)
  signal.signal(signal.SIGINT, signal_term_handler)
  # To make raw_input for python 2/3
  real_raw_input = vars(__builtins__).get('raw_input',input)
  # Get params
  import argparse
  parser = argparse.ArgumentParser(description='DrySync copies source files/directories into a destination, asking the user for confirmation before actually doing it')
  parser.add_argument('source', help='Source files or directories', nargs='+', default=[])
  parser.add_argument('destination', help='Destination directory')
  parser.add_argument('--includetopdir', help='Sync also top directory', action="store_true")
  parser.add_argument('--norecursive', help='Prevent going down subdirectories', action="store_true")
  parser.add_argument('--verbose', '-v', help='Show all actions as they are executed', action="store_true")
  parser.add_argument('--force', help='Do not stop after the first execution error', action="store_true")
  parser.add_argument('--truncate', help='Display only the first N actions. (0 for All)', default='100', type=int)
  args, unknownargs = parser.parse_known_args()
  print vars(args)

  # Start creating the task
  run = DryRun()
  task = Task(inputPaths=args.source, outputPath=args.destination, recursive=not args.norecursive, skipTopDir=not args.includetopdir)
  #print vars(task)
  run.addTask(task)
  run.dryRun()
  if len(run.actions) < 1:
    print(" Source and destination are already in sync. Nothing to do")
    sys.exit()

  # There is work to do. Show it.
  print(" The following actions are needed to sync:")
  truncated = False
  for index, action in enumerate(run.actions):
    diff = "*" if not action.isNew else "" # mark actions with diff information to show
    print ("%d%s: %s" % (index, diff, action.toString()))
    if args.truncate > 1 and index == args.truncate - 1:
      print ("[...] %d actions to do" % len(run.actions))
      truncated = True
      break

  # Ask the user what to do next
  while True:
    print("\n Type action number to display details")
    if truncated:
      input = real_raw_input(" Or select: eXecute, show All, Quit [X/A/Q]?")
    else:
      input = real_raw_input(" Or select: eXecute, Quit [X/Q]?")
    # Check input
    if input in ['Q', 'q']:
      break
    elif input in ['A', 'a']:
      # Print all actions and ask again
      for index, action in enumerate(run.actions):
        print ("%d: %s" % (index, action.toString()))
      continue
    elif input in ['X', 'x']:
      print (" Syncing...")
      # We can pass a pre/post action callback
      if args.verbose:
        def log(index, action):
          print(action.getExecutionLog())
        run.setPostAction(log)
      # do the sync!
      run.execute(force=args.force) 
      print (run.getExecutionLog(onlyErrors=True, onlySummary=args.verbose)) # Only summary if verbose
      break
    elif input.isdigit() and int(input) < len(run.actions):
      print (run.actions[int(input)].showDetail())
      continue
    else:
      print(" Invalid answer!")

