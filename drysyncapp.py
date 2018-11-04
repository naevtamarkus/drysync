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

# Options to run this app:
# - Run normally without parameters for a full GUI
# - Run with 'auto' parameter to perform a dry sync and launch GUI only if necessary (if there are things to sync)
#
# In order to make this run regularly, insert this with 'crontab -e' as a user
# 0 8,16 * * * /home/myself/SharedStorage/drysync/drysyncapp.py auto >> /tmp/drysync-cron.log


import json
import os, sys
import ast
import datetime

from drysync import DryRun
from drysync import Task
from drysync import Action

#os.environ["KIVY_NO_CONSOLELOG"] = "1"
if 'DISPLAY' not in os.environ:
  os.environ["DISPLAY"] = ':0'

from kivy.app import App
#from kivy.uix.boxlayout import BoxLayout
from kivy.properties import ObjectProperty
from kivy.uix.stacklayout import StackLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.checkbox import CheckBox
from kivy.uix.scrollview import ScrollView
from kivy.uix.popup import Popup
from kivy.core.window import Window
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.lang import Builder

guiWidgets = """
#<Widget>:
#  canvas.after:
#    Line:
#      rectangle: self.x+1,self.y+1,self.width-1,self.height-1
#      dash_offset: 5
#      dash_length: 3

<NormalButton@Button>:
  width: '150dp'
  height: '50dp'
  size_hint: (None, None)

<ConfigureScreen>:
  on_pre_enter: self.preEnter()
  GridLayout:
    cols: 1
    StackLayout:
      padding: '6dp'
      spacing: '3dp'
      size_hint: (1,None)
      height: self.minimum_height
      NormalButton:
        text: 'Add new task'
        on_release: root.newTask()
      #NormalButton:
      #  id: saveButton
      #  text: 'Save'
      #  disabled: True
      #  on_press: root.saveConfig()
      NormalButton:
        text: 'Dry Run'
        background_color: (0,1,0,1)
        on_release: root.dryRun()
    ScrollView:
      size_hint: (1, 1)
      do_scroll_x: False
      GridLayout:
        id: taskList
        cols: 1
        size_hint: (1, None)
        row_default_height: '40dp'
        row_force_default: True
        height: self.minimum_height

<EditTaskScreen>:
  on_pre_enter: self.preEnter()
  GridLayout:
    cols: 1
    padding: '6dp'
    spacing: '3dp'
    row_default_height: '50dp'
    row_force_default: True
    # name
    BoxLayout:
      Label:
        text: 'Task name'   
        size_hint: (None,1)
        width: '120dp'
      TextInput:
        id: taskDescription
        padding_y: '15dp'
        multiline: False
    # Input
    BoxLayout:
      Label:
        text: 'Input'   
        size_hint: (None,1)
        width: '120dp'
      NormalButton:
        text: 'Choose'  
        width: '100dp'
        on_release: root.openInputSelectDialog()
      TextInput:
        id: inputText
        padding_y: '15dp'
        multiline: False
    # Checkbox 1
    GridLayout:
      rows: 1
      Label:
        size_hint: (None, 1)
        width: '60dp'
      CheckBox:
        id: inputRecursiveSync
        size_hint: (None, 1)
        width: '60dp'
      Label:
        text: 'Recursive sync (include subdirectories)'
        size_hint: (None, 1)
        size: self.texture_size
    # Checkbox 2
    GridLayout:
      rows: 1
      Label:
        size_hint: (None, 1)
        width: '60dp'
      CheckBox:
        id: inputDescendDirectories
        size_hint: (None, 1)
        width: '60dp'
      Label:
        text: 'Do not sync top directories, just its contents (/dir --> /dir/*)'
        size_hint: (None, 1)
        size: self.texture_size
    # Output
    BoxLayout:
      Label:
        text: 'Output'   
        size_hint: (None,1)
        width: '120dp'
      NormalButton:
        text: 'Choose'  
        width: '100dp'
        on_release: root.openOutputSelectDialog()
      TextInput:
        id: outputText
        padding_y: '15dp'
        multiline: False
    # Buttons below
    StackLayout:
      size_hint: (1,None)
    StackLayout:
      spacing: '3dp'
      size_hint: (1,None)
      height: self.minimum_height
      NormalButton:
        text: 'Cancel'
        on_press: root.cancel()
      NormalButton:
        id: deleteButton
        text: 'Delete task'
        on_press: root.deleteTask()
      NormalButton:
        text: 'Dry run'
        on_press: root.dryRun()
      NormalButton:
        id: saveAsNewButton
        text: 'Save as new task'
        on_press: root.saveAsNewTask()
        background_color: (0,1,0,1)
      NormalButton:
        text: 'Save'
        on_press: root.saveTask()
        background_color: (0,1,0,1)

<FileChooserDialog>:
  BoxLayout:
    size: root.size
    pos: root.pos
    orientation: "vertical"
    FileChooserIconView:
      id: filechooser
      dirselect: True
      multiselect: root.multi
    BoxLayout:
      size_hint_y: None
      height: 30
      Button:
        text: "Cancel"
        on_release: root.cancel()
      Button:
        text: "Choose"
        on_release: root.select(filechooser.path, filechooser.selection)

<ActionListScreen>:
  on_pre_enter: self.preEnter()
  GridLayout:
    cols: 1
    StackLayout:
      padding: '6dp'
      spacing: '3dp'
      size_hint: (1,None)
      height: self.minimum_height
      NormalButton:
        text: 'Cancel'
        on_press: root.cancel()
      NormalButton:
        text: 'Dry run again'
        on_press: root.dryRunAgain()
      NormalButton:
        id: executeButton
        text: 'Execute!'
        background_color: (0,1,0,1)
        on_press: root.realRun()
    ScrollView:
      size_hint: (1, 1)
      do_scroll_x: False
      GridLayout:
        id: actionList
        cols: 1
        size_hint: (1, None)
        row_default_height: '40dp'
        row_force_default: True
        height: self.minimum_height

<SingleActionLayout@GridLayout>:
  rows: 1
  Label:
    id: actionType
    size_hint: (None, 1)
    width: '60dp'
  Label: 
    id: actionParams
    halign: 'left'
    valign: 'middle'
    text_size: self.size
  Button:
    id: actionButton
    size_hint: (None, 1)
    width: '60dp'
    on_release: root.showDetail()

<TextPopup@Popup>:
  size_hint: (0.9, 0.9)
  BoxLayout:
    size: root.size
    pos: root.pos
    orientation: "vertical"
    ScrollView:
      Label:
        id: logText
        halign: 'left'
        valign: 'top'
        size_hint: (None, None)
        size: self.texture_size
    BoxLayout:
      size_hint_y: None
      height: 30
      Button:
        text: "Exit"
        on_release: root.dismiss()

"""

