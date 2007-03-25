# -*- coding: iso-8859-1 -*-

"""
 Unit: Surface
 Project: BioImageXD
 Created: 28.04.2005, KP
 Description:

 A module containing the surface rendering modules for the visualization
           
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

import wx

import vtk
import ColorTransferEditor
import Dialogs
import types
import Logging
import Volume

import scripting as bxd
from Visualizer.VisualizationModules import *

def getClass():return SurfaceModule
def getConfigPanel():return SurfaceConfigurationPanel
def getName():return "Surface rendering"
def getQuickKeyCombo(): return "Shift-Ctrl-S"

class SurfaceModule(VisualizationModule):
    """
    Created: 28.04.2005, KP
    Description: A surface Rendering module
    """    
    def __init__(self,parent,visualizer,**kws):
        """
        Created: 28.04.2005, KP
        Description: Initialization
        """     
        VisualizationModule.__init__(self,parent,visualizer,**kws)   
        #self.name = "Surface Rendering"
        self.normals = vtk.vtkPolyDataNormals()
        self.smooth = None
        self.volumeModule = None
        self.scalarRange=(0,255)
        
        self.eventDesc="Rendering iso-surface"
        self.decimate = vtk.vtkDecimatePro()
        self.setMethod(1)
        self.init=0
        self.mapper = vtk.vtkPolyDataMapper()
        
        self.descs = {"Method":"Surface rendering method","Gaussian":"Smooth surface with gaussian smoothing",
            "Normals":"Smooth surface with normals","FeatureAngle":"Feature angle of normals\n",
            "Simplify":"Simplify surface","PreserveTopology":"Preserve topology",
            "IsoValue":"Iso value","SurfaceRangeBegin":"Generate surfaces in range:\n",
            "SurfaceAmnt":"Number of surfaces","Transparency":"Surface transparency",
            "MultipleSurfaces":"Visualize multiple surfaces"}
        
        self.actor = self.lodActor = vtk.vtkLODActor()
        self.lodActor.SetMapper(self.mapper)
        self.lodActor.SetNumberOfCloudPoints(10000)
        self.renderer = self.parent.getRenderer()
        self.renderer.AddActor(self.lodActor)
        #self.updateRendering()
        
    def getParameterLevel(self, parameter):
        """
        Created: 1.11.2006, KP
        Description: Return the level of the given parameter
        """
        if parameter in ["FeatureAngle","Normals"]:
            return bxd.COLOR_EXPERIENCED
        if parameter == "PreserveTopology":
            return bxd.COLOR_INTERMEDIATE
        
        
        return bxd.COLOR_BEGINNER            
        

    def setScalarRange(self, min,max):
        """
        Created: 21.07.2006, KP
        Description: Set the scalar range of this module
        """   
        self.scalarRange = (min,max)
        messenger.send(self,"update_SurfaceRangeBegin")
        messenger.send(self,"update_SurfaceRangeEnd")
        messenger.send(self,"update_SurfaceAmnt")
        messenger.send(self,"update_IsoValue")
        print "Scalar range of data=",min,max
        
    def getParameters(self):
        """
        Created: 31.05.2006, KP
        Description: Return the list of parameters needed for configuring this GUI
        """            
        return [ ["", ("Method",)],
       ["Smoothing options",("Gaussian","Normals","FeatureAngle","Simplify","PreserveTopology") ],
       ["Iso-Surface",("IsoValue",)],
       ["Multiple Surfaces",("MultipleSurfaces","SurfaceRangeBegin",GUIBuilder.NOBR,"SurfaceRangeEnd","SurfaceAmnt","Transparency")]]
        
    def getRange(self, parameter):
        """
        Created: 21.07.2006, KP
        Description: If a parameter has a certain range of valid values, the values can be queried with this function
        """     
        if parameter=="Method":
            return ["Contour Filter","Marching Cubes","Discrete Marching Cubes","Iso-Surface Volume Rendering"]
        if parameter in ["Simplify","Transparency"]:
            return 0,100
        if parameter == "FeatureAngle":
            return 0,180
        if parameter in ["IsoValue","SurfaceAmnt","SurfaceRangeBegin","SurfaceRangeEnd"]:
            return self.scalarRange
        
        return -1,-1
        
    def getDefaultValue(self,parameter):
        """
        Created: 13.04.2006, KP
        Description: Return the default value of a parameter
        """           
        if parameter == "Method":return 1
        if parameter == "Gaussian": return 1
        if parameter == "Normals": return 1
        if parameter == "FeatureAngle": return 45   
        if parameter == "Simplify": return 0
        if parameter == "PreserveTopology": return 1
        if parameter == "IsoValue": return 128
        if parameter == "Transparency": return 0
        if parameter == "SurfaceRangeBegin": return 1
        if parameter == "SurfaceRangeEnd": return 255
        if parameter == "SurfaceAmnt": return 1
        if parameter == "MultipleSurfaces": return 0
            
    def getType(self,parameter):
        """
        Created: 20.07.2006, KP
        Description: Return the type of the parameter
        """   
        if parameter == "Method":return GUIBuilder.CHOICE
        if parameter in ["Gaussian","Normals","PreserveTopology","MultipleSurfaces"]: return types.BooleanType
        if parameter in ["Simplify", "IsoValue","Transparency"]: return GUIBuilder.SLICE
        if parameter in ["SurfaceRangeBegin","SurfaceRangeEnd","SurfaceAmnt","FeatureAngle"]: return GUIBuilder.SPINCTRL
                

        
    def setDataUnit(self,dataunit):
        """
        Created: 28.04.2005, KP
        Description: Sets the dataunit this module uses for visualization
        """       
        VisualizationModule.setDataUnit(self,dataunit)
#        self.data=self.dataUnit.getTimePoint(0)
        
    def showTimepoint(self, value, update=1):
        """
        Created: 06.11.2006, KP
        Description: Show the given timepoint
        """
        VisualizationModule.showTimepoint(self,value,update)
        min,max=self.data.GetScalarRange()
        #if (min,max) != self.scalarRange:
        self.setScalarRange(min,max)
                

    def setMethod(self,method):
        """
        Created: 28.04.2005, KP
        Description: Set the Rendering method used
        """             
        self.method=method
        if method<3:
            #Ray Casting, RGBA Ray Casting, Texture Mapping, MIP
            filters = [vtk.vtkContourFilter,vtk.vtkMarchingCubes,vtk.vtkDiscreteMarchingCubes]
            Logging.info("Using ",filters[method],"as  contourer",kw="visualizer")
            self.contour = filters[method]()
            if self.volumeModule:
                self.volumeModule.disableRendering()
                self.volumeModule = None
                self.enableRendering()
        else:
            Logging.info("Using volume rendering for isosurface")
            self.disableRendering()
            if not self.volumeModule:
                self.volumeModule = Volume.VolumeModule(self.parent,self.visualizer,moduleName="Volume",label="Volume")
                self.volumeModule.setMethod(Volume.ISOSURFACE)
                self.volumeModule.setDataUnit(self.dataUnit)
            self.volumeModule.showTimepoint(self.timepoint)

    def updateRendering(self):
        """
        Created: 28.04.2005, KP
        Description: Update the Rendering of this module
        """           
        method = self.parameters["Method"]
        self.setMethod(method)

        if self.volumeModule:
            self.volumeModule.function.SetIsoValue(self.parameters["IsoValue"])
            self.volumeModule.showTimepoint(self.timepoint)
            return
        if not self.init:
            self.init=1
            self.mapper.ColorByArrayComponent(0,0)
        self.mapper.AddObserver("ProgressEvent",self.updateProgress)
        dataUnit = self.getInputDataUnit(1)
        if not dataUnit:
            dataUnit = self.dataUnit
        self.mapper.SetLookupTable(dataUnit.getColorTransferFunction())
        self.mapper.ScalarVisibilityOn()
        
        min,max=self.data.GetScalarRange()
        #if (min,max) != self.scalarRange:
        self.setScalarRange(min,max)
        
        
        self.mapper.SetScalarRange(min,max)
        self.mapper.SetColorModeToMapScalars()
        
        opacity = self.parameters["Transparency"]
        opacity = (100-opacity)/100.0
        Logging.info("Using opacity ",  opacity,kw="visualizer")
        if opacity != 1:
            cullers = self.parent.getRenderer().GetCullers()
            cullers.InitTraversal()
            culler = cullers.GetNextItem()
            culler.SetSortingStyleToBackToFront()
        
        self.actor.GetProperty().SetOpacity(opacity)
        input = self.getInput(1)
        if self.parameters["Gaussian"]:
            Logging.info("Doing gaussian smoothing",kw="visualizer")
            if not self.smooth:
                self.smooth=vtk.vtkImageGaussianSmooth()
            self.smooth.SetInput(input)
            input=self.smooth.GetOutput()
        
        x,y,z = self.dataUnit.getDimensions()
        input = bxd.mem.optimize(image = input, updateExtent = (0,x-1,0,y-1,0,z-1))
        self.contour.SetInput(input)
        input=self.contour.GetOutput()
        
        multi = self.parameters["MultipleSurfaces"]

        
        if not multi:
            self.contour.SetValue(0,self.parameters["IsoValue"])
        else:
            begin,end,n=self.parameters["SurfaceRangeBegin"], self.parameters["SurfaceRangeEnd"],self.parameters["SurfaceAmnt"]
            Logging.info("Generating %d values in range %d-%d"%(n,begin,end),kw="visualizer")            
            self.contour.GenerateValues(n,begin,end)
        
        decimateLevel = self.parameters["Simplify"]
        preserveTopology = self.parameters["PreserveTopology"]
        if decimateLevel != 0:            
            self.decimate.SetPreserveTopology(preserveTopology)
            if not preserveTopology:
                self.decimate.SplittingOn()
                self.decimate.BoundaryVertexDeletionOn()
            else:
                self.decimate.SplittingOff()
                self.decimate.BoundaryVertexDeletionOff()
            self.decimate.SetTargetReduction(decimateLevel/100.0)
            
            Logging.info("Decimating %.2f%%, preserve topology: %s"%(decimateLevel,preserveTopology),kw="visualizer")
            self.decimate.SetInput(input)
            input=self.decimate.GetOutput()
        
        if self.parameters["Normals"]:
            angle = self.parameters["FeatureAngle"]
            Logging.info("Generating normals at angle",angle,kw="visualizer")
            self.normals.SetFeatureAngle(angle)
            self.normals.SetInput(input)
            input=self.normals.GetOutput()

        
        self.mapper.SetInput(input)
        VisualizationModule.updateRendering(self,input)
        #self.mapper.Update()
        self.parent.Render()    

    def __getstate__(self):
        """
        Method: __getstate__
        Created: 02.08.2005, KP
        Description: A getstate method that saves the lights
        """            
        odict=VisualizationModule.__getstate__(self)
        odict.update({"mapper":self.getVTKState(self.mapper)})
        odict.update({"actor":self.getVTKState(self.actor)})
        odict.update({"renderer":self.getVTKState(self.renderer)})
        odict.update({"camera":self.getVTKState(self.renderer.GetActiveCamera())})
        odict.update({"method":self.method})
        
        odict.update({"generateNormals":self.generateNormals,
                      "isoValue":self.isoValue,
                      "contourRange":self.contourRange,
                      "opacity":self.opacity,
                      "decimateLevel":self.decimateLevel,
                      "preserveTopology":self.preserveTopology})
        return odict
        
    def __set_pure_state__(self,state):
        """
        Created: 02.08.2005, KP
        Description: Set the state of the light
        """        
        #print "\n\n\n__set_pure_state__\n\n\n"
        self.setVTKState(self.mapper,state.mapper)
        self.setVTKState(self.actor,state.actor)
        self.setVTKState(self.renderer,state.renderer)
        self.setVTKState(self.renderer.GetActiveCamera(),state.camera)
        self.setMethod(state.method)
        self.generateNormals = state.generateNormals
        print "state.isoValue=",state.isoValue
        self.isoValue = state.isoValue
        
        self.contourRange = state.contourRange
        self.opacity = state.opacity
        if state.decimateLevel:
            self.setDecimate(state.decimateLevel,state.preserveTopology)
        
        VisualizationModule.__set_pure_state__(self,state)        


class SurfaceConfiguration(ModuleConfiguration):
    def __init__(self,parent,visualizer):
        """
        Created: 28.04.2005, KP
        Description: Initialization
        """     
        ModuleConfiguration.__init__(self,parent,"Surface rendering")
        self.panel=SurfaceConfigurationPanel(self,visualizer)
        self.method=0

class SurfaceConfigurationPanel(ModuleConfigurationPanel):
    def __init__(self,parent,visualizer,name="Surface rendering",**kws):
        """
        Created: 28.04.2005, KP
        Description: Initialization
        """     
        ModuleConfigurationPanel.__init__(self,parent,visualizer,name,**kws)
        self.method=0
        
    def setModule(self,module):
        """
        Created: 28.04.2005, KP
        Description: Set the module to be configured
        """  
        ModuleConfigurationPanel.setModule(self,module)
        self.module.sendUpdateGUI()
        
    def onApply(self,event):
        """
        Created: 30.04.2005, KP
        Description: Apply the changes
        """     
        ModuleConfigurationPanel.onApply(self,event)
            
        self.module.updateData()
        self.module.updateRendering()
        
    def onSelectMethod(self,event):
        """
        Created: 30.04.2005, KP
        Description: Select the surface rendering method
        """  
        self.method = self.moduleChoice.GetSelection()
        flag=(self.method!=3)
        self.isoRangeBegin.Enable(flag)
        self.isoRangeEnd.Enable(flag)
        self.isoRangeSurfaces.Enable(flag)

    def initializeGUI(self):
        """
        Created: 28.04.2005, KP
        Description: Initialization
        """          
        pass
        
    def setModule(self,module):
        """
        Created: 28.04.2005, KP
        Description: Set the module to be configured
        """  
        ModuleConfigurationPanel.setModule(self,module)
        #print "module=",module
        self.module=module
        self.gui = GUIBuilder.GUIBuilder(self, self.module)
        
        self.contentSizer.Add(self.gui,(0,0))
        
        self.module.setScalarRange(*self.module.scalarRange)
        self.module.sendUpdateGUI()
