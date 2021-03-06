#! /usr/bin/env python
# -*- coding: iso-8859-1 -*-
"""
 Unit: MainWindow
 Project: BioImageXD
 Description:

 The main window for the BioImageXD program

 Copyright (C) 2005  BioImageXD Project
 See CREDITS.txt for details

 This program is free software; you can redistribute it and/or modify
 it under the terms of the GNU General Public License as published by
 the Free Software Foundation; either version 2 of the License, or
 (at your option) any later version.

 This program is distributed in the hope that it will be useful,
 but WITHOUT ANY WARRANTY; without even the implied warranty of
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 GNU General Public License for more details.

 You should have received a copy of the GNU General Public License
 along with this program; if not, write to the Free Software
 Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""

__author__ = "BioImageXD Project <http://www.bioimagexd.org/>"
__version__ = "$Revision: 1.71 $"
__date__ = "$Date: 2005/01/13 13:42:03 $"

from bxdversion import VERSION

import AboutDialog
import BatchProcessor
import BugDialog
import scripting
import Configuration
import ConfigParser
import Dialogs
import ExportDialog
import imp
import InfoWidget
import lib.Command # Module for classes that implement the Command design pattern
import lib.DataSource.BXDDataWriter
import lib.messenger
import Logging
import MaskTray
import MenuManager
import Modules.DynamicLoader
import os
import os.path
import platform
import wx.py as py
import random
import ResampleDialog
import RescaleDialog
import ScriptEditor
import SettingsWindow
import sys
import time
import GUI.TreeWidget
import types
import UIElements
import UndoListBox
from Visualizer.Visualizer import Visualizer
import wx
import lib.ImageOperations
import QuitDialog
import Urmas.UrmasWindow

class MainWindow(wx.Frame):
	"""
	Description: The main window of the BioImageXD software
	"""
	def __init__(self, parent, id, app, splash):
		"""
		Initialization
		"""
		# A flag indicating whether we've loaded files at startup (i.e. they were given on command line or dragged over the icon)
		self.loadFilesAtStartup = False
		conf = Configuration.getConfiguration()
		
		lib.Command.mainWindow = self
		self.splash = splash
		scripting.recorder = self.recorder = lib.Command.ScriptRecorder()
		
		size = conf.getConfigItem("WindowSize", "Sizes")
		if size:
			size = eval(size)
		else:
			size = (1024, 768)

		wx.Frame.__init__(self, parent, -1, "BioImageXD", size = size,
			style = wx.DEFAULT_FRAME_STYLE | wx.NO_FULL_REPAINT_ON_RESIZE)
		self.Bind(
			wx.EVT_SASH_DRAGGED_RANGE, self.onSashDrag,
			id = MenuManager.ID_TREE_WIN, id2 = MenuManager.ID_INFO_WIN,
		)
		self.Bind(wx.EVT_MENU_RANGE, self.OnFileHistory, id = wx.ID_FILE1, id2 = wx.ID_FILE9)
		self.Bind(wx.EVT_CLOSE, self.quitApp)
		self.progressTimeStamp = 0
		self.progressObject = None
		self.filehistory = wx.FileHistory()
		self.commands = {}
		
		self.defaultModeName = "slices"
		
		self.tasks = {}
		self.help = None
		self.statusbar = None
		self.progress = None
		self.visualizationPanel = None
		self.visualizer = None
		self.nodes_to_be_added = []
		self.app = app
		self.commandHistory = None
		
		self.paths = {}
		self.currentTaskWindow = None
		self.currentTaskWindowName = ""
		self.currentTaskWindowType = None

		self.currentTask = ""
		self.currentFile = ""
		scripting.currentVisualizationMode = ""
		self.progressCoeff = 1.0
		self.progressShift = 0.0
		self.taskToId = {}
		self.visToId = {}

		self.splash.SetMessage("Loading filter modules...")
		Modules.DynamicLoader.getFilterModules()
		self.splash.SetMessage("Loading task modules...")
		self.taskPanels = Modules.DynamicLoader.getTaskModules(callback = self.splash.SetMessage)
		self.splash.SetMessage("Loading visualization modes...")
		self.visualizationModes = Modules.DynamicLoader.getVisualizationModes(callback = self.splash.SetMessage)
		self.splash.SetMessage("Loading image readers...")
		self.readers = Modules.DynamicLoader.getReaders(callback = self.splash.SetMessage)
		self.extToSource = {}
		self.typeToSource = {}
		self.datasetWildcards = "Volume datasets|*.jpg;*.jpeg;*.tif;*.tiff;*.png;*.bmp;"
		
		descs = []
		self.splash.SetMessage("Initializing application...")

		for modeclass, ign, module in self.readers.values():
			exts = module.getExtensions()
			wcs = ""
			self.typeToSource[module.getFileType()] = modeclass

			for ext in exts:
				self.extToSource[ext] = modeclass
				wcs += "*.%s;" % ext
				wcs += "*.%s;" % ext.upper()
				self.datasetWildcards += wcs

			if len(exts) > 0:
				descs.append("%s|%s" % (module.getFileType(), wcs[:-1]))
			
		self.datasetWildcards = self.datasetWildcards[:-1]
		self.datasetWildcards += "|"
		self.datasetWildcards += "|".join(descs)
		
		self.datasetWildcards += "|JPEG image stack (*.jpg)|*.jpg"
		self.datasetWildcards += "|TIFF image stack (*.tif)|*.tif;*.tiff"
		self.datasetWildcards += "|PNG image stack (*.png)|*.png"
		self.datasetWildcards += "|BMP image stack (*.bmp)|*.bmp"
		for i in self.taskPanels.keys():
			self.taskToId[i] = wx.NewId()
			
		for i in self.visualizationModes.keys():
			self.visToId[i] = wx.NewId()
		
		self.splash.SetMessage("Initializing layout...")
		self.menuManager = MenuManager.MenuManager(self, text = 0)
		
		# A window for the file tree
		self.treeWin = wx.SashLayoutWindow(self, MenuManager.ID_TREE_WIN, style = wx.RAISED_BORDER | wx.SW_3D)
		self.treeWin.SetOrientation(wx.LAYOUT_VERTICAL)
		self.treeWin.SetAlignment(wx.LAYOUT_LEFT)
		self.treeWin.SetSashVisible(wx.SASH_RIGHT, True)
		self.treeWin.SetDefaultSize((160, 768))
		self.treeWin.origSize = (160, 768)

		self.treeBtnWin = wx.SashLayoutWindow(self.treeWin, wx.NewId(), style = wx.SW_3D)
		self.treeBtnWin.SetOrientation(wx.LAYOUT_HORIZONTAL)
		self.treeBtnWin.SetAlignment(wx.LAYOUT_BOTTOM)
		self.treeBtnWin.SetSashVisible(wx.SASH_TOP, False)
		self.treeBtnWin.SetDefaultSize((160, 32))
		
		self.switchBtn = wx.Button(self.treeBtnWin, -1, "Apply change")
		self.switchBtn.Bind(wx.EVT_BUTTON, self.onSwitchDataset)
		self.switchBtn.Enable(0)
	
		# A window for the visualization modes
		self.visWin = wx.SashLayoutWindow(self, MenuManager.ID_VIS_WIN, style = wx.RAISED_BORDER | wx.SW_3D)
		self.visWin.SetDoubleBuffered(True)
		self.visWin.SetOrientation(wx.LAYOUT_VERTICAL)
		self.visWin.SetAlignment(wx.LAYOUT_LEFT)
		self.visWin.SetSashVisible(wx.SASH_RIGHT, False)
		self.visWin.SetDefaultSize((500, 768))
		
		# A window for the task panels
		self.taskWin = wx.SashLayoutWindow(self, MenuManager.ID_TASK_WIN, style = wx.RAISED_BORDER | wx.SW_3D)
		self.taskWin.parent = self
		self.taskWin.SetOrientation(wx.LAYOUT_VERTICAL)
		self.taskWin.SetAlignment(wx.LAYOUT_RIGHT)
		self.taskWin.SetSashVisible(wx.SASH_LEFT, True)
		#self.taskWin.SetSashBorder(wx.SASH_LEFT, True)
		self.taskWin.SetDefaultSize((0, 768))
		self.taskWin.origSize = (360, 768)
		conf = Configuration.getConfiguration()
		s = conf.getConfigItem("TaskWinSize", "Sizes")
		if s:
			s = eval(s)
			self.taskWin.origSize = s
		
		# A window for the task panels
		self.infoWin = wx.SashLayoutWindow(self, MenuManager.ID_INFO_WIN, style = wx.RAISED_BORDER | wx.SW_3D)
		self.infoWin.SetOrientation(wx.LAYOUT_VERTICAL)
		self.infoWin.SetAlignment(wx.LAYOUT_RIGHT)
		self.infoWin.SetSashVisible(wx.SASH_LEFT, True)
		#self.infoWin.SetSashBorder(wx.SASH_LEFT, True)
		self.infoWin.SetDefaultSize((300, 768))
		self.infoWin.origSize = (300, 768)
		
		self.infoWidget = InfoWidget.InfoWidget(self.infoWin)
		
		self.shellWin = wx.SashLayoutWindow(self, MenuManager.ID_SHELL_WIN, style = wx.NO_BORDER)
		self.shellWin.SetOrientation(wx.LAYOUT_HORIZONTAL)
		self.shellWin.SetAlignment(wx.LAYOUT_BOTTOM)
		self.shellWin.origSize = (500, 128)
		self.shellWin.SetDefaultSize((0, 0))
		self.shell = None
		
		
		# Icon for the window
		ico = reduce(os.path.join, [scripting.get_icon_dir(), "logo.ico"])
		self.icon = wx.Icon(ico, wx.BITMAP_TYPE_ICO)
			
		self.SetIcon(self.icon)
		
		lib.messenger.send(None, "update_progress", 0.1, "Loading BioImageXD...")
		
		# Create Menu, ToolBar and Tree
		self.createStatusBar()
		lib.messenger.send(None, "update_progress", 0.3, "Creating menus...")
		self.splash.SetMessage("Creating menus...")
		self.createMenu()
		lib.messenger.send(None, "update_progress", 0.6, "Creating toolbars...")
		self.splash.SetMessage("Creating tool bar...")
		self.createToolBar()
		
		self.Bind(wx.EVT_SIZE, self.OnSize)
		lib.messenger.send(None, "update_progress", 0.9, "Pre-loading visualization views...")
		
		# Create the file tree
		self.tree = GUI.TreeWidget.TreeWidget(self.treeWin)
		
		# Alias for scripting
		self.fileTree = self.tree
		
		self.splash.SetMessage("Loading default visualization mode...")
		self.loadVisualizer(self.defaultModeName, init = 1)
		
		self.onMenuShowTree(show = True)
		try:
			self.splash.Show(False)
			del self.splash
		except:
			pass
		self.SetSize(size)

		self.Show(True)
		# Start listening for messenger signals
		lib.messenger.send(None, "update_progress", 1.0, "Done.") 
		lib.messenger.connect(None, "set_status", self.onSetStatus)
		lib.messenger.connect(None, "current_task", self.updateTitle)
		lib.messenger.connect(None, "current_file", self.updateTitle)
		lib.messenger.connect(None, "tree_selection_changed", self.onTreeSelectionChanged)
		lib.messenger.connect(None, "get_voxel_at", self.updateVoxelInfo)
		lib.messenger.connect(None, "show_measured_distance", self.onShowDistance)
		lib.messenger.connect(None, "load_dataunit", self.onMenuOpen)
		lib.messenger.connect(None, "view_help", self.onViewHelp)
		lib.messenger.connect(None, "delete_dataset", self.onDeleteDataset)
		lib.messenger.connect(None, "execute_command", self.onExecuteCommand)
		lib.messenger.connect(None, "show_error", self.onShowError)
		lib.messenger.connect(None, "data_changed", self.updateCache)

		wx.CallAfter(self.showTip)
		filelist = conf.getConfigItem("FileList", "General")
		# We do not restore files is there were files requested to be loaded at startup
		# because that might mess with e.g. scripts 
		if filelist and not self.loadFilesAtStartup:
			filelist = eval(filelist)
			restoreFiles = conf.getConfigItem("RestoreFiles", "General")
			if restoreFiles and type(restoreFiles) == type(""):
				restoreFiles = eval(restoreFiles)
			if restoreFiles:
				self.loadFiles(filelist, noWarn = 1)

		reportCrash = conf.getConfigItem("ReportCrash", "General")
		if reportCrash and type(reportCrash) == type(""):
			reportCrash = eval(reportCrash)
		if reportCrash and scripting.uncleanLog:
			self.reportCrash()
		
		lst = conf.getConfigItem("HistoryList", "General")
		if lst:
			lst = eval(lst)
			for item in lst:
				self.filehistory.AddFileToHistory(item)

	def reportCrash(self):
		"""
		send a bug report reporting the latest crash
		"""
		dlg = BugDialog.BugDialog(self, crashMode = 1)
		dlg.crashModeOn(scripting.uncleanLog)
		conf = Configuration.getConfiguration()

		try:
			data = open(scripting.uncleanLog).read()
		except:
			return
		dlg.setContent("User actions resulted a crash", data)
		dlg.ShowModal()

	def Cleanup(self, *args):
		"""
		clean up the file history
		"""
		# A little extra cleanup is required for the FileHistory control
		del self.filehistory
		self.menu.Destroy()
		
	def OnFileHistory(self, evt):
		"""
		An event handler for when the user selects a history item from file menu
		"""
		# get the file based on the menu ID

		fileNum = evt.GetId() - wx.ID_FILE1

		path = self.filehistory.GetHistoryFile(fileNum)

		self.loadFiles([path])

	def loadScript(self, filename):
		"""
		Load a given script file
		"""
		Logging.info("Loading script %s" % filename, kw = "scripting")
		f = open(filename)
		module = imp.load_module("script", f, filename, ('.py', 'r', 1))
		f.close()
		module.scripting = scripting
		module.mainWindow = self
		module.visualizer = self.visualizer
		module.run()
		
	def loadFiles(self, files, noWarn = 0):
		"""
		Load the given data files
		"""
		self.loadFilesAtStartup = True
		for file in files:
			name = os.path.basename(file)
			self.createDataUnit(name, file, noWarn = noWarn)

	def onMenuUndo(self, evt):
		"""
		Undo a previous command
		"""
		cmd = self.menuManager.getLastCommand()
		if cmd and cmd.canUndo():		# Undo the previous command if there has been a previous command.
			cmd.undo()
			self.menuManager.setUndoedCommand(cmd)
			self.menuManager.enable(MenuManager.ID_REDO)
		
	def onMenuRedo(self, evt):
		"""
		Redo a previously undo'd action
		"""
		cmd = self.menuManager.getUndoedCommand()
		cmd.run()
		self.menuManager.disable(MenuManager.ID_REDO)
		self.menuManager.enable(MenuManager.ID_UNDO)
		
	def onExecuteCommand(self, obj, evt, command, undo = 0):
		"""
		A command was executed
		"""
		if not undo:
			if command.canUndo():
				undolbl = "Undo: %s...*\tCtrl-Z" % command.getDesc()
				if not scripting.TFLag:
					self.menuManager.menus["edit"].SetLabel(MenuManager.ID_UNDO, undolbl)
		else:
			redolbl = "Redo: %s...*\tShift-Ctrl-Z" % command.getCategory()
			if not scripting.TFLag:
				self.menuManager.menus["edit"].SetLabel(MenuManager.ID_REDO, redolbl)
				self.menuManager.menus["edit"].SetLabel(MenuManager.ID_UNDO, "Undo...*\tCtrl-Z")
		self.menuManager.addCommand(command)
		
	def onDeleteDataset(self, obj, evt, arg):
		"""
		Remove a dataset from the program
		"""
		close = 0
		Logging.info("onDeleteDataset, visualizer dataset = ", self.visualizer.dataUnit, "deleted=", arg)
		if self.visualizer.dataUnit == arg:
			close = 1
		if self.visualizer.getProcessedMode():
			if arg in self.visualizer.dataUnit.getSourceDataUnits():
				self.onCloseTaskPanel(None)
		if close:
			mode = self.visualizer.mode
			self.closeVisualizer()
			self.infoWidget.clearInfo()
			self.loadVisualizer(mode)

	def onSwitchDataset(self, evt):
		"""
		Switch the datasets used by a task module
		"""
		lib.messenger.send(None, "clear_cache_dataunits")
		# Z might change when changing datasets.
		#z = self.visualizer.getZSliderValue() - 1
		selectedFiles = self.tree.getSelectedDataUnits()
		lib.messenger.send(None, "switch_datasets", selectedFiles)
		#if z > self.visualizer.zslider.GetMax():
		#	z = self.visualizer.zslider.GetMax() - 1
		#lib.messenger.send(None, "zslice_changed", z)

	def showTip(self):
		"""
		Show a tip to the user
		"""
		conf = Configuration.getConfiguration()
		showTip = conf.getConfigItem("ShowTip", "General")
		if showTip:
			showTip = eval(showTip)
		tipNumber = int(conf.getConfigItem("TipNumber", "General"))
		if showTip:
			f = open("Help/tips.txt", "r")
			n = len(f.readlines())
			f.close()
			tp = wx.CreateFileTipProvider("Help/tips.txt", random.randrange(n))
			showTip = wx.ShowTip(self, tp)
			index = tp.GetCurrentTip()
			conf.setConfigItem("ShowTip", "General", showTip)
			conf.setConfigItem("TipNumber", "General", index)

	def onTreeSelectionChanged(self, obj, evt, data):
		"""
		A method for updating the dataset based on tree selection
		"""
		selected = self.tree.getSelectedDataUnits()
		dataunits = {}
		if len(selected)==1 and hasattr(selected[0], "getSourceDataUnits"):
			selected = selected[0].getSourceDataUnits()
		for i in selected:
			pth = i.dataSource.getPath()
			if pth in dataunits:
				dataunits[pth].append(i)
			else:
				dataunits[pth] = [i]
		names = [i.getName() for i in selected]
		do_cmd = "mainWindow.fileTree.unselectAll()"
		for i in dataunits.keys():
			names = [x.getName() for x in dataunits[i]]
			filename = i.replace("'", "\\'")
			do_cmd += "\n" + "mainWindow.fileTree.selectChannelsByName(r'%s', %s)" % (filename, str(names))
		undo_cmd = ""

		cmd = lib.Command.Command(lib.Command.MGMT_CMD, None, None, do_cmd, \
									undo_cmd, desc = "Unselect all in file tree")
		cmd.run(recordOnly = 1)

		# Bug-fix (Mac): double click on a multi-channeled dataset's parent in the file tree
		if isinstance(data, str):
			return
		if data.dataSource.getResampling():
			if scripting.resamplingDisabled:
				self.visualizer.resamplingBtn.SetToggle(False)
				self.menuManager.check(MenuManager.ID_MENU_RESAMPLING, False)
			else:
				self.visualizer.resamplingBtn.SetToggle(True)
				self.menuManager.check(MenuManager.ID_MENU_RESAMPLING, True)
			self.visualizer.resamplingBtn.Enable(1)
			self.menuManager.enable(MenuManager.ID_MENU_RESAMPLING)
		else:
			self.visualizer.resamplingBtn.SetToggle(False)
			self.visualizer.resamplingBtn.Enable(0)
			self.menuManager.check(MenuManager.ID_MENU_RESAMPLING, False)
			self.menuManager.disable(MenuManager.ID_MENU_RESAMPLING)

		# If no task window has been loaded, then we will update the visualizer
		# with the selected dataset
		if not self.currentTaskWindow:
			data.getSettings().resetSettings()
			Logging.info("Setting dataset for visualizer=", data.__class__, kw = "dataunit")
			self.visualizer.setDataUnit(data)
			#self.visualizer.updateRendering()
		
	def updateTitle(self, obj, evt, data):
		"""
		A method for updating the title of this window
		"""
		if evt == "current_task":
			self.currentTask = data
		elif evt == "current_file":
			self.currentFile = data
		lst = ["BioImageXD", self.currentTask, self.currentFile] 
		
		self.SetTitle(lst[0] + " - " + lst[1] + " (" + lst[2] + ")")
		
		
	def onSashDrag(self, event):
		"""
		A method for laying out the window
		"""
		if event.GetDragStatus() == wx.SASH_STATUS_OUT_OF_RANGE:
			return

		eID = event.GetId()

		if eID == MenuManager.ID_TREE_WIN:
			w, h = self.treeWin.GetSize()
			newsize = (event.GetDragRect().width, h)
			self.treeWin.SetDefaultSize(newsize)
			self.treeWin.origSize = newsize

		elif eID == MenuManager.ID_INFO_WIN:
			w, h = self.infoWin.GetSize()
			newsize = (event.GetDragRect().width, h)
			self.infoWin.SetDefaultSize(newsize)
			self.infoWin.origSize = newsize
		elif eID == MenuManager.ID_TASK_WIN:
			w, h = self.taskWin.GetSize()
			newsize = (event.GetDragRect().width, h)
			self.taskWin.SetDefaultSize(newsize)
			self.taskWin.origSize = newsize
			
			conf = Configuration.getConfiguration()
			conf.setConfigItem("TaskWinSize", "Sizes", str(newsize))
			
		wx.LayoutAlgorithm().LayoutWindow(self, self.visWin)
		self.visualizer.OnSize(None)
		self.visWin.Refresh()

	def OnSize(self, event):
		"""
		the size event handler for main window
		"""
		wx.LayoutAlgorithm().LayoutWindow(self, self.visWin)
		if self.statusbar:
			rect = self.statusbar.GetFieldRect(2)
			self.progress.SetPosition((rect.x + 2, rect.y + 2))
			self.progress.SetSize((rect.width - 4, rect.height - 4))
			rect = self.statusbar.GetFieldRect(1)
			self.colorLbl.SetPosition((rect.x + 2, rect.y + 2))
			self.colorLbl.SetSize((rect.width - 4, rect.height - 4))

	def showVisualization(self, window):
		"""
		Changes the window to show in the split window
		"""
		if window == self.visualizer.getCurrentWindow():
			return
		window.Show()
			
		wx.LayoutAlgorithm().LayoutWindow(self, self.visWin)
		self.visWin.Refresh()

	def onSetStatus(self, obj, event, arg):
		"""
		Set the status text
		"""
		self.statusbar.SetStatusText(arg)
	
	def onShowError(self, obj, event, title, msg):
		"""
		Show an error message
		"""
		Dialogs.showerror(self, msg, title)

	def updateProgressBar(self, obj, event, arg, text = None, allow_gui = 1):
		"""
		Updates the progress bar
		"""
		if self.progressObject and obj != self.progressObject:
			return
		t = time.time()
		#if arg not in [1.0, 100] and abs(t - self.progressTimeStamp) < 1:
		#	return

		self.progressTimeStamp = t
		if type(arg) == types.FloatType:
			arg *= 100
		# The progress coefficient gives us some amount of control on what range
		arg *= self.progressCoeff
		arg += self.progressShift

		self.progress.SetValue(int(arg))

		if int(arg) >= 100:
			wx.CallLater(1500, self.clearProgressBar)
		else:
			self.progress.Show()
			
		renderingEnabled = scripting.renderingEnabled
		scripting.renderingEnabled = False
		self.progress.Update()
		scripting.renderingEnabled = renderingEnabled
		
		if text:
			self.statusbar.SetStatusText(text)
			self.statusbar.Update()

				
	def clearProgressBar(self,*args):
		"""
		clear the progress bar
		"""
		self.statusbar.SetStatusText("")
		self.statusbar.Update()
		self.progress.Show(0)
		self.progress.Update()
		
	def onShowDistance(self, obj, event, distance):
		"""
		Show the distance measured in interactive panel
		"""
		dataunit = scripting.visualizer.getDataUnit()
		xsize,ysize,zsize = dataunit.getVoxelSize()
		print "voxel sizes=",xsize,ysize,zsize
		distanceUm = distance*xsize*(1000000)
		text = u"%d pixels = %.2f\u03BCm"%(distance, distanceUm)
		self.statusbar.SetStatusText(text)
			
	def updateVoxelInfo(self, obj, event, x, y, z, scalar, rval, gval, bval, r, g, b, a, ctf):
		"""
		Update the voxel info in status bar
		"""
		z += 1
		if scalar != 0xdeadbeef:
			#print obj,event,x,y,z,scalar, rval, gval, bval, r,g,b,a
			if type(scalar) == types.TupleType:
				if len(scalar) > 1:
					lst = map(str, map(int, scalar))
					
					scalartxt = ", ".join(lst[:-1])
					scalartxt += " and " + lst[-1]
					text = "Scalars %s at (%d,%d,%d) map to (%d,%d,%d)" % (scalartxt, x, y, z, r, g, b)
				else:
					scalar = int(scalar[0])
					text = "Scalar %d at (%d,%d,%d) maps to (%d,%d,%d)" % (scalar, x, y, z, r, g, b)
			else:
				scalar = int(scalar)
				text = "Scalar %d at (%d,%d,%d) maps to (%d,%d,%d)" % (scalar, x, y, z, r, g, b)
		else:
			text = "Color (%s,%s,%s) at (%d,%d,%d) is (%d,%d,%d)" % (rval, gval, bval, x, y, z, r, g, b)
			if a != -1:
				text += " with alpha %d" % a
		self.colorLbl.setLabel(text)
		self.colorLbl.SetToolTip(wx.ToolTip(text))

		#fg = 255 - r, 255 - g, 255 - b
		#bg = r, g, b
		bg = 0, 0, 0 # Black
		fg = 255, 255, 255 # White
		self.colorLbl.setColor(fg, bg)
		#wx.GetApp().Yield(1)
		#wx.SafeYield()
		
	def sortModes(self, x, y):
		return cmp(x[2].getToolbarPos(), y[2].getToolbarPos())
		
	def createToolBar(self):
		"""
		Creates a tool bar for the window
		"""
		iconpath = scripting.get_icon_dir()
		self.CreateToolBar(wx.TB_HORIZONTAL, MenuManager.ID_MAIN_TOOLBAR)
		tb = self.GetToolBar()
		tb.SetMargins((5,5))
		tb.SetToolBitmapSize((32, 32))
		self.taskIds = []
		self.visIds = []
		Logging.info("Creating toolbar", kw = "init")
		bmp = wx.Image(os.path.join(iconpath, "FileIO_OpenDataset.png"), wx.BITMAP_TYPE_PNG).ConvertToBitmap()
		tb.DoAddTool(MenuManager.ID_OPEN, "Open dataset", bmp, shortHelp = "Open dataset")
		wx.EVT_TOOL(self, MenuManager.ID_OPEN, self.onMenuOpen)

		bmp = wx.Image(os.path.join(iconpath, "FileIO_SaveDataset.png"), wx.BITMAP_TYPE_PNG).ConvertToBitmap()
		tb.DoAddTool(MenuManager.ID_SAVE_DATASET, "Save dataset", bmp, \
						shortHelp = "Save dataset")
		wx.EVT_TOOL(self, MenuManager.ID_SAVE_DATASET, self.onSaveDataset)

		
		bmp = wx.Image(os.path.join(iconpath, "FileIO_OpenSettings.png"), wx.BITMAP_TYPE_PNG).ConvertToBitmap()
		tb.DoAddTool(MenuManager.ID_OPEN_SETTINGS, "Open settings", bmp, shortHelp = "Open settings")
		wx.EVT_TOOL(self, MenuManager.ID_OPEN_SETTINGS, self.onMenuOpenSettings)
		bmp = wx.Image(os.path.join(iconpath, "FileIO_SaveSettings.png"), wx.BITMAP_TYPE_PNG).ConvertToBitmap()
		tb.DoAddTool(MenuManager.ID_SAVE_SETTINGS, "Save settings", bmp, shortHelp = "Save settings")
		wx.EVT_TOOL(self, MenuManager.ID_SAVE_SETTINGS, self.onMenuSaveSettings)

		bmp = wx.Image(os.path.join(iconpath, "FileIO_Snapshot.png"), wx.BITMAP_TYPE_PNG).ConvertToBitmap()
		tb.DoAddTool(MenuManager.ID_SAVE_SNAPSHOT, "Save rendered image", bmp, \
						shortHelp = "Save snapshot image")

		bmp = wx.Image(os.path.join(iconpath, "FileIO_Tree.png"), wx.BITMAP_TYPE_PNG).ConvertToBitmap()
		tb.DoAddTool(MenuManager.ID_SHOW_TREE, "File manager", bmp, kind = wx.ITEM_CHECK, \
						shortHelp = "View file tree")
		wx.EVT_TOOL(self, MenuManager.ID_SHOW_TREE, self.onMenuShowTree)

		modules = self.taskPanels.values()
		modules.sort(self.sortModes)

		if platform.system() != "Darwin":
			tb.AddSeparator()
		
		for (moduletype, windowtype, mod) in modules:
			name = mod.getName()
			shortDesc = mod.getShortDesc()
			bmp = wx.Image(os.path.join(iconpath, mod.getIcon())).ConvertToBitmap()
			
			tid = self.taskToId[name]
			tb.DoAddTool(tid, name, bmp, kind = wx.ITEM_CHECK, shortHelp = shortDesc)
			wx.EVT_TOOL(self, tid, self.onMenuShowTaskWindow)
			self.taskIds.append(tid)

		if platform.system() != "Darwin":
			tb.AddSeparator()
		
		modes = self.visualizationModes.values()
		modes.sort(self.sortModes)

		for (mod, settingclass, module) in modes:
			name = module.getName()
			iconName = module.getIcon()
			# Visualization modes that do not wish to appear in the toolbar need to 
			# return None as their icon name
			if not iconName:
				continue
			if module.isDefaultMode():
				self.defaultModeName = name
			bmp = wx.Image(os.path.join(iconpath, iconName)).ConvertToBitmap()
			vid = self.visToId[name]
			
			sepBefore, sepAfter = module.showSeparator()
			if sepBefore:
				if platform.system() != "Darwin":
					tb.AddSeparator()
			
			tb.DoAddTool(vid, module.getShortDesc(), bmp, kind = wx.ITEM_CHECK, shortHelp = module.getShortDesc())
			
			if sepAfter:
				if platform.system() != "Darwin":
					tb.AddSeparator()
			
			wx.EVT_TOOL(self, vid, self.onMenuVisualizer)
			self.visIds.append(vid)
			if module.isDefaultMode():
				tb.ToggleTool(vid, 1)
		
		bmp = wx.Image(os.path.join(iconpath, "Help.png"), wx.BITMAP_TYPE_PNG).ConvertToBitmap()
		
		tb.DoAddTool(MenuManager.ID_TOOLBAR_HELP, "Help", bmp, \
						shortHelp = "Help")
		wx.EVT_TOOL(self, MenuManager.ID_TOOLBAR_HELP, self.onToolbarHelp)
		
		#self.visIds.append(MenuManager.ID_VIS_ANIMATOR)
		tb.Realize()
		self.menuManager.setMainToolbar(tb)

	def onToolbarHelp(self, evt):
		"""
		An event handler for the toolbar help button that will launch a help
					 page that depends on what task or visualization mode the user is currently using
		"""
		if self.currentTaskWindow:
			lib.messenger.send(None, "view_help", self.currentTaskWindowName)
		else:
			lib.messenger.send(None, "view_help", scripting.currentVisualizationMode)

	def onSaveDataset(self, *args):
		"""
		Process the dataset
		"""
		lib.messenger.send(None, "clear_cache_dataunits")
		if self.currentTaskWindow:
			do_cmd = "mainWindow.processDataset(modal = 0)"
			cmd = lib.Command.Command(lib.Command.VISUALIZATION_CMD, None, None, do_cmd, "", \
										desc = "Process the dataset with the current task")
			cmd.run(recordOnly = 1)
			self.processDataset()
		else:
			filename = Dialogs.askSaveAsFileName(self, "Save dataset as", "output.bxd", \
													"BioImageXD Dataset (*.bxd)|*.bxd")
			if filename:
				filename = filename.replace("\\", "\\\\")
				
				do_cmd = "mainWindow.saveSelectedDatasets(r'%s')" % filename
				cmd = lib.Command.Command(lib.Command.GUI_CMD, None, None, do_cmd, "", \
											desc = "Save the selected datasets to a BXD file")
				cmd.run()
			
	def saveSelectedDatasets(self, filename):
		"""
		Save the selected datasets into a .bxd file
		"""
		selectedUnits = self.tree.getSelectedDataUnits()
		bxdwriter =  lib.DataSource.BXDDataWriter.BXDDataWriter(filename)
		for dataUnit in selectedUnits:
			chname = dataUnit.getName()
			chname = chname.replace(" ", "_")
			filename = dataUnit.getDataSource().getFileName()
			filenamelist = filename.split(".")
			filebase = os.path.basename(".".join(filenamelist[:-1]))
			# Include also image name if exists (ex. LIF files)
			imagename = "_".join(filenamelist[len(filenamelist)-1].split("_")[1:])
			if len(imagename) > 0:
				filebase = filebase + "_" + imagename
			bxcfilename = bxdwriter.getBXCFileName("%s_%s" % (filebase, chname))
			writer = lib.DataSource.BXCDataWriter.BXCDataWriter(bxcfilename)
			n = dataUnit.getNumberOfTimepoints()
			for i in range(0, n):
				data = dataUnit.getTimepoint(i)
				writer.addImageData(data)
				writer.sync()
			parser = writer.getParser()
			
			dataUnit.getSettings().set("Name", dataUnit.getName())
			dataUnit.getSettings().set("ExcitationWavelength", dataUnit.getExcitationWavelength())
			dataUnit.getSettings().set("EmissionWavelength", dataUnit.getEmissionWavelength())
			dataUnit.updateSettings()
			dataUnit.getSettings().writeTo(parser)
			writer.write()
		
			bxdwriter.addChannelWriter(writer)
		bxdwriter.write()
			
		
	def processDataset(self, modal = 1):
		"""
		send the message to use the current task for processing the data
		"""
		scripting.modal = modal
		lib.messenger.send(None, "process_dataset")

	def onContextHelp(self, evt):
		"""
		Put the app in a context help mode
		"""
		wx.ContextHelp(self)
		
	def createMenu(self):
		"""
		Creates a menu for the window
		"""
		self.menu = wx.MenuBar()
		mgr = self.menuManager
		self.SetMenuBar(self.menu)
		mgr.setMenuBar(self.menu)

		# We create the menu objects
		self.fmenu = mgr.createMenu("file", "&File")
		self.filehistory.UseMenu(self.fmenu)

		mgr.createMenu("edit", "&Edit")
		mgr.createMenu("view", "V&iew")
		#mgr.createMenu("settings", "&Settings")
		mgr.createMenu("processing", "&Tasks")
		mgr.createMenu("visualization", "&Visualization")
		mgr.createMenu("animation", "&Animation")
		mgr.createMenu("annotations", "&Annotations")
		mgr.createMenu("help", "&Help")

		
		##### File menu #####
		mgr.addMenuItem("file", MenuManager.ID_OPEN, "&Open dataset\tCtrl-O", self.onMenuOpen)
		mgr.addMenuItem("file", MenuManager.ID_SAVE_DATASET, "&Save dataset\tCtrl-S", self.onSaveDataset)

		mgr.addMenuItem("file", MenuManager.ID_OPEN_SETTINGS, "&Open settings", self.onMenuOpenSettings)
		mgr.addMenuItem("file", MenuManager.ID_SAVE_SETTINGS, "&Save settings", self.onMenuSaveSettings)

		mgr.addMenuItem("file", MenuManager.ID_SAVE_SNAPSHOT, "&Save snapshot image", self.onSnapshot)
		
		mgr.addSeparator("file")
		mgr.addMenuItem("file", MenuManager.ID_IMPORT_IMAGES, "&Import images\tCtrl-I", self.onMenuImport)

		mgr.createMenu("export", "&Export", place = 0)
		mgr.addSubMenu("file", "export", "&Export images", MenuManager.ID_EXPORT)
		mgr.addMenuItem("export", MenuManager.ID_EXPORT_OMEFILES, "&OME-TIFF dataset series\tCtrl-E", self.onMenuExport)
		mgr.addMenuItem("export", MenuManager.ID_EXPORT_IMAGES, "&Stack of images\tShift-Ctrl-E", self.onMenuExport)
		mgr.addMenuItem("export", MenuManager.ID_EXPORT_VTIFILES, "&VTK dataset series", self.onMenuExport)

		mgr.addSeparator("file")
		#mgr.addMenuItem("file", MenuManager.ID_CLOSE_TASKWIN, "&Close task panel\tCtrl-W", \
		#				"Close the task panel", self.onCloseTaskPanel)
		#mgr.disable(MenuManager.ID_CLOSE_TASKWIN)

		mgr.addMenuItem("file",	MenuManager.ID_FILE_VIEW_TREE, "&View file tree", "Show or hide the file tree", self.onMenuToggleVisibility, check = 1, checked = 1)
		mgr.addMenuItem("file", MenuManager.ID_SELECT_ALL, "Select &all\tCtrl-A", self.onSelectAll)
		mgr.addMenuItem("file", MenuManager.ID_CLOSE_ALL, "&Close all", self.onCloseAll)
		
		mgr.addSeparator("file")
		mgr.addMenuItem("file", wx.ID_EXIT, "&Exit", "Quit BioImageXD", self.quitApp)


		##### Edit menu #####
		if not scripting.TFLag:
			mgr.addMenuItem("edit", MenuManager.ID_UNDO, "&Undo*\tCtrl-Z", self.onMenuUndo)
			mgr.addMenuItem("edit", MenuManager.ID_REDO, "&Redo*\tShift-Ctrl-Z", self.onMenuRedo)
			mgr.addMenuItem("edit", MenuManager.ID_COMMAND_HISTORY, "Command history*", self.onShowCommandHistory)
			mgr.addSeparator("edit")
			mgr.disable(MenuManager.ID_REDO)

		if platform.system() == "Darwin":
			keyCombo = "\tCtrl-, "
		else:
			keyCombo = "\tCtrl-P"
		mgr.addMenuItem("edit", wx.ID_PREFERENCES, "&Preferences" + keyCombo, self.onMenuPreferences)
		#mgr.addMenuItem("edit", MenuManager.ID_VIEW_SCRIPTEDIT, "Script &editor*", "Show the script editor", self.onMenuShowScriptEditor)
		mgr.addSeparator("edit")

		mgr.addMenuItem("edit", MenuManager.ID_IMMEDIATE_RENDER, "&Immediate view panel updating", \
						"Toggle immediate updating of view panel \
							(when settings that affect the visualization change) on or off.", \
						self.onMenuImmediateRender, check = 1, checked = 1)
		mgr.addMenuItem("edit", MenuManager.ID_NO_RENDER, "&No view panel updating", \
						"Toggle view panel updating on or off.", self.onMenuNoRender, check = 1, checked = 0)
		mgr.addMenuItem("edit", MenuManager.ID_MENU_RESAMPLING, "Use &resampled image", self.onResampleData, check = 1, checked = 0)
		mgr.disable(MenuManager.ID_MENU_RESAMPLING)

		##### View menu #####
		mgr.addMenuItem("view", MenuManager.ID_VIEW_TREE, "&File tree", "Show or hide the file tree", \
						self.onMenuToggleVisibility, check = 1, checked = 1)
		mgr.addMenuItem("view", MenuManager.ID_VIEW_INFO, "&Dataset info", \
						"Show or hide information about the dataset", self.onMenuToggleVisibility, check = 1, checked = 1)
		mgr.addMenuItem("view", MenuManager.ID_VIEW_TASKPANEL, "&Task panel", \
						"Show or hide task panel", self.onMenuToggleVisibility, check = 1, checked = 1)
		mgr.disable(MenuManager.ID_VIEW_TASKPANEL)
		mgr.addMenuItem("view", MenuManager.ID_VIEW_CONFIG, "View panel &configuration", \
						"Show or hide the configuration panel", self.onMenuToggleVisibility, check = 1, checked = 1)
		mgr.addSeparator("view")
		
		mgr.addMenuItem("view", MenuManager.ID_VIEW_MAIN_TOOLBAR, "View main toolbar", "Show or hide main toolbar", self.onMenuToggleVisibility, check = 1, checked = 1)
		mgr.addMenuItem("view", MenuManager.ID_VIEW_TOOLBAR, "View panel top toolbar", \
						"Show or hide view panel toolbar", self.onMenuToggleVisibility, check = 1, checked = 1)
		mgr.addMenuItem("view", MenuManager.ID_VIEW_ANNOPANEL, "View panel side toolbar", "Show or hide annotation panel", self.onMenuToggleVisibility, check = 1, checked = 1)
		mgr.addSeparator("view")

		mgr.addMenuItem("view", MenuManager.ID_VIEW_HISTOGRAM, "&Histograms\tAlt-Ctrl-H", \
						"Show or hide channel histograms", self.onMenuToggleVisibility, check = 1, checked = 0)
		
		mgr.addMenuItem("view", MenuManager.ID_VIEW_SHELL, "Python &shell", \
						"Show a python interpreter", self.onMenuToggleVisibility, check = 1, checked = 0)
		mgr.addSeparator("view")


		#mgr.addMenuItem("view", MenuManager.ID_VIEW_MASKSEL, "&Mask selection", \
		#				"Show mask selection dialog", self.onMenuToggleVisibility)
		#mgr.addSeparator("view")

		mgr.addMenuItem("view", MenuManager.ID_HIDE_INFO, "Maximize view panel\tAlt-Enter", \
						"Hide all panels, giving visualizer maximum screen space", self.onMaximizeViewPanel)

		mgr.disable(MenuManager.ID_VIEW_TOOLBAR)
		mgr.disable(MenuManager.ID_VIEW_HISTOGRAM)


		##### Task menu #####
		modules = self.taskPanels.values()
		modules.sort(self.sortModes)
		
		for (moduletype, windowtype, mod) in modules:
			name = mod.getName()
			desc = mod.getDesc()
			shortdesc = mod.getShortDesc()
			tid = self.taskToId[name]
			#tb.DoAddTool(tid, name, bmp, kind = wx.ITEM_CHECK, shortHelp = name)
			mgr.addMenuItem("processing", tid, "&" + shortdesc, desc, self.onMenuShowTaskWindow, check = 1, checked = 0)
			#wx.EVT_TOOL(self, tid, self.onMenuShowTaskWindow)
			
		mgr.addSeparator("processing")
		mgr.addMenuItem("processing", MenuManager.ID_BATCHPROCESSOR, "&Batch processor\tCtrl-B",
						"Open batch processing tool",self.onMenuBatchProcessor)

		mgr.addMenuItem("processing", MenuManager.ID_RESAMPLE, "Re&size dataset\tCtrl-R", \
						"Resample data to a different resolution", self.onMenuResampleData)
		mgr.addMenuItem("processing", MenuManager.ID_RESCALE, "Con&vert to 8-bit\tCtrl-Shift-R", \
						"Rescale data to 8-bit intensity range", self.onMenuRescaleData)
		
		
		##### Visualization menu #####
		modes = self.visualizationModes.values()
		modes.sort(self.sortModes)

		animMod = None
		for (mod, settingclass, module) in modes:
			name = module.getName()
			if name == "animator":
				animMod = module
				continue
			vid = self.visToId[name] 
			sdesc = module.getShortDesc()
			desc = module.getDesc()
			# Visualization modes that do not wish to be in the menu can return None as the desc
			if not desc:
				continue
			mgr.addMenuItem("visualization", vid, "&" + sdesc, desc, check = 1, checked = 0)

		if not scripting.TFLag:
			mgr.addSeparator("visualization")
			mgr.addMenuItem("visualization", MenuManager.ID_LIGHTS, "&Lights...*\tCtrl-L", "Configure lighting")
			mgr.disable(MenuManager.ID_LIGHTS)
			#mgr.addMenuItem("visualization", MenuManager.ID_RENDERWIN, "&Render window", "Configure Render Window")
			#mgr.disable(MenuManager.ID_RENDERWIN)


		##### Animation menu #####
		#mgr.createMenu("track", "&Track", before = "help")
		#mgr.createMenu("rendering","&Rendering",before="help")
		#mgr.createMenu("camera","&Camera",before="help")

		mgr.addMenuItem("animation", self.visToId["animator"], "&Animator mode", check = 1, checked = 0)
		mgr.addSeparator("animation")
		
		mgr.addMenuItem("animation", MenuManager.ID_OPEN_PROJECT, "Open project", "Open a BioImageXD Animator Project")
		mgr.addMenuItem("animation", MenuManager.ID_SAVE_PROJECT, "Save project", "Save current BioImageXD Animator Project")
		mgr.addMenuItem("animation", MenuManager.ID_CLOSE_PROJECT, "Close project", "Close this Animator Project")
		mgr.addSeparator("animation")

		mgr.createMenu("addtrack", "&Add track", place = 0)
		mgr.addSubMenu("animation", "addtrack", "&Add track", MenuManager.ID_ADD_TRACK)
		mgr.addMenuItem("addtrack", MenuManager.ID_ADD_TIMEPOINT, "Timepoint track", "Add a timepoint track to the timeline")
		mgr.addMenuItem("addtrack", MenuManager.ID_ADD_SPLINE, "Camera path track", "Add a camera path track to the timeline")
		mgr.addMenuItem("addtrack", MenuManager.ID_ADD_KEYFRAME, "Keyframe track", "Add a keyframe track to the timeline")
		
		mgr.createMenu("sizetrack", "&Item sizes", place = 0)
		mgr.addSubMenu("animation", "sizetrack", "&Item sizes", MenuManager.ID_ITEM_SIZES)
		
		mgr.addMenuItem("sizetrack", MenuManager.ID_FIT_TRACK, "Expand to maximum", "Expand the track to encompass the whole timeline")
		mgr.addMenuItem("sizetrack", MenuManager.ID_FIT_TRACK_RATIO, "Expand to track length (keep ratio)", "Expand the track to encompass the whole timeline while retainining the relative sizes of each item.")
		mgr.addMenuItem("sizetrack", MenuManager.ID_MIN_TRACK, "Shrink to minimum", "Shrink the track to as small as possible")
		mgr.addMenuItem("sizetrack", MenuManager.ID_SET_TRACK, "Set item size", "Set each item on this track to be of given size")
		mgr.addMenuItem("sizetrack", MenuManager.ID_SET_TRACK_TOTAL, "Set total length", "Set total length of items on this track")
		mgr.addMenuItem("sizetrack", MenuManager.ID_SET_TRACK_RELATIVE, "Set to physical length", "Set the length of items on this track to be relative to their physical length")

		mgr.createMenu("shuffle", "&Shift items", place = 0)
		mgr.addSubMenu("animation", "shuffle", "Shift items", MenuManager.ID_ITEM_ORDER)
		mgr.addMenuItem("shuffle", MenuManager.ID_ITEM_ROTATE_CW, "&Left")
		mgr.addMenuItem("shuffle", MenuManager.ID_ITEM_ROTATE_CCW, "&Right")

		mgr.addSeparator("animation")
		mgr.addMenuItem("animation", MenuManager.ID_DELETE_TRACK, "&Remove track", "Remove the track from timeline")
		mgr.addMenuItem("animation", MenuManager.ID_DELETE_ITEM, "&Remove item", "Remove the selected track item")
	
		mgr.addSeparator("animation")
		mgr.addMenuItem("animation", MenuManager.ID_SPLINE_SET_BEGIN, "&Begin at the end of previous path", "Set this camera path to begin where the previous path ends")
		mgr.addMenuItem("animation", MenuManager.ID_SPLINE_SET_END, "&End at the beginning of next path", "Set this camera path to end where the next path starts")

		mgr.addSeparator("animation")
		mgr.addMenuItem("animation", MenuManager.ID_SPLINE_CLOSED, "&Closed path", "Set the camera path to open / closed.", check = 1)
		mgr.addMenuItem("animation", MenuManager.ID_MAINTAIN_UP, "&Maintain up direction", check = 1)

		mgr.disable(MenuManager.ID_OPEN_PROJECT)
		mgr.disable(MenuManager.ID_SAVE_PROJECT)
		mgr.disable(MenuManager.ID_CLOSE_PROJECT)
		mgr.disable(MenuManager.ID_ADD_TIMEPOINT)
		mgr.disable(MenuManager.ID_ADD_SPLINE)
		mgr.disable(MenuManager.ID_ADD_KEYFRAME)
		mgr.disable(MenuManager.ID_FIT_TRACK)
		mgr.disable(MenuManager.ID_FIT_TRACK_RATIO)
		mgr.disable(MenuManager.ID_MIN_TRACK)
		mgr.disable(MenuManager.ID_SET_TRACK)
		mgr.disable(MenuManager.ID_SET_TRACK_TOTAL)
		mgr.disable(MenuManager.ID_SET_TRACK_RELATIVE)
		mgr.disable(MenuManager.ID_ITEM_ROTATE_CW)
		mgr.disable(MenuManager.ID_ITEM_ROTATE_CCW)
		mgr.disable(MenuManager.ID_DELETE_TRACK)
		mgr.disable(MenuManager.ID_DELETE_ITEM)
		mgr.disable(MenuManager.ID_SPLINE_SET_BEGIN)
		mgr.disable(MenuManager.ID_SPLINE_SET_END)
		mgr.disable(MenuManager.ID_SPLINE_CLOSED)
		mgr.disable(MenuManager.ID_MAINTAIN_UP)
		

		##### Annotations menu #####
		mgr.addMenuItem("annotations", MenuManager.ID_MENU_ROI_CIRCLE, "Draw &circle ROI", "", self.onAddAnnotation)
		mgr.addMenuItem("annotations", MenuManager.ID_MENU_ROI_RECTANGLE, "Draw &rectangle ROI", "", self.onAddAnnotation)
		mgr.addMenuItem("annotations", MenuManager.ID_MENU_ROI_POLYGON, "Draw &polygon ROI", "", self.onAddAnnotation)
		mgr.addMenuItem("annotations", MenuManager.ID_MENU_ADD_SCALE, "Draw &scale bar", "", self.onAddAnnotation)

		mgr.addSeparator("annotations")
		mgr.addMenuItem("annotations", MenuManager.ID_MENU_DEL_ANNOTATION, "&Delete annotation\t Del", "", self.onDeleteAnnotation)
		mgr.addMenuItem("annotations", MenuManager.ID_MENU_CHANGE_COLOR, "Change &annotation color", "", self.onMenuHelp)

		mgr.addSeparator("annotations")
		mgr.addMenuItem("annotations", MenuManager.ID_MENU_ROI_TO_MASK, "Convert ROI &to mask", "", self.onRoiToMask)
		mgr.addMenuItem("annotations", MenuManager.ID_VIEW_MASKSEL, "&Mask selection", "Show mask selection dialog", self.onMenuToggleVisibility)

		##### Help menu #####
		mgr.addMenuItem("help", wx.ID_ABOUT, "&About", "About BioImageXD", self.onMenuAbout)
		#mgr.addSeparator("help")
		mgr.addMenuItem("help", wx.ID_HELP, "&Help", "Online Help", self.onMenuHelp)
		mgr.addMenuItem("help", MenuManager.ID_REPORT_BUG, "&Report bug", "Send a bug report", self.onMenuBugReport)
		#mgr.addSeparator("help")
		#mgr.addMenuItem("help", MenuManager.ID_CONTEXT_HELP, "&Context help\tF1", \
		#				"Show help on current task or visualization mode", self.onToolbarHelp)
	
#        if platform.system() =="Darwin":
#            wx.App_SetMacHelpMenuTitleName("&Help")
			
	def createStatusBar(self):
		"""
		Creates a status bar for the window
		"""
		self.statusbar = wx.StatusBar(self)
		self.SetStatusBar(self.statusbar)
		self.statusbar.SetFieldsCount(3)
		self.statusbar.SetStatusWidths([-3, -2, -2])
		self.progress = wx.Gauge(self.statusbar)
		self.progress.SetRange(100)
		self.progress.SetValue(100)
		
		col = self.statusbar.GetBackgroundColour()
		rect = self.statusbar.GetFieldRect(1)

		self.colorLbl = UIElements.NamePanel(self.statusbar, "", col, size = (rect.width - 4, rect.height - 4))
		self.colorLbl.SetPosition((rect.x + 2, rect.y + 2))
		lib.messenger.connect(None, "update_progress", self.updateProgressBar)
		lib.messenger.connect(None, "report_progress_only", self.onSetProgressObject)
		
	def onSetProgressObject(self, obj, evt, arg):
		"""
		Set the object that is allowed to send progress updates
		"""
		if not arg and self.progressObject:
			lib.messenger.disconnect(self.progressObject, "update_progress")
		self.progressObject = arg
		lib.messenger.connect(self.progressObject, "update_progress", self.updateProgressBar)
		
	
	def onShowCommandHistory(self, evt = None):
		"""
		Show the command history
		"""
		# Use a clever contraption in where if we're called from the menu
		# then we create a command object that will call us, but with an
		# empty argument that will trigger the actual dialog to show
		if evt:
			if "show_history" not in self.commands:
				do_cmd = "mainWindow.onShowCommandHistory()"
				undo_cmd = "mainWindow.commandHistory.Destroy()\nmainWindow.commandHistory = None"
				
				cmd = lib.Command.Command(lib.Command.MENU_CMD, None, None, do_cmd, undo_cmd, \
											desc = "Show command history")
				self.commands["show_history"] = cmd
			self.commands["show_history"].run()
		else:
			if not self.commandHistory:
				self.commandHistory = UndoListBox.CommandHistory(self, self.menuManager)
			
			self.commandHistory.update()
			self.commandHistory.Show()
			
	def onMenuBatchProcessor(self, evt):
		"""
		show the batch processor tool
		"""
		self.batchProcessor = BatchProcessor.BatchProcessor(self)
		scripting.registerDialog("BatchProcessor", self.batchProcessor)
		selectedFiles = self.tree.getSelectedDataUnits()
		self.batchProcessor.setInputDataUnits(selectedFiles)
		self.batchProcessor.Show()
		

	def onMenuBugReport(self, evt):
		"""
		Show a dialog for sending a bug report to the developers
		"""
		dlg = BugDialog.BugDialog(self)
		dlg.ShowModal()
		dlg.Destroy()

	def onMenuImmediateRender(self, evt):
		"""
		Toggle immediate render updates on or off
		"""
		flag = evt.IsChecked()
		self.visualizer.setImmediateRender(flag)

	def onMenuNoRender(self, evt):
		"""
		Toggle immediate render updates on or off
		"""
		flag = evt.IsChecked()
		if flag:
			self.menuManager.disable(MenuManager.ID_IMMEDIATE_RENDER)
		else:
			self.menuManager.enable(MenuManager.ID_IMMEDIATE_RENDER)
		self.visualizer.setNoRendering(flag)
		
	def onMenuShowScriptEditor(self, evt):
		"""
		Show the script editor
		"""
		if scripting.record:
			self.scriptEditor.Show()
		else:
			self.scriptEditor = ScriptEditor.ScriptEditorFrame(self)
			self.scriptEditor.Show()

		
	def onMenuHideInfo(self, evt):
		"""
		Hide info windows, giving visualizer maximum screen estate
		"""
		gts = self.GetToolBar().GetToolState
		status = not (gts(MenuManager.ID_SHOW_TREE) or self.menuManager.isChecked(MenuManager.ID_VIEW_INFO))

		self.GetToolBar().ToggleTool(MenuManager.ID_SHOW_TREE, status)
		self.menuManager.check(MenuManager.ID_VIEW_INFO, status)
		
		if not status:
			self.infoWin.SetDefaultSize((0, 0))
		else:
			self.infoWin.SetDefaultSize(self.infoWin.origSize)

		self.onMenuShowTree(status)

	def onMaximizeViewPanel(self, evt):
		"""
		Maximize view panel
		"""
		mgr = self.menuManager
		self.toggleVisibility(MenuManager.ID_VIEW_TREE, False)
		mgr.check(MenuManager.ID_VIEW_TREE, False)
		self.toggleVisibility(MenuManager.ID_VIEW_INFO, False)
		mgr.check(MenuManager.ID_VIEW_INFO, False)
		self.toggleVisibility(MenuManager.ID_VIEW_CONFIG, False)
		mgr.check(MenuManager.ID_VIEW_CONFIG, False)
		self.toggleVisibility(MenuManager.ID_VIEW_TASKPANEL, False)
		mgr.check(MenuManager.ID_VIEW_TASKPANEL, False)
		self.toggleVisibility(MenuManager.ID_VIEW_SHELL, False)
		mgr.check(MenuManager.ID_VIEW_SHELL, False)
		self.toggleVisibility(MenuManager.ID_VIEW_HISTOGRAM, False)
		mgr.check(MenuManager.ID_VIEW_HISTOGRAM, False)
		self.toggleVisibility(MenuManager.ID_VIEW_ANNOPANEL, False)
		mgr.check(MenuManager.ID_VIEW_ANNOPANEL, False)
		self.toggleVisibility(MenuManager.ID_VIEW_TOOLBAR, False)
		mgr.check(MenuManager.ID_VIEW_TOOLBAR, False)

	def onMenuResampleData(self, evt):
		"""
		Resize data to be smaller or larger
		"""
		selectedFiles, items = self.tree.getSelectionContainer()
		if not selectedFiles:
			return
		dlg = ResampleDialog.ResampleDialog(self)
		dlg.setDataUnits(selectedFiles)
		dlg.ShowModal()
		if dlg.result == 1:
			self.tree.markRed(items, "*")
			mode = self.visualizer.mode
			unit = self.visualizer.dataUnit
			self.closeVisualizer()
			self.loadVisualizer(mode, dataunit = unit)
			self.visualizer.resamplingBtn.SetToggle(True)
			self.visualizer.resamplingBtn.Enable(1)
			self.menuManager.check(MenuManager.ID_MENU_RESAMPLING, True)
			self.menuManager.enable(MenuManager.ID_MENU_RESAMPLING)
			self.infoWidget.updateInfo(None, None, None)
			self.visualizer.updateRendering()
		
	def onMenuRescaleData(self, evt):
		"""
		Rescale data to 8-bit intensity range
		"""
		selectedFiles, items = self.tree.getSelectionContainer()
		if not selectedFiles:
			return

		conf = Configuration.getConfiguration()
		autoRescale = conf.getConfigItem("AutoRescaleMapping", "Performance")
		if autoRescale:
			autoRescale = eval(autoRescale)

		if autoRescale:
			lib.ImageOperations.rescaleDataUnits(selectedFiles,0,255)
			wid = wx.ID_OK
		else:
			dlg = RescaleDialog.RescaleDialog(self)
			dlg.setDataUnits(selectedFiles)
			wid = dlg.ShowModal()
			dlg.zoomToFit()
			dlg.Destroy()
		
		if wid == wx.ID_OK:
			self.tree.markBlue(items, "#")
			self.infoWidget.updateInfo(None, None, None)
			mode = self.visualizer.mode
			unit = self.visualizer.dataUnit
			self.closeVisualizer()
			self.loadVisualizer(mode, dataunit = unit)
			self.infoWidget.showInfo(selectedFiles[0])

	
	def onMenuToggleVisibility(self, evt):
		"""
		A callback function for toggling the visibility of different UI elements
		"""
		eid = evt.GetId()
		flag = evt.IsChecked()
		self.toggleVisibility(eid,flag)

	def toggleVisibility(self,eid,flag):
		"""
		Toggle visibility of different UI elements
		"""
		cmd = "hide"
		if flag:
			cmd = "show"
		
		if eid == MenuManager.ID_VIEW_CONFIG:
			obj = "config"
		elif eid == MenuManager.ID_VIEW_TREE or eid == MenuManager.ID_FILE_VIEW_TREE:
			self.onMenuShowTree(show = flag)
			return
		elif eid == MenuManager.ID_VIEW_MASKSEL:
			if self.visualizer:
				masksel = MaskTray.MaskTray(self)
				dataUnit = self.visualizer.getDataUnit()
				masks = self.visualizer.getMasks()
				for mask in masks:
					masksel.addMask(mask = mask)
				masksel.setDataUnit(dataUnit)
				masksel.Show()
				return
		elif eid == MenuManager.ID_VIEW_TOOLBAR:
			obj = "toolbar"
		elif eid == MenuManager.ID_VIEW_HISTOGRAM:
			obj = "histogram"
		elif eid in [MenuManager.ID_VIEW_INFO, MenuManager.ID_VIEW_TASKPANEL]:
			if eid == MenuManager.ID_VIEW_INFO:
				win = self.infoWin
			else:
				win = self.taskWin
			
			if cmd == "hide":
				win.origSize = win.GetSize()
				win.SetDefaultSize((0, 0))
			else:
				win.SetDefaultSize(win.origSize)

			self.OnSize(None)
			self.visualizer.OnSize(None)
			return
		elif eid == MenuManager.ID_VIEW_SHELL:
			if cmd == "hide":
				self.shellWin.origSize = self.shellWin.GetSize()
				self.shellWin.SetDefaultSize((0, 0))
			else:
				if not self.shell:
					intro = 'BioImageXD interactive interpreter v0.1'
					self.shell = py.shell.Shell(self.shellWin, -1, introText = intro)
				self.shellWin.SetDefaultSize(self.shellWin.origSize)
			self.OnSize(None)
			self.visualizer.OnSize(None)
			return
		elif eid == MenuManager.ID_VIEW_ANNOPANEL:
			obj = "annotation"
		elif eid == MenuManager.ID_VIEW_MAIN_TOOLBAR:
			tb = self.GetToolBar()
			if cmd == "hide":
				tb.Destroy()
				self.taskIds = []
				self.visIds = []
			else:
				self.createToolBar()
			self.OnSize(None)
			self.visualizer.OnSize(None)
			return

		lib.messenger.send(None, cmd, obj)
		
	def onCloseTaskPanel(self, event):
		"""
		Called when the user wants to close the task panel
		"""
		undo_cmd = ""
		do_cmd = "mainWindow.closeTaskPanel()"
		cmd = lib.Command.Command(lib.Command.MGMT_CMD, None, None, do_cmd, undo_cmd, \
									desc = "Close the current task panel")
		cmd.run()
		
	def getCurrentTaskName(self):
		"""
		return the name of the current task
		"""
		return self.currentTaskWindowName

	def closeTaskPanel(self):
		"""
		A method that actually closes the task panel
		"""
		if self.currentTaskWindow:
			self.currentTaskWindow.removeFilters()
			self.currentTaskWindow.cacheSettings()
		selectedUnits = self.tree.getSelectedDataUnits()
		self.visualizer.enable(0)
		Logging.info("Setting processed mode = 0")
		self.visualizer.setProcessedMode(0)
		self.menuManager.clearItemsBar()

		if self.currentTaskWindow:
			Logging.info("Closing task")
			self.currentTaskWindow.deregister()
			self.currentTaskWindow.Show(0)
			self.currentTaskWindow.Destroy()
			del self.currentTaskWindow
			self.currentTaskWindow = None
			self.currentTaskWindowName = ""
			self.currentTaskWindowType = None

		Logging.info("Switching dataunit")
		self.visualizer.setDataUnit(selectedUnits[0])
		self.visualizer.enable(1)
		
		self.switchBtn.Enable(0)
		#self.menuManager.disable(MenuManager.ID_CLOSE_TASKWIN)
		self.taskWin.SetDefaultSize((0, 0))
		
		tb = self.GetToolBar()
		for eid in self.taskIds:
			tb.ToggleTool(eid, 0)
		# Set the dataunit used by visualizer to one of the source units
		
		self.infoWin.SetDefaultSize(self.infoWin.origSize)
		self.menuManager.check(MenuManager.ID_VIEW_INFO, 1)
		
		wx.LayoutAlgorithm().LayoutWindow(self, self.visWin)
		self.visWin.Refresh()
		
	
	def onMenuImport(self, evt, startFile = ""):
		"""
		Callback function for menu item "Import"
		"""
		import_code = """