def loadFile(file, default):
  try:
    with open(file, 'r') as handle:
      return json.load(handle)
  except:
    return default

def saveFile(filename, variable):
  try:
    if not os.path.exists(os.path.dirname(filename)):
      os.makedirs(os.path.dirname(filename))
    with open(filename, 'w+') as file:
      file.write(json.dumps(variable, indent=2))  # use `json.loads` to do the reverse
  except:
    print("Error writing file %s" % filename)


class ConfigureScreen(Screen):
  def newTask(self):
    global editingTask
    editingTask = None  # New task for the other window
    global previousScreen
    previousScreen = 'Configure'
    sm.current = 'EditTask'
    
  def saveConfig(self):
    global tasks
    varlist = []
    for task in tasks: varlist.append(vars(task))
    config["goals"]["default"]["tasks"] = varlist
    saveFile(configFile, config)
    #self.ids.saveButton.disabled = True

  def showSingleTask(self, task, parentLayout):
    layout = GridLayout(rows=1)
    # Define Checkbox. Must be done in a separate function, to have independent callbacks (one for each checkbox)
    checkbox = CheckBox(size_hint=(None, 1), width='60dp', active=task.active)  # all aligned to left
    def onClickCheckbox(cb, val):
      task.active = val
      self.saveConfig()
      #self.ids.saveButton.disabled = False
    checkbox.bind(active=onClickCheckbox)
    layout.add_widget(checkbox)
    # Define Label. Same story.
    label = Label(text="[ref=all]%s[/ref]"%task.description, size_hint=(None, 1), markup=True)
    def onClickLabel(cb, val):
      global editingTask
      editingTask = task  
      global previousScreen
      previousScreen = 'Configure'
      sm.current = 'EditTask'
    label.bind(on_ref_press=onClickLabel)
    layout.add_widget(label)
    parentLayout.add_widget(layout)

  def preEnter(self):
    global editingTask
    global tasks
    # Display all tasks
    parentLayout = self.ids.taskList
    parentLayout.clear_widgets()
    if editingTask != None:
      # We're back from edit task and something changed
        self.saveConfig()
        #self.ids.saveButton.disabled = False
    for task in tasks:
      # Must be done in a separate function, to have independent callbacks (one for each checkbox)
      self.showSingleTask(task, parentLayout)
    editingTask = None  # Start with a clean slate

  def dryRun(self):
    global tasks
    global run
    run = DryRun()
    for task in tasks:
      if task.active:
        run.addTask(task)
    run.dryRun()
    global previousScreen
    previousScreen = 'Configure'
    sm.current = 'ListActions'


