#! /usr/bin/env python
# -*- coding: iso-8859-1 -*-
"""
 Unit: FilterEditor
 Project: BioImageXD
 Description:

 A common filter editor GUI component and model for use all around the software
 							
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
__version__ = "$Revision: 1.42 $"
__date__ = "$Date: 2005/01/13 14:52:39 $"

import scripting
import ConfigParser
import GUI.Dialogs
import GUI.FilterBasedTaskPanel
import Logging
import glob 
import lib.Command
import lib.ImageOperations
import lib.messenger

import lib.FilterTypes
import lib.FilterBasedModule
import Modules.DynamicLoader

import os.path
import sys
import platform
import types
import wx

class FilterEditor(wx.Panel):
	"""
	Description: A filter list editor
	"""
	def __init__(self, parent, filtersModule = None, filterList = None, taskPanel = None, scriptingId = "scripting.mainWindow.tasks['Process'].filterEditor", fbSize = (300,300)):
		"""
		Initialization
		"""
		wx.Panel.__init__(self, parent)
		self.filterBoxSize = fbSize
		self.parent = parent
		self.taskPanel = taskPanel
		self.currentSelected = -1
		pluginLoader = Modules.DynamicLoader.getPluginLoader()
		taskMod = pluginLoader.getPluginModule("Task", "Process")
		print "taskmod=",taskMod
		filtersMod = taskMod.getFilterModule()
		if not filtersModule:
			filtersModule = filtersMod
			
		self.filtersModule = filtersModule
		self.menus = {}
		if filterList:
			self.filterList = filterList
		else:
			self.filterList = lib.FilterBasedModule.FilterList(filtersModule)
		self.scriptingId = scriptingId
		self.initializeGUI()
		
		self.currentGUI = None
		self.presetMenu = None
		self.parser = None
		self.onByDefault = 0
		self.dataUnit = None
		self.Show()

	def setFilterList(self, filterList):
		"""
		set the filter list edited by this filter editor
		"""
		self.filterList = filterList
		

	def getFilters(self, name):
		"""
		Retrieve the filters with the given name
		"""	 
		return self.filterList.getFiltersWithName(name)
	
	def getFilter(self, name, index = 0):
		"""
		Retrieve the filter with the given name, using optionally an index 
								if there are more than one filter with the same name
		"""	 
		return self.getFilters(name)[index]
		
	def getFilterList(self):
		"""
		return the filter list
		"""
		return self.filterList

	def setDataUnit(self, dataUnit):
		"""
		set the dataunit that is controlled by this editor
		"""
		self.dataUnit = dataUnit
		self.filterList.setDataUnit(dataUnit)
		
	def initializeGUI(self):
		"""
		Creates a frame that contains the various widgets
					 used to control the colocalization settings
		"""
		self.sizer = wx.GridBagSizer()
	
		self.filtersizer = wx.GridBagSizer(4, 4)
		
		self.filterLbl = wx.StaticText(self, -1, "Procedure list:")
		self.filterListbox = wx.CheckListBox(self, -1, size = self.filterBoxSize)
		self.filterListbox.Bind(wx.EVT_LISTBOX, self.onSelectFilter)
		self.filterListbox.Bind(wx.EVT_CHECKLISTBOX, self.onCheckFilter)
		self.addFilteringBtn = wx.Button(self, -1, u"Filtering \u00BB")
		self.addArithmeticsBtn = wx.Button(self, -1, u"Arithmetics \u00BB")
		self.addSegmentationBtn = wx.Button(self, -1, u"Segmentation \u00BB")
		self.addAnalyzeBtn = wx.Button(self, -1, u"Analyze \u00BB")
		self.addMiscBtn = wx.Button(self, -1, u"Misc \u00BB")
		self.presetBtn = wx.Button(self, -1, u"Presets \u00BB")

		MP = self.filtersModule
		f = lambda evt, btn = self.addFilteringBtn, \
					cats = (lib.FilterTypes.FILTERING, lib.FilterTypes.DECONVOLUTION, lib.FilterTypes.FEATUREDETECTION, lib.FilterTypes.MORPHOLOGICAL, lib.FilterTypes.FOURIER, lib.FilterTypes.MISCFILTERING): \
					self.onShowAddMenu(evt, btn, cats)
		self.addFilteringBtn.Bind(wx.EVT_LEFT_DOWN, f)
		
		f = lambda evt, btn = self.addArithmeticsBtn, \
					cats = (lib.FilterTypes.MATH, lib.FilterTypes.LOGIC, lib.FilterTypes.SUBTRACT): \
					self.onShowAddMenu(evt, btn, cats)
		self.addArithmeticsBtn.Bind(wx.EVT_LEFT_DOWN, f)
		
		f = lambda evt, btn = self.addSegmentationBtn, \
					cats = (lib.FilterTypes.THRESHOLDING, lib.FilterTypes.WATERSHED, \
							lib.FilterTypes.REGION_GROWING, \
							lib.FilterTypes.ACTIVECONTOUR, lib.FilterTypes.OBJECT): \
					self.onShowAddMenu(evt, btn, cats)
		self.addSegmentationBtn.Bind(wx.EVT_LEFT_DOWN, f)

		f = lambda evt, btn = self.addAnalyzeBtn, \
			cats = (lib.FilterTypes.SEGMENTATIONANALYSE, lib.FilterTypes.VOXELANALYSE, lib.FilterTypes.COLOCALIZATION): \
			self.onShowAddMenu(evt, btn, cats)
		self.addAnalyzeBtn.Bind(wx.EVT_LEFT_DOWN, f)

		f = lambda evt, btn = self.addMiscBtn, \
			cats = (lib.FilterTypes.ROI, lib.FilterTypes.SIMULATION, lib.FilterTypes.REGISTRATION, lib.FilterTypes.TRACKING, lib.FilterTypes.CONVERSION): \
			self.onShowAddMenu(evt, btn, cats)
			
		self.addMiscBtn.Bind(wx.EVT_LEFT_DOWN, f)
		
		#f = lambda evt, btn = self.addTrackingBtn, cats = (lib.FilterTypes.TRACKING, ): \
		#			self.onShowAddMenu(evt, btn, cats)        
		#self.addTrackingBtn.Bind(wx.EVT_LEFT_DOWN, f)
		
		self.presetBtn.Bind(wx.EVT_LEFT_DOWN, self.onShowPresetsMenu)
		
		vertbtnBox = wx.BoxSizer(wx.VERTICAL)
		#bmp = wx.ArtProvider_GetBitmap(wx.ART_DELETE, wx.ART_TOOLBAR, (16, 16))        
		#self.remove = wx.BitmapButton(self, -1, bmp)
		#self.remove.Bind(wx.EVT_BUTTON, self.onRemoveFilter)
		
		#bmp = wx.ArtProvider_GetBitmap(wx.ART_GO_UP, wx.ART_TOOLBAR, (16, 16))        
		#self.up = wx.BitmapButton(self, -1, bmp)
		#bmp = wx.ArtProvider_GetBitmap(wx.ART_GO_DOWN, wx.ART_TOOLBAR, (16, 16))        
		#self.up.Bind(wx.EVT_BUTTON, self.onMoveFilterUp)
		#self.down = wx.BitmapButton(self, -1, bmp)
		#self.down.Bind(wx.EVT_BUTTON, self.onMoveFilterDown)

		iconpath = scripting.get_icon_dir()
		uparrow = wx.Image(os.path.join(iconpath, "Arrow_Up.png"), wx.BITMAP_TYPE_PNG).ConvertToBitmap()
		downarrow = wx.Image(os.path.join(iconpath, "Arrow_Down.png"), wx.BITMAP_TYPE_PNG).ConvertToBitmap()
		remove = wx.Image(os.path.join(iconpath, "Delete.png"), wx.BITMAP_TYPE_PNG).ConvertToBitmap()

		self.up = wx.BitmapButton(self, -1, uparrow)
		self.down = wx.BitmapButton(self, -1, downarrow)
		self.remove = wx.BitmapButton(self, -1, remove)

		self.up.Bind(wx.EVT_BUTTON, self.onMoveFilterUp)
		self.down.Bind(wx.EVT_BUTTON, self.onMoveFilterDown)
		self.remove.Bind(wx.EVT_BUTTON, self.onRemoveFilter)
		
		vertbtnBox.Add(self.remove)
		vertbtnBox.Add(self.up)
		vertbtnBox.Add(self.down)
		btnBox = wx.FlexGridSizer(2, 3)
		btnBox.SetVGap(3)
		btnBox.SetHGap(4)
		#btnBox2 = wx.GridSizer(wx.HORIZONTAL)
		btnBox.Add(self.addFilteringBtn)
		#btnBox.AddSpacer((4, 4))
		btnBox.Add(self.addArithmeticsBtn)
		#btnBox.AddSpacer((4, 4))
		btnBox.Add(self.addSegmentationBtn)
		#btnBox2.Add(self.addTrackingBtn)
		btnBox.Add(self.addAnalyzeBtn)
		#btnBox2.AddSpacer((4, 4))
		btnBox.Add(self.addMiscBtn)
		#btnBox2.AddSpacer((4, 4))
		btnBox.Add(self.presetBtn)

		box = wx.BoxSizer(wx.HORIZONTAL)
		box.Add(self.filterListbox)
		box.Add(vertbtnBox)
		self.filtersizer.Add(self.filterLbl, (0, 0))
		self.filtersizer.Add(box, (1, 0), flag = wx.EXPAND | wx.LEFT | wx.RIGHT)
		self.filtersizer.Add(btnBox, (2, 0))
		#self.filtersizer.Add(btnBox2, (3, 0))
		
		self.sizer.Add(self.filtersizer, (0, 0))

		self.SetSizer(self.sizer)
		self.SetAutoLayout(1)
		
		#self.settingsSizer.Add(self, (1, 0), flag = wx.EXPAND | wx.ALL)
		
	def updateFromFilterList(self):
		"""
		update the list box to reflect the filter list
		"""
		self.filterListbox.Clear()
		filterList = self.filterList.getFilters()
		labels = [x.getName() for x in filterList]
		if labels:
			self.filterListbox.InsertItems(labels,0)
		for i, currFilter in enumerate(filterList):
			self.filterListbox.Check(i, currFilter.getEnabled())
		
	def onMoveFilterDown(self, event):
		"""
		Move a filter down in the list
		"""
		index = self.filterListbox.GetSelection()
		if index == -1:
			GUI.Dialogs.showerror(self, "You have to select a filter to be moved", "No filter selected")
			return 
		n = self.filterListbox.GetCount()
		if index == n - 1:
			GUI.Dialogs.showerror(self, "Cannot move last filter down", "Cannot move filter")
			return
		
		lbl = self.filterListbox.GetString(index)
		chk = self.filterListbox.IsChecked(index)
		self.filterListbox.InsertItems([lbl], index + 2)
		self.filterListbox.Check(index + 2, chk)
		self.filterListbox.SetSelection(index + 2)
		self.filterListbox.Delete(index)
		self.filterList.moveDown(index)
		
	def onMoveFilterUp(self, event):
		"""
		Move a filter up in the list
		"""
		index = self.filterListbox.GetSelection()
		if index == -1:
			GUI.Dialogs.showerror(self, "You have to select a filter to be moved", "No filter selected")
			return        
		if index == 0:
			GUI.Dialogs.showerror(self, "Cannot move first filter up", "Cannot move filter")
			return
			
		lbl = self.filterListbox.GetString(index)
		chk = self.filterListbox.IsChecked(index)
		self.filterListbox.InsertItems([lbl], index - 1)
		self.filterListbox.Check(index - 1, chk)
		self.filterListbox.SetSelection(index -1)
		self.filterListbox.Delete(index + 1)
		self.filterList.moveUp(index)
		
	def onRemoveFilter(self, event):
		"""
		Remove a filter from the list
		"""
		index = self.filterListbox.GetSelection()
		if index == -1:
			GUI.Dialogs.showerror(self, "You have to select a filter to be removed", "No filter selected")
			return 
		name = self.filterList.getFilter(index).getName()
		undo_cmd = ""
		do_cmd = "%s.deleteFilter(index=%d, name='%s')" % (self.scriptingId, index, name)
		cmd = lib.Command.Command(lib.Command.GUI_CMD, None, None, do_cmd, undo_cmd, \
									desc = "Remove filter '%s'" % (name))
		cmd.run()
			

		
	def onCheckFilter(self, event):
		"""
		Event handler called when user toggles filter on or off
		"""
		index = event.GetSelection()
		name = self.filterList.getFilter(index).getName()
		status = self.filterListbox.IsChecked(index)
		cmd = "Enable"
		if not status:
			cmd = "Disable"
		undo_cmd = "%s.setFilter(%s, index=%d, name='%s')" \
					% (self.scriptingId, str(status), index, name)
		do_cmd = "%s.setFilter(%s, index=%d, name='%s')" \
					% (self.scriptingId, str(status), index, name)
		descstr  = "%s filter '%s'" % (cmd, name)
				
		cmd = lib.Command.Command(lib.Command.GUI_CMD, None, None, do_cmd,
		undo_cmd, None, descstr)
		cmd.run()
		
	def setFilter(self, status, index = -1, name = ""):
		"""
		Set the status of a given filter by either it's index or
					 if index is not given, it's name
		"""        
		if index == -1:
			for i in self.filterList.getFilters():
				if i.getName() == name:
					index = i
					break
		if index == -1:
			return False
		self.filterList.setEnabled(index, status)
		
	def removeGUI(self):
		"""
		Remove the GUI
		"""        
		if self.currentGUI:
			self.sizer.Detach(self.currentGUI)
			self.currentGUI.Show(0)

	def resetGUI(self):
		"""
		reset the shown GUI
		"""
		self.removeGUI()
		self.Layout()
		self.parent.Layout()
		self.parent.FitInside()
		self.selected = -1
		self.currentSelected = -1
		
	def onSelectFilter(self, event):
		"""
		Event handler called when user selects a filter in the listbox
		"""
		self.selected = event.GetSelection()
		if self.selected == self.currentSelected:
			return
		self.currentSelected = self.selected
		self.removeGUI()
		
		currfilter = self.filterList.getFilter(self.selected)
		self.currentGUI = currfilter.getGUI(self, self.taskPanel)
		
		currfilter.sendUpdateGUI()
		
		self.currentGUI.Show(1)        
		self.sizer.Add(self.currentGUI, (1, 0), flag = wx.EXPAND | wx.ALL)
		
		self.currentGUI.Layout()
		
		self.Layout()
		self.parent.Layout()
		self.parent.FitInside()

		
	def loadFilter(self, className):
		"""
		Add a filter with the given name to the stack
		"""
		filterclass = self.filterList.getClassForName(className)
		return self.addFilter(None, filterclass)
		
	def deleteFilter(self, index = -1, name = ""):
		"""
		Delete a filter by either it's index, or
					 if index is not given, it's name
		"""
		if index == -1:
			index = self.filterList.getIndexForName(name)
			if index == -1:
				return False
		
		self.filterListbox.Delete(index)
		self.filterList.removeFilter(index)
		self.currentSelected = -1
		self.removeGUI()
		self.currentGUI = None
		self.Layout()
		self.parent.Layout()

	def addFilter(self, event, filterclass):
		"""
		Add a filter to the stack
		"""        
		if not filterclass:
			return
		addfilter = filterclass()
		addfilter.setDataUnit(self.dataUnit)
		if self.taskPanel:
			addfilter.setTaskPanel(self.taskPanel)
		name = addfilter.getName()
		n = self.filterListbox.GetCount()
		self.filterListbox.InsertItems([name], n)
		self.filterListbox.Check(n)
		
		self.filterList.addFilter(addfilter)
		lib.messenger.send(self, "updateFilterList")
		
	def onShowPresetsMenu(self, event):
		"""
		show a menu with preloaded presets for different tasks
		"""
		if not self.presetMenu:
			self.presetMenu = wx.Menu()
			addId = wx.NewId()
			addItem = wx.MenuItem(self.presetMenu, addId, "Save as preset...")
			self.presetMenu.AppendItem(addItem)
			self.presetMenu.AppendSeparator()
			self.Bind(wx.EVT_MENU, self.onSavePreset, id = addId)
			
			presetDir = scripting.get_preset_dir()
			presetFiles = os.path.join(presetDir,"*.bxp")
			files = glob.glob(presetFiles)
			for filenm in files:
				name = ".".join(os.path.basename(filenm).split(".")[:-1])
				fileId = wx.NewId()
				fileItem = wx.MenuItem(self.presetMenu, fileId, name)
				filenm = filenm.replace("\\", "\\\\")
				if platform.system == "Windows":
					filenm = filenm.encode('mbcs')
				do_cmd = "%s.loadPreset('%s')" % (self.scriptingId, filenm)
			   
				cmd = lib.Command.Command(lib.Command.GUI_CMD, None, None, do_cmd, "", \
											desc = "Load preset %s" % name)
				f = lambda evt, c = cmd: c.run()
				self.Bind(wx.EVT_MENU, f, id = fileId)
				self.presetMenu.AppendItem(fileItem)
				
		self.presetBtn.PopupMenu(self.presetMenu, event.GetPosition())
				
	def loadPreset(self, name):
		"""
		load the given preset
		"""
		parser = ConfigParser.RawConfigParser()
		parser.optionxform = str
		parser.read([name])
		self.filterList.clear()
		self.filterList.setDataUnit(self.dataUnit)
		values = parser.get("FilterList","FilterList")
		if type(values)==type(""):
			values = eval(values)
		self.filterList.populate(values)
		self.filterList.readValuesFrom(parser)
		#self.filterList = filterList
		self.updateFromFilterList()
		
	def saveAsPreset(self, name):
		"""
		save the procedure list as preset
		"""
		parser = ConfigParser.RawConfigParser()
		parser.optionxform = str
		self.filterList.writeOut(parser)

		presetDir = scripting.get_preset_dir()
		if platform.system() == "Windows":
			try:
				name = name.encode('mbcs')
			except:
				Logging.error("Preset saving error", 'Only ascii characters (a-z,0-9,-,_) can be used in preset name in Windows')

		if not os.access(presetDir, os.F_OK):
			os.mkdir(presetDir)
		filename = os.path.join(presetDir, name + ".bxp")
		parser.write(open(filename,"w"))

	def setModified(self, flag):
		"""
		set the status of the filter list
		"""
		self.filterList.setModified(flag)

	def onSavePreset(self, evt):
		"""
		eventhandler called when the user selects save as preset
		"""
		dlg = wx.TextEntryDialog(
		self, 'Enter name for preset',
				'Save preset as...', 'Preset')

		if dlg.ShowModal() == wx.ID_OK:
			name = dlg.GetValue()
			do_cmd = "%s.saveAsPreset('%s')" % (self.scriptingId, name)
			cmd = lib.Command.Command(lib.Command.GUI_CMD, None, None, do_cmd, "", \
										desc = "Save procedure list as preset %s" % name)
			cmd.run()
			del self.presetMenu
			self.presetMenu = None

	def onShowAddMenu(self, event, btn, categories = ()):
		"""
		Show a menu for adding filters to the stack
		"""
		if categories not in self.menus:
			menu = wx.Menu()
			for category in categories:
				submenu = wx.Menu()
				for currfilter in self.filterList.getFiltersInCategory(category):
					menuid = wx.NewId()
					name = currfilter.getName()
					
					newitem = wx.MenuItem(submenu, menuid, name)
					if currfilter.level:
						newitem.SetTextColour(wx.Colour(*currfilter.level))
					submenu.AppendItem(newitem)
					n = self.filterList.getCount()
					undo_cmd = "%s.deleteFilter(index=%d, name = '%s')" % (self.scriptingId, n, name)
					
					do_cmd = "%s.loadFilter('%s')" % (self.scriptingId, name)
					cmd = lib.Command.Command(lib.Command.GUI_CMD, None, None, do_cmd, undo_cmd, \
												desc = "Load filter %s" % name)
					
					f = lambda evt, c = cmd: c.run()
					self.Bind(wx.EVT_MENU, f, id = menuid)
				menu.AppendMenu(-1, category, submenu)
			self.menus[categories] = menu
		btn.PopupMenu(self.menus[categories], event.GetPosition())
		

	def doFilterCheckCallback(self, event = None):
		"""
		A callback function called when the neither of the
					 filtering checkbox changes state
		"""
		pass

	def cleanFilterListBox(self):
		"""
		Empties filter list and resets GUI
		"""
		self.filterListbox.Clear()
		self.resetGUI()
		
