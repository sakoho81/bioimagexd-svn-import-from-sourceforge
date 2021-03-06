# -*- coding: iso-8859-1 -*-
"""
 Unit: RenderingInterface.py
 Project: BioImageXD
 Description:

		   
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
__version__ = "$Revision: 1.21 $"
__date__ = "$Date: 2005/01/13 13:42:03 $"

import math
import os.path
import Logging
import scripting
import platform
renderingInterface = None

def getRenderingInterface(mayavi = 0):
	global renderingInterface
	if not renderingInterface:
		renderingInterface = RenderingInterface()
	return renderingInterface

class RenderingInterface:
	"""
	The interface to visualizer used for animator rendering
	"""
	def __init__(self, dataUnit = None, timePoints = [], **kws):
		"""
		Initialization
		"""
		self.dataUnit = dataUnit
		self.currentData = None
		self.timePoints = timePoints
		
		self.settings_mode = 0
		self.frameName = "frame"
		self.thread = None
		self.stop = 0
		self.currentTimePoint = -1
		# XXX: Make this configurable
		#self.imageType = Configuration.getConfiguration().getConfigItem("ImageFormat", "Output")
		
		#if not self.imageType:
		#	 self.imageType = "pnm"
		self.imageType = "png"
		self.visualizer = None
		self.frameList = []
		
	def setType(self, imageType):
		"""
		Set the imageType of the rendered frame
		"""			   
		self.imageType = imageType
		
	def getColorTransferFunction(self):
		"""
		Return the current ctf
		"""
		return self.ctf
		
	def getCurrentData(self):
		"""
		Return the current timepoint
		"""
	
		if not self.currentData:
			currentTimepoint = self.currentTimePoint
			if currentTimepoint < 0:
				currentTimepoint = 0
			self.setCurrentTimepoint(currentTimepoint)
		return self.currentData
		
	def setCurrentTimepoint(self, timepoint):
		"""
		Sets the current timepoint to be the specified timepoint.
					 This will also update relevant information about the dataset

		Preconditions: self.dataUnit != 0
		"""
		if not self.dataUnit:
			return
		
		self.currentTimePoint = timepoint
		if self.dataUnit.isProcessed():
			self.currentData = self.dataUnit.doPreview(scripting.WHOLE_DATASET, True, timepoint)
		else:
			self.currentData = self.dataUnit.getTimepoint(timepoint)
		self.dimensions = self.currentData.GetDimensions()
		
	def setRenderWindowSize(self, size):
		"""
		Sets the visualizer's render window size
		"""		   
		x, y = size
		if self.visualizer:
			self.visualizer.setRenderWindowSize((x, y))
			
	def getRenderWindow(self):
		"""
		Returns the visualizer's render window. Added for Animator compatibility
		"""
		return self.visualizer.getCurrentMode().GetRenderWindow()
	
	def setParent(self, parent):
		"""
		Set the parent of this window
		"""		   
		self.parent = parent
		
	def getRenderer(self):
		"""
		Returns the renderer
		"""		   
		return self.visualizer.getCurrentMode().GetRenderer()
		
	def render(self):
		self.visualizer.getCurrentMode().Render()
	
	def setVisualizer(self, visualizer):
		"""
		Set the visualizer instance to use
		"""		   
		self.visualizer = visualizer
		self.frameList = []
		
	def setDataUnit(self, dataUnit):
		"""
		Set the dataunit from which the rendered datasets are read
		"""
		# Format, the format will be /path/to/data/image_001.png
		ndigits = 1
		self.format = "%%s%s%%s_%%.%dd.%s" % (os.path.sep, ndigits, self.imageType)
		
		self.dataUnit = dataUnit
		if not dataUnit:
			return
		
		# Calculate how many digits there will be in the rendered output
		# file names, with a running counter
		ndigits = 1 + int(math.log(self.dataUnit.getNumberOfTimepoints(), 10))

		#Logging.info("File name format = ", self.format)
		self.ctf = dataUnit.getColorTransferFunction()

		#self.ctf = dataUnit.getSettings().get("ColorTransferFunction")
		self.frameName = self.dataUnit.getName()

	def setTimePoints(self, timepoints):
		"""
		Set the list of timepoints to be rendered
		"""
		self.timePoints = timepoints

	def isVisualizationSoftwareRunning(self):
		"""
		A method that returns true if a visualizer window exists that 
					 can be used for rendering
		"""
		return (self.visualizer and not self.visualizer.isClosed())
		
	def isVisualizationModuleLoaded(self):
		"""
		A method that returns true if the visualizer has a visualization module loaded.
		"""
		return len(self.visualizer.getCurrentMode().getModules())		 
		
	def getFrameList(self):
		"""
		Return the list of the names of the frames that have been rendered
		"""
		return self.frameList
		
	def setOutputPath(self, path):
		"""
		Sets the path where the rendered frames are stored.
		"""
		self.dirname = path
			
	def saveFrame(self, filename):
		"""
		Saves a frame with a given name
		"""
		self.frameList.append(filename)
		visualizer = self.visualizer
		imageType = self.imageType
		Logging.info("Saving screenshot to ", filename, kw = "visualizer")
		comm = "visualizer.getCurrentMode().saveSnapshot(filename)"
		eval(comm)
			
	def getFilenamePattern(self):
		"""
		Returns output filename pattern
		"""
		return self.format
		
	def getFrameName(self):
		"""
		Returns name used to construct the filenames
		"""
		return self.frameName
			
	def getFilename(self, frameNum):
		"""
		Returns output filename of the frame we're rendering
		"""
		return self.format % (self.dirname, self.frameName, frameNum)

	def getCenter(self, timepoint = -1):
		"""
		Returns the center of the requested dataset. If none is specified, the
					 center of the current dataset is returned
		"""
		if self.currentTimePoint < 0 or not self.timePoints or timepoint > max(self.timePoints):
			return (0, 0, 0)
		if timepoint < 0:
			return self.currentData.GetCenter()
		else:
			return self.dataUnit.getTimepoint(timepoint).GetCenter()
		
	def getDimensions(self, timepoint = -1):
		"""
		Returns the dimensions of the requested dataset. If none is specified, the
					 dimensions of the current dataset is returned
		"""    
		if self.currentTimePoint < 0 or not self.timePoints or timepoint > max(self.timePoints):
			return (0, 0, 0)
		if timepoint < 0:
			return self.dimensions
		else:
			return self.dataUnit.getTimepoint(timepoint).GetDimensions()
			
			
	def updateDataset(self):
		"""
		Updates the dataset to the current timepoint
		"""
		if self.visualizer:
			self.visualizer.setTimepoint(self.currentTimePoint)
			
			