class EditTaskScreen(Screen):
  def cancel(self):
    global editingTask
    editingTask = None  # to tell parent there were no changes
    global previousScreen
    previousScreen = 'EditTask'
    sm.current = 'Configure'

  def deleteTask(self):
    global tasks
    global editingTask
    tasks.remove(editingTask)
    global previousScreen
    previousScreen = 'EditTask'
    sm.current = 'Configure'

  def genTaskFromForm(self, task):
    task.description = self.ids.taskDescription.text 
    task.inputPaths = ast.literal_eval(self.ids.inputText.text) # convert "['/bin']" to ['/bin']
    task.recursive = self.ids.inputRecursiveSync.active
    task.skipTopDir = self.ids.inputDescendDirectories.active
    task.outputPath = self.ids.outputText.text
    #editingTask.active = True # Use the previous value

  def saveTask(self):
    global editingTask
    global tasks
    if not self.isOldTask:
      # It's as new task
      editingTask = Task(active=True)
      tasks.append(editingTask)
    # editingTask now has the task to fill up
    self.genTaskFromForm(editingTask)
    # done filling up the instance, go back to previous screen
    global previousScreen
    previousScreen = 'EditTask'
    sm.current = 'Configure'

  def saveAsNewTask(self):
    self.isOldTask = False
    self.saveTask()

  # For popup:
  def selectInput(self, directory, filenames):
    # if no filenames are selected, take directory as target
    if len(filenames) > 0:
      self.ids.inputText.text = str(filenames)
    else:
      self.ids.inputText.text = str([directory])
    self._selectPopup.dismiss()

  # For popup:
  def selectOutput(self, directory, filenames):
    # if filenames is a single dir, take it instead
    if len(filenames) == 1 and os.path.isdir(filenames[0]):
      self.ids.outputText.text = filenames[0]
    else:
      self.ids.outputText.text = directory
    self._selectPopup.dismiss()

  # For popup:
  def cancelSelect(self):
    self._selectPopup.dismiss()

  # For popup:
  def openInputSelectDialog(self):
    content = FileChooserDialog(select=self.selectInput, cancel=self.cancelSelect, multi=True)
    self._selectPopup = Popup(title="Select input files/directories", content=content, size_hint=(0.9, 0.9))
    self._selectPopup.open()

  # For popup:
  def openOutputSelectDialog(self):
    content = FileChooserDialog(select=self.selectOutput, cancel=self.cancelSelect, multi=False)
    self._selectPopup = Popup(title="Select output directory", content=content, size_hint=(0.9, 0.9))
    self._selectPopup.open()

  def dryRun(self):
    global run
    run = DryRun()
    task = Task()
    self.genTaskFromForm(task) # populate task
    run.addTask(task)
    run.dryRun() # Do the run
    global previousScreen
    previousScreen = 'EditTask'
    sm.current = 'ListActions'

  def preEnter(self):
    self.isOldTask = (editingTask != None)
    # we don't create the Task instance until the end (in case they click on "Save as new task")
    if self.isOldTask:
      # If exists, fill up the form with its 
      self.ids.taskDescription.text = editingTask.description
      self.ids.inputText.text = str(editingTask.inputPaths) 
      self.ids.inputRecursiveSync.active = editingTask.recursive
      self.ids.inputDescendDirectories.active = editingTask.skipTopDir
      self.ids.outputText.text = editingTask.outputPath
      self.ids.saveAsNewButton.disabled = False
      self.ids.deleteButton.disabled = False
    else:
      # If new, fill up the form with default values
      self.ids.taskDescription.text = 'new task'
      self.ids.inputText.text = '[]'
      self.ids.inputRecursiveSync.active = False
      self.ids.inputDescendDirectories.active = False
      self.ids.outputText.text = ''
      self.ids.saveAsNewButton.disabled = True
      self.ids.deleteButton.disabled = True


