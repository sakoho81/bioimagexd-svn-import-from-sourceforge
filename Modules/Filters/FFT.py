#! /usr/bin/env python
# -*- coding: iso-8859-1 -*-
"""
 Unit: FFT.py
 Project: BioImageXD
 Created: 18.09.2009, LP
 Description:

 A module that contains fast fourier transform for the processing task.
 
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
__author__ = "BioImageXD Project <http://www.bioimagexd.net/>"
__version__ = "$Revision$"
__date__ = "$Date$"

import lib.ProcessingFilter
import lib.FilterTypes
import vtk
import scripting

class FFTFilter(lib.ProcessingFilter.ProcessingFilter):
	"""
	A fourier transform filter.
	"""
	name = "FFT"
	category = lib.FilterTypes.FOURIER
	level = scripting.COLOR_BEGINNER

	def __init__(self, inputs = (1,1)):
		"""
		Initialization
		"""
		lib.ProcessingFilter.ProcessingFilter.__init__(self,(1,1))
		self.descs = {}
		self.filter = None

	def updateProgress(self):
		"""
		Update progress event handler
		"""
		lib.ProcessingFilter.ProcessingFilter.updateProgress(self,self.filter,"ProgressEvent")

	def getParameterLevel(self, param):
		"""
		Returns the level of knowledge for using parameter
		@param param Parameter name
		"""
		return scripting.COLOR_BEGINNER

	def execute(self, inputs = (1,1), update = 0, last = 0):
		"""
		Execute filter in input image and return output image
		"""
		if not lib.ProcessingFilter.ProcessingFilter.execute(self,inputs):
			return None

		self.eventDesc = "Calculating FFT"
		inputImage = self.getInput(1)

		# Convert image to float
		origType = inputImage.GetScalarType()
		castFloat = vtk.vtkImageCast()
		castFloat.SetOutputScalarTypeToFloat()
		self.filter = vtk.vtkImageFFT()
		#magnitude = vtk.vtkImageMagnitude()
		#fourierCenter = vtk.vtkImageFourierCenter()
		#logarithmic = vtk.vtkImageLogarithmicScale()
		#logarithmic.SetConstant(15)

		castFloat.SetInput(inputImage)
		self.filter.SetInputConnection(castFloat.GetOutputPort())
		#magnitude.SetInputConnection(self.filter.GetOutputPort())
		#fourierCenter.SetInputConnection(magnitude.GetOutputPort())
		#logarithmic.SetInputConnection(fourierCenter.GetOutputPort())
		#outputImage = logarithmic.GetOutput()
		outputImage = self.filter.GetOutput()
		
		if update:
			outputImage.Update()

		return outputImage