importdlg = GUI.ImportDialog.ImportDialog(mainWindow)
		"""
		if startFile:
			import_code += "importdlg.setInputFile('%s')\n" % startFile
		import_code += "if importdlg.ShowModal() == wx.ID_OK: mainWindow.openFile( importdlg.getDatasetName() )\n"
		command = lib.Command.Command(lib.Command.MENU_CMD, None, None, import_code, "", \
										imports = ["GUI.ImportDialog","wx"], desc = "Show import dialog")
		self.commands["show_import"] = command
		self.commands["show_import"].run()
		#self.importdlg = ImportDialog.ImportDialog(self)
		#self.importdlg.ShowModal()
		
		
	def onMenuExport(self, evt):
		"""
		Callback function for menu item "Export"
		"""
		selectedFiles = self.tree.getSelectedDataUnits()
		if len(selectedFiles) > 1:
			dataunit = selectedFiles[0]
			dims1 = dataunit.getDimensions()
			tps1 = dataunit.getNumberOfTimepoints()
			vs1 = dataunit.getSettings().get("VoxelSize")
			bd1 = dataunit.getSettings().get("BitDepth")
			for dataunit in selectedFiles:
				dims2 = dataunit.getDimensions()
				tps2 = dataunit.getNumberOfTimepoints()
				vs2 = dataunit.getSettings().get("VoxelSize")
				bd2 = dataunit.getSettings().get("BitDepth")
				if dims1 != dims2 or tps1 != tps2 or vs1 != vs2 or bd1 != bd2:
					Dialogs.showerror(self, "You can only export dataunits that have same spatial and temporal dimensions, voxel size and bit depth", "Cannot export selected datasets")
					return
		elif len(selectedFiles) < 1:
			Dialogs.showerror(self, "You need to select a dataunit to be exported.", "Select dataunit to be exported")
			return
		eid = evt.GetId()
		imageMode = 0
		if eid == MenuManager.ID_EXPORT_IMAGES:
			imageMode = 1
		elif eid == MenuManager.ID_EXPORT_VTIFILES:
			imageMode = 2
		self.exportdlg = ExportDialog.ExportDialog(self, selectedFiles, imageMode)
		
		self.exportdlg.ShowModal()
		
	
	def onMenuPreferences(self, evt):
		"""
		Callback function for menu item "Preferences"
		"""
		self.settingswindow = SettingsWindow.SettingsWindow(self)
		self.settingswindow.Show()

	def onMenuVisualizer(self, evt):
		"""
		Callback function for launching the visualizer
		"""
		# Hide the infowin and toggle the menu item accordingly
		eid = evt.GetId()
		mode = ""
		for name, vid in self.visToId.items():
			if vid == eid:
				mode = name
				break
		if not name:
			raise "Did not find a visualization mode corresponding to id ", eid
		
		# Double buffering is only needed in slices mode and can cause troubles in 3d in Windows
		if mode == 'slices':
			self.visWin.SetDoubleBuffered(True)
		else:
			self.visWin.SetDoubleBuffered(False)
			
		do_cmd = "mainWindow.loadVisualizerMode('%s')" % (mode)
		if scripting.currentVisualizationMode in self.visToId:
			undo_cmd = "mainWindow.loadVisualizerMode('%s')" % (scripting.currentVisualizationMode)
		else:
			undo_cmd = ""
		cmd = lib.Command.Command(lib.Command.GUI_CMD, None, None, do_cmd, undo_cmd, \
									desc = "Switch to visualizer mode %s" % mode)
		cmd.run()
		
	def loadVisualizerMode(self, mode):
		"""
		Load the visualizer mode with the given name
		"""
		eid = self.visToId[mode]
		if scripting.currentVisualizationMode == mode:
			# If the user re-clicks on the icon, then close it (same as tasks) and load slices mode
			unit = self.visualizer.dataUnit
			self.closeVisualizer()
			self.infoWin.SetDefaultSize(self.infoWin.origSize)
			self.loadVisualizer(self.defaultModeName, dataunit = unit)
			return

		scripting.currentVisualizationMode = mode
		lib.messenger.send(None, "update_progress", 0.1, "Loading %s view..." % mode)

		modeclass, settingclass, module = self.visualizationModes[mode]
		needUpdate = 0
		if not module.showFileTree():
			self.onMenuShowTree(show = False)
			needUpdate = 1
		if not module.showInfoWindow():
			self.infoWin.SetDefaultSize((0, 0))
			needUpdate = 1
		if needUpdate:
			self.OnSize(None)
			
		# If a visualizer is already running, just switch the mode
		selectedFiles = self.tree.getSelectedDataUnits()
		if (not len(selectedFiles)) and mode != "3d" and mode != "animator":
			Dialogs.showerror(self, "You need to select a dataset to load in the visualizer.", \
								"Please select a dataset")
			return

		if len(selectedFiles) > 1 and self.currentTaskWindow is None and (mode == "3d" or mode == "animator"): # Group files automatically if no task is open
			self.tree.onGroupDataset(None)
			selectedFiles = self.tree.getSelectedDataUnits()
		
		# If we open 3D then there is not necessary any open files when we use
		# pdb reader or tracking visualizer
		if len(selectedFiles) == 0:
			selectedFiles.append(None)
		self.setButtonSelection(eid)
		self.setVisualizerMenuSelection(eid)

		dataunit = selectedFiles[0]
		if self.visualizer:
			hasDataunit = bool(self.visualizer.dataUnit)
			if hasDataunit and dataunit.getDataUnitCount() == self.visualizer.dataUnit.getDataUnitCount():
				dataunit = self.visualizer.dataUnit
			didSetDataUnit = False
			self.visualizer.enable(False)
			if not self.visualizer.getProcessedMode() and dataunit:
				Logging.info("Setting dataunit for visualizer", kw = "main")
				self.visualizer.setDataUnit(dataunit)
				didSetDataUnit = True
			
			self.visualizer.setVisualizationMode(mode)
			lib.messenger.send(None, "update_progress", 0.3, "Loading %s view..." % mode)
			self.showVisualization(self.visPanel)
			self.visualizer.enable(True)
#			if not didSetDataUnit:
#				self.visualizer.setDataUnit(dataunit)
			#if hasDataunit:
			#	Logging.info("Forcing visualizer update since dataunit has been changed", kw = "visualizer")
			self.visualizer.updateRendering()
			lib.messenger.send(None, "update_progress", 1.0, "Loading %s view..." % mode, 0)
			return
		
		if len(selectedFiles) > 1:
			lst = [i.getName() for i in selectedFiles]

			Dialogs.showerror(self,
			"You have selected the following datasets: %s.\n"
			"More than one dataset cannot be opened in the Visualizer concurrently.\nPlease "
			"select only one dataset or use the Merge tool." % (", ".join(lst)),
			"Multiple datasets selected")
			return
		
		if len(selectedFiles) < 1:
			Dialogs.showerror(self,
			"You have not selected a dataset to be loaded to Visualizer.\nPlease "
			"select a dataset and try again.\n", "No dataset selected")
			return
			
		dataunit = selectedFiles[0]
		lib.messenger.send(None, "update_progress", 0.5, "Loading %s view..." % mode)
		self.loadVisualizer(mode, 0, dataunit = dataunit)
		
	def onMenuOpenSettings(self, event):
		"""
		Callback function for menu item "Load settings"
		"""
		if self.visualizer:
			dataunit = self.visualizer.getDataUnit()
			if dataunit:
				name = dataunit.getName()
				filenames = Dialogs.askOpenFileName(self, "Open settings for %s" % name, "Settings (*.bxp)|*.bxp")
				if not filenames:
					Logging.info("Got no name for settings file", kw = "dataunit")
					return
				filenames = filenames[0]
				Logging.info("Loading settings for dataset", name, " from ", filenames, kw = "dataunit")

				do_cmd = "mainWindow.loadSettings(\"%s\")" % filenames
			
				cmd = lib.Command.Command(lib.Command.OPEN_CMD, None, None, do_cmd, "", \
											desc = "Load settings file %s" % filenames)
				cmd.run()
				
			else:
				Logging.info("No dataunit, cannot load settings")
				
	def loadSettings(self, filenames):
		"""
		Load settings from given filename
		"""
		dataunit = self.visualizer.getDataUnit()
		parser = ConfigParser.RawConfigParser()
		parser.optionxform = str
		parser.read(filenames)
		dataunit.getSettings().readFrom(parser)
		dataunit.parser = parser
		lib.messenger.send(None, "update_settings_gui")

	def onMenuSaveSettings(self, event):
		"""
		Callback function for menu item "Save settings"
		"""
		if self.visualizer:
			dataunit = self.visualizer.getDataUnit()
			if dataunit:
				name = dataunit.getName()
				filename = Dialogs.askSaveAsFileName(self, "Save settings of %s as" % name, \
													"settings.bxp", "Settings (*.bxd)|*.bxp")
		
				if not filename:
					Logging.info("Got no name for settings file", kw = "dataunit")
					return
				Logging.info("Saving settings of dataset", name, " to ", filename, kw = "dataunit")
				if dataunit.isProcessed():
					dataunit.doProcessing(filename, settings_only = 1)
			else:
				Logging.info("No dataunit, cannot save settings")
		
	def onMenuOpen(self, evt, evt2 = None, *args):
		"""
		Callback function for menu item "Open dataset"
		"""
		if not evt2:
			self.onMenuShowTree(show = True)
			asklist = []
			wc = self.datasetWildcards + "|Encoding project (*.bxr)|*.bxr"
			asklist = Dialogs.askOpenFileName(self, "Open a volume dataset", wc)
		else:
			asklist = args
		
		for askfile in asklist:
			sep = askfile.split(".")[-1]
			if sep.lower() == "bxr":
				do_cmd = 'mainWindow.loadEncodingProject(ur"%s")' % (askfile)
				fname = os.path.split(askfile)[-1]

				cmd = lib.Command.Command(lib.Command.OPEN_CMD, None, None, do_cmd, "", \
											desc = "Load encoding project %s" % fname)
				cmd.run()		
				continue

			if sep.lower() in ["tif", "tiff", "jpg", "jpeg", "png","bmp"]:
				sep2 = askfile.split(".")[-2]
				if sep2.lower() == "ome":
					pass
				else:
					self.onMenuImport(None, askfile)
					return
			
			fname = os.path.split(askfile)[-1]
			self.SetStatusText("Loading " + fname + "...")
			askfile = askfile.replace("\\", "\\\\")
			askfile = askfile.replace("'", "\\'")
			do_cmd = "mainWindow.createDataUnit(u'%s', u'%s')" % (fname, askfile)
			
			cmd = lib.Command.Command(lib.Command.OPEN_CMD, None, None, do_cmd, "", \
										desc = "Load dataset %s" % fname)
			cmd.run()
		self.SetStatusText("Done.")
		
	def loadEncodingProject(self, filename):
		"""
		present a GUI for re-encoding an encoding project file
		"""
		import GUI.Urmas.VideoGeneration

		dlg = GUI.Urmas.VideoGeneration.VideoGenerationDialog(self, filename)
		dlg.disableFrameDeletion()
		dlg.ShowModal()
		dlg.Destroy()
		scripting.videoGeneration = None

	def openFile(self, filepath):
		"""
		Open a file extracting the dataset name from the filename
		"""
		self.createDataUnit(os.path.basename(filepath), filepath)
		
	def createDataUnit(self, name, path, noWarn = 0):
		"""
		Creates a dataunit with the given name and path
		Parameters:
			name    Name used to identify this dataunit
			path    Path to the file this dataunit points to
		"""
		ext = path.split(".")[-1]
		self.filehistory.AddFileToHistory(path)
		dataunit = None
		if self.tree.hasItem(path):
			return
		
		ext = ext.lower()
		if ext in ["tif", "tiff"]:
			ext2 = path.split(".")[-2].lower()
			if ext2 == "ome":
				ext = "ome."+ext

		if ext not in self.extToSource.keys():
			return
		# We try to load the actual data
		Logging.info("Loading dataset with extension %s, path=%s" % (ext, path), kw = "io")
		datasource = self.extToSource[ext]()
		try:
			datasource = self.extToSource[ext]()
		except KeyError:
			if not noWarn:
				Dialogs.showerror(self, "Failed to load file %s: Unrecognized extension %s" % (name, ext), \
									"Unrecognized extension")
			return
		dataunits = []

		try:
			dataunits = datasource.loadFromFile(path)
			Logging.info("Loaded from file %s %d dataunits" % (path, len(dataunits)), kw = "io")
		except Logging.GUIError, ex:
			if not noWarn:
				ex.show()

		if not dataunits:
			if not noWarn:
				Dialogs.showerror(self, "Failed to read dataset %s." % path, "Failed to read dataset")
			return

		Logging.info("Got %d dataunits"%len(dataunits), kw="io")
		# We might get tuples from leica
		d = GUI.TreeWidget.OrderedDict()
		self.visualizer.enable(0)
		if type(dataunits[0]) == types.TupleType:
			for (name, unit) in dataunits:
				if d.has_key(name):
					d[name].append(unit)
				else:
					d[name] = [unit]
			for key in d.keys():
				Logging.info("Adding dataunit %s %s %s" % (key, path, ext), kw = "io")
				self.tree.addToTree(key, path, ext, d[key])
		else:
			# If we got data, add corresponding nodes to tree
			#Logging.info("Adding to tree ", name, path, ext, dataunits, kw = "io")
			bitness = max([x.getSingleComponentBitDepth() for x in dataunits])
			
			conf = Configuration.getConfiguration()
			wantToRescale = conf.getConfigItem("RescaleOnLoading", "Performance")
			if wantToRescale:
				wantToRescale = eval(wantToRescale)
			autoRescale = conf.getConfigItem("AutoRescaleMapping", "Performance")
			if autoRescale:
				autoRescale = eval(autoRescale)

			if wantToRescale and bitness > 8:
				if autoRescale:
					lib.ImageOperations.rescaleDataUnits(dataunits, 0, 255)
				else:
					dlg = RescaleDialog.RescaleDialog(self)
					dlg.setDataUnits(dataunits)
					wid = dlg.ShowModal()
					dlg.zoomToFit()
					if wid != wx.ID_OK:
						del dataunits
						dlg.Destroy()
						return
					dlg.Destroy()

			self.tree.addToTree(name, path, ext, dataunits)
		self.visualizer.enable(1)

	def onMenuShowTaskWindow(self, event):
		"""
		A method that shows a taskwindow of given type
		"""
		eid = event.GetId()
		tb = self.GetToolBar()
		shown = tb.GetToolState(eid)
		
		taskname = ""
		for name, taskid in self.taskToId.items():
			if taskid == eid:
				taskname = name
				break
		if not taskname:
			raise "Couldn't find a task corresponding to id ", eid

		if taskname == self.currentTaskWindowName:
			if taskname == "Process":
				lib.messenger.send(None, "enable_dataunits_cache", False)
			Logging.info("Task", taskname, "already showing, will close", kw = "task")
			tb.ToggleTool(eid, 0)
			self.onCloseTaskPanel(None)
			self.menuManager.check(self.taskToId[taskname], False)
			return
		
		do_cmd = 'mainWindow.loadTask("%s")' % (taskname)
		if self.currentTaskWindowName:
			undo_cmd = 'mainWindow.loadTask("%s")' % (self.currentTaskWindowName)
		else:
			undo_cmd = 'mainWindow.closeTask()'
		cmd = lib.Command.Command(lib.Command.TASK_CMD, None, None, do_cmd, undo_cmd, \
									desc = "Load task %s" % taskname)
		cmd.run()

		# Set mark on right menu item
		for name, taskid in self.taskToId.items():
			if name == taskname:
				self.menuManager.check(taskid, True)
			else:
				self.menuManager.check(taskid, False)
		
	def closeTask(self):
		"""
		Close the current task window
		"""   
		self.onCloseTaskPanel(None)
		self.onMenuShowTree(show = True)

			
	def loadTask(self, taskname):
		"""
		Load the task with the given name
		"""
		moduletype, windowtype, mod = self.taskPanels[taskname]
		filesAtLeast, filesAtMost = mod.getInputLimits()
		
		unittype = mod.getDataUnit()
		action = mod.getName()
		Logging.info("Module type for taskwindow: ", moduletype, kw = "task")
		
		selectedFiles = self.tree.getSelectedDataUnits()
		selectedPaths = self.tree.getSelectedPaths()
		if filesAtLeast != -1 and len(selectedFiles) < filesAtLeast:
			Dialogs.showerror(self,	\
								"You need to select at least %d source datasets for the task: %s" \
									% (filesAtLeast, action), \
								"Need more source datasets")
			self.setButtonSelection(-1)
			return
		elif filesAtMost != -1 and len(selectedFiles) > filesAtMost:
			Dialogs.showerror(self,
			"You can select at most %d source datasets for %s" % (filesAtMost, action), "Too many source datasets")
			self.setButtonSelection(-1)
			return
		
		self.visualizer.enable(0)
		lib.messenger.send(None, "update_progress", 0.1, "Loading task %s..." % action)
		self.onMenuShowTree(show = False)
		# Hide the infowin and toggle the menu item accordingly
		self.infoWin.SetDefaultSize((0, 0))
		self.menuManager.check(MenuManager.ID_VIEW_INFO, 0)
		self.currentTaskWindowType = windowtype
		
		window = windowtype(self.taskWin, self.menuManager)
		
		lib.messenger.send(None, "update_progress", 0.2, "Loading task %s..." % action)
		window.Show()
		
		self.switchBtn.Enable(1)
		if self.currentTaskWindow:
			self.currentTaskWindow.cacheSettings()
			self.currentTaskWindow.Show(0)
			self.currentTaskWindow.Destroy()
			del self.currentTaskWindow
		
		self.currentTaskWindowName = taskname
		self.currentTaskWindow = window
		self.tasks[taskname] = window
		w, h = self.taskWin.GetSize()
		w, h2 = self.taskWin.origSize
		self.taskWin.SetDefaultSize((w, h))
		self.currentTaskWindow.SetSize((w, h))
		wx.LayoutAlgorithm().LayoutWindow(self, self.visWin)
		
		names = [i.getName() for i in selectedFiles]
		
		cacheKey = scripting.getCacheKey(selectedPaths, names, taskname)
		
		self.currentTaskWindow.setCacheKey(cacheKey)
		# Sets name for new dataset series
		name = "%s (%s)" % (action, ", ".join(names))

		#Logging.info(unittype, name, kw = "task")
		unit = unittype(name)
		Logging.info("unit = %s(%s)=%s" % (unittype, name, unit), kw = "task")
		try:
			for dataunit in selectedFiles:
				unit.addSourceDataUnit(dataunit)
				#Logging.info("ctf of source=", dataunit.getSettings().get("ColorTransferFunction"), kw = "ctf")
		except Logging.GUIError, ex:
			lib.messenger.send(None, "update_progress", 1.0, "Loading task %s cancelled." % action)
			ex.show()
			self.closeTask()
			return

		lib.messenger.send(None, "update_progress", 0.3, "Loading task %s..." % action)
		Logging.info("Moduletype=", moduletype, kw = "dataunit")
		module = moduletype()
		unit.setModule(module)
		unit.setCacheKey(cacheKey)
		window.setCombinedDataUnit(unit)		

		for name, taskid in self.taskToId.items():
			if name == taskname:
				self.setButtonSelection(taskid)
				break

		# If visualizer has not been loaded, load it now
		# This is a high time to have a visualization loaded
		self.progressCoeff = 0.5
		self.progressShift = 30
		self.visualizer.enable(1)
		if not self.visualizer:
			Logging.info("Loading slices view for ", unit, kw = "task")
			self.loadVisualizer(self.defaultModeName, 1, dataunit = unit)
			self.setButtonSelection(MenuManager.ID_VIS_SLICES)
		else:
			if not self.visualizer.getProcessedMode():
				self.visualizer.setProcessedMode(1)

		self.visualizer.setDataUnit(unit)
		
		self.progressCoeff = 1.0
		self.progressShift = 0
		lib.messenger.send(None, "update_progress", 0.9, "Loading task %s..." % action)
		wx.LayoutAlgorithm().LayoutWindow(self, self.visWin)
		self.visWin.Refresh()
		#self.menuManager.enable(MenuManager.ID_CLOSE_TASKWIN)
		self.menuManager.enable(MenuManager.ID_VIEW_TASKPANEL)
		lib.messenger.send(None, "update_progress", 1.0, "Loading task %s... done" % action)
		
		
	def onMenuShowTree(self, event = None, show = -1):
		"""
		A method that shows the file management tree
		"""
		tb = self.GetToolBar()
		if show == -1:
			show = tb.GetToolState(MenuManager.ID_SHOW_TREE)
		else:
			tb.ToggleTool(MenuManager.ID_SHOW_TREE, show)

		self.menuManager.check(MenuManager.ID_VIEW_TREE, show)
		self.menuManager.check(MenuManager.ID_FILE_VIEW_TREE, show)
		
		if not show:
			w, h = self.treeWin.GetSize()
			if w and h:
				self.treeWin.origSize = (w, h)
			w = 0
		else:
			w, h = self.treeWin.origSize
		self.treeWin.SetDefaultSize((w, h))
		
		wx.LayoutAlgorithm().LayoutWindow(self, self.visWin)
		self.visualizer.OnSize(None)
		self.visualizer.getCurrentWindow().setZoomFactor(self.visualizer.getCurrentWindow().getZoomFactor())
		self.visualizer.getCurrentWindow().updatePreview()

	def loadVisualizer(self, mode, processed = 0, dataunit = None, **kws):
		"""
		Load a dataunit and a given mode to visualizer
		"""
		print "\n\nLOADVISUALIZER",mode,dataunit
		scripting.currentVisualizationMode = mode
		eid = self.visToId[mode]
		self.setButtonSelection(eid)
		self.setVisualizerMenuSelection(eid)

		if not self.visualizer:
			self.visPanel = wx.SashLayoutWindow(self.visWin, -1)
			self.visualizer = Visualizer(self.visPanel, self.menuManager, self)
			scripting.visualizer = self.visualizer
			lib.Command.visualizer = self.visualizer
			self.menuManager.setVisualizer(self.visualizer)
			self.visualizer.setProcessedMode(processed)

		self.visualizer.enable(0)
		lib.messenger.send(None, "update_progress", 0.6, "Loading %s view..." % mode)
		wx.EVT_TOOL(self, MenuManager.ID_SAVE_SNAPSHOT, self.onSnapshot)
		shouldReload = kws.get("reload", 0)
		
		self.visualizer.setVisualizationMode(mode, shouldReload = shouldReload)

		if not "init" in kws and dataunit:
			print "SETTING DATAUNIT",dataunit
			self.visualizer.setDataUnit(dataunit)
		else:
			self.visualizer.toggleTimeSlider(0)
			self.visualizer.toggleZSlider(0)

		# handle icons
		lib.messenger.send(None, "update_progress", 0.8, "Loading %s view..." % mode)

		self.showVisualization(self.visPanel)
		self.visualizer.enable(1)
		mgr = self.menuManager
		mgr.enable(MenuManager.ID_VIEW_TOOLBAR)
		mgr.enable(MenuManager.ID_VIEW_HISTOGRAM)
		wx.LayoutAlgorithm().LayoutWindow(self, self.visWin)
		self.visWin.Refresh()
		lib.messenger.send(None, "update_progress", 1.0, "Loading %s view... done." % mode)

	def setButtonSelection(self, eid, all = 0):
		"""
		Select only the selected button
		"""
		lst = []
		# If the selection is to be set among all buttons (both task & vis mode) then go thorugh 
		# the ids of all the buttons
		if all:
			lst.extend(self.visIds)
			lst.extend(self.taskIds)
		else:
			# otherwise only go through the ids of the buttons that belong to the same cateogry
			# (task or vis mode) as the selected id
			if eid in self.visIds:
				lst.extend(self.visIds)
			else:
				lst.extend(self.taskIds)
		tb = self.GetToolBar()
		# loop through the button ids and toggle the selected button on and others off
		for i in lst:
			flag = (i == eid)
			tb.ToggleTool(i, flag)

	def onMenuAbout(self, evt):
		"""
		Callback function for menu item "About"
		"""
		about = GUI.AboutDialog.AboutDialog(self)
		about.ShowModal()
		about.Destroy()
		
	def onViewHelp(self, obj, evt, args):
		"""
		A method that shows a help of some item
		"""
		"""
		if not self.help:
			self.help = wx.html.HtmlHelpController()
			helppath = os.path.join(scripting.get_help_dir(), "help.hhp")
			self.help.AddBook(helppath, 1)
			self.help.SetTitleFormat("BioImageXD - %s")
		if not args:
			self.help.DisplayContents()
		else:
			self.help.Display(args)
		"""
		filename = os.path.join(scripting.get_help_dir(), "BioImageXD_GettingStarted.pdf")
		ftype = wx.TheMimeTypesManager.GetFileTypeFromExtension('pdf')
		if ftype is not None:
			cmd = ftype.GetOpenCommand(filename)
			wx.Execute(cmd)
		else:
			wx.MessageBox("No application to open %s"%filename)
			
	def onMenuHelp(self, evt):
		"""
		Callback function for menu item "Help"
		"""
		self.onViewHelp(None, None, None)
		
	def saveWindowSizes(self):
		"""
		Save window sizes to the settings
		"""
		conf = Configuration.getConfiguration()

		size = str(self.GetSize())
		conf.setConfigItem("WindowSize", "Sizes", size)
		conf.writeSettings()
	
	def quitApp(self, evt):
		"""
		Possibly queries the user before quitting, then quits
		"""
		conf = Configuration.getConfiguration()
		try:
			openFiles = conf.getConfigItem("FileList", "General")
		except:
			openFiles = []

		if not openFiles or type(openFiles) == types.UnicodeType:
			numOpenFiles = 0
		else:
			numOpenFiles = len(openFiles)

		askOnQuit = conf.getConfigItem("AskOnQuit", "General")
		if askOnQuit and eval(askOnQuit) and numOpenFiles:
			dlg = QuitDialog.QuitDialog(self, "Do you really want to quit",
											"Do you want to save file tree for later use?")

			answer = dlg.ShowModal()
			dlg.Destroy()

			if answer != wx.ID_YES and answer != wx.ID_NO:
				return
		else:
			answer = wx.ID_NO
			
		self.saveWindowSizes()
			
		self.visualizer.enable(0)		
		self.closeVisualizer()

		if answer == wx.ID_NO:
			conf.setConfigItem("FileList", "General", "[]")
		conf.setConfigItem("CleanExit", "General", "True")
		history = []
		#for i in range(0, self.filehistory.GetCount()):
		#	filepath = self.filehistory.GetHistoryFile(i)
		#	history.append(filepath)
		i = self.filehistory.GetCount()-1
		while i >= 0:
			history.append(self.filehistory.GetHistoryFile(i))
			i = i - 1
		conf.setConfigItem("HistoryList", "General", str(history))
		conf.writeSettings()
		self.Cleanup()
		
		self.Destroy()
		sys.exit(0)

	def onSnapshot(self,event):
		"""
		Save snapshot event handler
		"""
		if self.visualizer:
			self.visualizer.onSnapshot(event)

	def onCloseAll(self,event):
		"""
		Close all files from the file tree
		"""
		self.tree.closeAll()

	def onSelectAll(self,event):
		"""
		Select all files from the file tree
		"""
		self.tree.onSelectAll(event)
		
	def onAddAnnotation(self,event):
		"""
		Add annotation to the visualizer
		"""
		if not self.visualizer.getCurrentMode():
			return
		
		annoclass = None
		eid = event.GetId()
		multiple = 0

		if eid == MenuManager.ID_MENU_ADD_SCALE:
			annoclass = "SCALEBAR"
		elif eid == MenuManager.ID_MENU_ROI_CIRCLE:
			annoclass = "CIRCLE"
		elif eid == MenuManager.ID_MENU_ROI_RECTANGLE:
			annoclass = "RECTANGLE"
		elif eid == MenuManager.ID_MENU_ROI_POLYGON:
			annoclass = "POLYGON"
			multiple = 1
		else:
			Logging.info("BOGUS ANNOTATION SELECTED!", kw = "visualizer")

		self.visualizer.getCurrentMode().annotate(annoclass, multiple = multiple)

	def onDeleteAnnotation(self,event):
		"""
		Delete selected annotation
		"""
		if self.visualizer.getCurrentMode():
			self.visualizer.getCurrentMode().deleteAnnotation()

	def onRoiToMask(self, evt):
		"""
		Convert the selected ROI to mask
		"""
		self.visualizer.annotateToolbar.roiToMask(evt)

	def setVisualizerMenuSelection(self, eid):
		"""
		Select only the selected button
		"""
		for i in self.visIds:
			flag = (i == eid)
			self.menuManager.check(i, flag)

	def onResampleData(self, evt):
		"""
		Toggle the resampling on / off
		"""
		flag = evt.IsChecked()
		self.visualizer.resamplingBtn.SetToggle(flag)
		self.visualizer.resampleData(flag)

	def updateCache(self, evt = None, obj = None, delay = 0):
		"""
		Hackish way to update settings cache when something is changed.
		"""
		try:
			selectedPaths = self.tree.getSelectedPaths()
			selectedFiles = self.tree.getSelectedDataUnits()
			names = [i.getName() for i in selectedFiles]
			cacheKey = scripting.getCacheKey(selectedPaths, names, "Adjust")
			scripting.removeSettingsFromCache(cacheKey, "ColorTransferFunction")
		except:
			pass

	def closeVisualizer(self):
		"""
		"""
		self.tree.onUngroup(None)
		self.visualizer.closeVisualizer()
		
