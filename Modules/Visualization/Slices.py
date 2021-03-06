# -*- coding: iso-8859-1 -*-

"""
 Unit: Slices
 Project: BioImageXD
 Description:

 A slices viewing rendering mode for Visualizer
		  
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
__author__ = "BioImageXD Project"
__version__ = "$Revision: 1.9 $"
__date__ = "$Date: 2005/01/13 13:42:03 $"

from GUI.PreviewFrame.PreviewFrame import PreviewFrame
import Logging
from Visualizer.VisualizationMode import VisualizationMode
import scripting

def getName():
	"""
	Description:Return the name of this visualization mode (used to identify mode internally)
	"""
	return "slices"
		
def isDefaultMode():
	"""
	Return a boolean indicating whether this mode should be used as the default visualization mode
	"""
	return 1
		
def showInfoWindow():
	"""
	Return a boolean indicating whether the info window should be kept visible when this mode is loaded
	"""
	return 1
		
def showFileTree():
	"""
	Return a boolean indicating whether the file tree should be kept visible when this mode is loaded
	"""
	return 1
		
def showSeparator():
	"""
	return two boolean values indicating whether to place toolbar separator before or after this icon
	"""
	return (0, 0)
		
# We want to be in the far left
def getToolbarPos():
	return - 999
		
def getIcon():
	"""
	return the icon name for this visualization mode
	"""
	return "Vis_Slices.png"
		
def getShortDesc():
	"""
	return a short description (used as menu items etc.) of this visualization mode
	"""
	return "Slices mode"
		
def getDesc():
	"""
	return a description (used as tooltips etc.) of this visualization mode
	"""
	return "View single optical sections of the dataset"
		
def getClass():
	"""
	return the class that is instantiated as the actual visualization mode
	"""
	return SlicesMode
		
def getImmediateRendering():
	"""
	Return a boolean indicating whether this mode should in general update it's 
				 rendering after each and every change to a configuration affecting the rendering
	"""
	return True
		
def getConfigPanel():
	"""
	return the class that is instantiated as the configuration panel for the mode
	"""
	return None
		
def getRenderingDelay():
	"""
	return a value in milliseconds that is the minimum delay between two rendering events being sent
				 to this visualization mode. In general, the smaller the value, the faster the rendering should be
	"""
	return 1500
		
def showZoomToolbar():
	"""
	return a boolean indicating whether the visualizer toolbars (zoom, annotation) should be visible 
	"""
	return True
		
class SlicesMode(VisualizationMode):
		
	def __init__(self, parent, visualizer):
		"""
		Initialization
		"""
		VisualizationMode.__init__(self, parent, visualizer)
		self.parent = parent
		self.visualizer = visualizer
		self.dataUnit = None

	def showSliceSlider(self):
		"""
		Method that is queried to determine whether
					 to show the zslider
		"""
		return True
		
	def showSideBar(self):
		"""
		Method that is queried to determine whether
					 to show the sidebar
		"""
		return False
		
	def Render(self):
		"""
		Update the rendering
		"""
		self.iactivePanel.updatePreview(renew = False)
		
	def updateRendering(self):
		"""
		Update the rendering
		"""
		Logging.info("Updating rendering", kw = "preview")
		self.iactivePanel.updatePreview(renew = True)
		
	def setBackground(self, red, green, blue):
		"""
		Set the background color
		"""
		if self.iactivePanel:
			self.iactivePanel.setBackgroundColor((red, green, blue))

	def activate(self, sidebarwin):
		"""
		Set the mode of visualization
		"""
		scripting.wantWholeDataset = 0
		if not self.iactivePanel:
			self.iactivePanel = PreviewFrame(self.parent, scrollbars = True)
		return self.iactivePanel
		
	def setDataUnit(self, dataUnit):
		"""
		Set the dataunit to be visualized
		"""
		self.iactivePanel.setDataUnit(dataUnit, 0)
		
	def setTimepoint(self, timePoint):
		"""
		Set the timepoint to be visualized
		"""
		Logging.info("Setting timepoint to ", timePoint, kw = "visualizer")
		self.iactivePanel.setTimepoint(timePoint)
		
	def deactivate(self, newmode = None):
		"""
		Unset the mode of visualization
		"""
		self.iactivePanel.Show(0)
		self.iactivePanel.onDeactivate()
		self.iactivePanel.Destroy()
		del self.iactivePanel
		self.iactivePanel = None
		
	def saveSnapshot(self, filename):
		"""
		Save a snapshot of the scene
		"""
		self.iactivePanel.saveSnapshot(filename)