class ActionListScreen(Screen):
  def cancel(self):
    if previousScreen != None:
      global sm
      sm.current = previousScreen

  def preEnter(self):
    global run 
    parentLayout = self.ids.actionList
    parentLayout.clear_widgets()
    # Display error on top
    if run.errorGenerateActions != None:
      parentLayout.add_widget(Label(text='ERROR in dry run\n%s' % run.errorGenerateActions))
      self.ids.executeButton.disabled = True
    else:
      self.ids.executeButton.disabled = False
    # Display all actions
    for index, action in enumerate(run.actions):
      if index > 100: break # TODO hide too many actions. Need pagination
      actionWidget = SingleActionLayout()
      actionWidget.setAction(action)
      parentLayout.add_widget(actionWidget)
    # If no actions, just say it
    if len(run.actions) == 0:
      parentLayout.add_widget(Label(text='Destination is up to date, nothing to do'))

  def realRun(self):
    # Finally, do the task
    global run
    self.runPopup = TextPopup()
    self.runPopup.open()
    self.runPopup.title = "Running..."
    # Run the stuff and show the logs
    run.execute()
    self.runPopup.ids.logText.text = run.getExecutionLog(limit=100, onlyErrors=True)
    # Update the screen behind the popup
    parentLayout = self.ids.actionList
    parentLayout.clear_widgets()
    parentLayout.add_widget(Label(text=run.getExecutionLog(onlySummary=True)))

  def dryRunAgain(self):
    global run
    run.dryRun()
    self.preEnter()


class SingleActionLayout(GridLayout):
  # Action():
    # command (txt) cp|mkdir|ln
    # target (txt)
    # source (txt) only for copy
    # isNew (bool)
  def setAction(self, action):
    self.action = action
    self.ids.actionType.text = action.command
    if action.command == 'mkdir' or action.isNew:
      self.ids.actionButton.text = "New"
      self.ids.actionButton.disabled = True
    else: 
      self.ids.actionButton.text = "Diff"
      self.ids.actionButton.disabled = False
    if action.command == 'cp' or action.command == 'ln':
      self.ids.actionParams.text = action.source + ' --> ' + action.target
    else:
      self.ids.actionParams.text = action.target

  def showDetail(self):
    self.diffPopup = TextPopup()
    self.diffPopup.open()
    self.diffPopup.title = "Detailed differences"
    tw = self.diffPopup.ids.logText
    tw.text = self.action.showDetail()


class FileChooserDialog(FloatLayout):
  select = ObjectProperty(None)
  cancel = ObjectProperty(None)
  multi = ObjectProperty(None)

class TextPopup(Popup):
  pass



# ******** BEGIN *********

# Prepare config & Globals
configFile = os.path.expanduser('~/.drysync/drysync.conf')
pidFile = os.path.expanduser('~/.drysync/drysync.pid')
config = None
tasks = []
sm = None
run = None  # actions are inside here

# editingTask is a tmp place to store task when we are editing it 
# If editingTask == None, it can have two meanings:
# - for the task edit screen, it's a new task
# - for the configure main screen, the editing task did NOT save changes
editingTask = None  
defaultConfig = {
    "goals": {"default": {"tasks": [] }}
  }

# Kill previous instances of this app
pid = loadFile(pidFile, None)
if pid != None:
  try:
    os.kill(pid,9)
  except:
    pass
saveFile(pidFile, os.getpid())

# Load the default config
config = loadFile(configFile, defaultConfig)
for task in config["goals"]["default"]["tasks"]:
  tasks.append(Task(task))

# Temporarily populate it:
#for i in range(3):
#  tasks.append(Task({"description": "item %d"%i, "active": i != 2}))

class DrySyncApp(App):
  def build(self):
    return sm

def initGUI(current = 'Configure'):
  global sm
  Builder.load_string(guiWidgets)
  sm = ScreenManager()
  sm.add_widget(ConfigureScreen(name='Configure'))
  sm.add_widget(EditTaskScreen(name='EditTask'))
  sm.add_widget(ActionListScreen(name='ListActions'))
  sm.current = current
  DrySyncApp().run()


if __name__ == '__main__':
  if 'auto' in sys.argv:
    # Do the Dry Run and launch screen only if there is something to do
    # global run (is already global here)
    run = DryRun()
    for task in tasks:
      if task.active:
        run.addTask(task)
    run.dryRun()
    if len(run.actions) > 0:
      print "%s - %d actions to do" % (str(datetime.datetime.now()), len(run.actions))
      # There is work to do. Launch the app
      previousScreen = 'Configure'
      # Create the different screens
      initGUI('ListActions')
    else:
      print "%s - Nothing to do" % str(datetime.datetime.now())
      # and exit
  else:
    # Launch the screen directly  
    # Create the different screens
    initGUI()

  # At the end, remove the pid file
  try:
    os.remove(pidFile)
  except:
    pass
    
