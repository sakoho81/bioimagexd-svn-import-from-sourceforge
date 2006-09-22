#! /usr/bin/env python
# -*- coding: iso-8859-1 -*-
"""
 Unit: GUIBuilder
 Project: BioImageXD
 Created: 15.04.2006, KP
 Description:

 A module containing the classes for building a GUI for all the manipulation filters
                            
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

import wx
import types
import Histogram
import wx.lib.buttons as buttons
import  wx.lib.filebrowsebutton as filebrowse

import messenger
import Logging
import scripting as bxd

RADIO_CHOICE="RADIO_CHOICE"
THRESHOLD="THRESHOLD"
PIXEL="PIXEL"
PIXELS="PIXELS"
SLICE="SLICE"
FILENAME="FILENAME"
CHOICE="CHOICE"
SPINCTRL="SPINCTRL"
NOBR="NOBR"
BR="BR"
ROISELECTION="ROISELECTION"

class GUIBuilderBase:
    """
    Created: 31.05.2006, KP
    Description: A base class for modules that intend to use GUI builder
    """ 
    def __init__(self, changeCallback):
        """
        Method: __init__()
        Created: 13.04.2006, KP
        Description: Initialization
        """
        self.parameters = {}
        self.gui = None
        self.modCallback = changeCallback
        for item in self.getPlainParameters():
            self.setParameter(item,self.getDefaultValue(item))
            
    def sendUpdateGUI(self):
        """
        Created: 05.06.2006, KP
        Description: Method to update the GUI for this filter
        """          
        for item in self.getPlainParameters():
            value = self.getParameter(item)
#            print "set_parameter",item,value
            messenger.send(self,"set_%s"%item,value)

    
    def canSelectChannels(self):
        """
        Created: 31.05.2006, KP
        Description: Should it be possible to select the channel
        """          
        return 1
    
    def getParameters(self):
        """
        Created: 13.04.2006, KP
        Description: Return the list of parameters needed for configuring this GUI
        """  
        return []
    
    def getPlainParameters(self):
        """
        Created: 15.04.2006, KP
        Description: Return whether this filter is enabled or not
        """
        ret=[]
        for item in self.getParameters():
            # If it's a label
            if type(item)==types.StringType:
                continue
            elif type(item)==types.ListType:
                title,items=item
                if type(items[0]) == types.TupleType:
                    items=items[0]
                ret.extend(items)
        return ret
        
    def setParameter(self,parameter,value):
        """
        Created: 13.04.2006, KP
        Description: Set a value for the parameter
        """    
        self.parameters[parameter]=value
        if self.modCallback:
            self.modCallback(self)
#
    def getParameter(self,parameter):
        """
        Created: 29.05.2006, KP
        Description: Get a value for the parameter
        """    
        if parameter in self.parameters:
            return self.parameters[parameter]
        return None
        
    def getDesc(self,parameter):
        """
        Created: 13.04.2006, KP
        Description: Return the description of the parameter
        """    
        try:
            return self.descs[parameter]
        except:            
            return ""
        
    def getLongDesc(self,parameter):
        """
        Created: 13.04.2006, KP
        Description: Return the long description of the parameter
        """    
        return ""
        
    def getType(self,parameter):
        """
        Created: 13.04.2006, KP
        Description: Return the type of the parameter
        """    
        return types.IntType
        
    def getRange(self, parameter):
        """
        Created: 31.05.2006, KP
        Description: If a parameter has a certain range of valid values, the values can be queried with this function
        """           
        return -1,-1
        
    def getDefaultValue(self,parameter):
        """
        Created: 13.04.2006, KP
        Description: Return the default value of a parameter
        """           
        return 0


class GUIBuilder(wx.Panel):
    """
    Created: 13.04.2006, KP
    Description: A GUI builder for the manipulation filters
    """      
    def __init__(self,parent,myfilter):
        """
        Created: 13.04.2006, KP
        Description: Initialization
        """ 
        wx.Panel.__init__(self,parent,-1)
        self.filter = myfilter
        self.sizer = wx.GridBagSizer()
        # store the histograms so that the filters can access them if they need
        # to
        self.histograms=[]
        
        self.buildGUI(myfilter)
        self.SetSizer(self.sizer)
        self.SetAutoLayout(1)
        
    def getSizerPosition(self):
        """
        Created: 07.06.2006, KP
        Description: Return the position in the sizer where the user can add more stuff
        """ 
        return (1,0)
        
    def buildGUI(self,currentFilter):
        """
        Created: 13.04.2006, KP
        Description: Build the GUI for a given filter
        """ 
        self.currentFilter = currentFilter
        parameters = currentFilter.getParameters()
        gy=0
            
        sbox=wx.StaticBox(self,-1,currentFilter.getName())
        sboxsizer=wx.StaticBoxSizer(sbox,wx.VERTICAL)
        self.sizer.Add(sboxsizer,(0,0))
        sizer=wx.GridBagSizer()
        sboxsizer.Add(sizer)
        
        if currentFilter.canSelectChannels():
            chlSel = self.buildChannelSelection()
        
            sizer.Add(chlSel,(gy,0),span=(1,2))
        
            gy+=1
        nobr = 0
        cx=0
        for param in parameters:

            # If it's a list with header name and items
            if type(param) == types.ListType:
                sboxname,items = param
                itemsizer = wx.GridBagSizer()

                y=-1
                skip=0
                for n,item in enumerate(items):
                    if item == NOBR:
                        nobr = 1
                        continue

                    if skip:
                        skip-=1
                        continue
                    itemName=item
                    isTuple=0
                    if type(item)==types.TupleType:
                        itemType = currentFilter.getType(item[0])
                        itemName=item[0]
                        isTuple=1
                    else:
                        itemType = currentFilter.getType(item)
                    print "item=",item,"param=",param
                    print "itemType=",itemType,"isTuple=",isTuple
                    
                    print "items=",items
                    
                    if not (isTuple and itemType == types.BooleanType) and itemType not in [RADIO_CHOICE, SLICE, PIXEL, PIXELS, THRESHOLD, FILENAME, CHOICE, ROISELECTION]:
                        if not nobr:
                            y+=1
                            cx=0
                        else:
                            nobr = 0
                            cx+=1
                        cx, y = self.processItem(currentFilter,itemsizer,item,x=cx,y=y)
                        
                    else: # Items that are contained in a tuple ask to be grouped
                          # together
                        if not nobr:
                            y+=1
                        print "cx=",cx,"y=",y
                        if itemType == RADIO_CHOICE:
                            # Indicate that we need to skip next item
                            skip=1
                            print item
                            print "Creating radio choice"
                            if items[n+1][0] == "cols":
                                majordim=wx.RA_SPECIFY_COLS
                            else:
                                majordim=wx.RA_SPECIFY_ROWS
                            
                            choices=[]
                            itemToDesc={}
                            funcs=[]
                            for i in item:
                                d = currentFilter.getDesc(i)
                                itemToDesc[i]=d
                                choices.append(d)
                                f=lambda obj,evt,arg, box, i=i, s=self: s.onSetRadioBox(box,i,arg)
                                funcs.append(("set_%s"%i,f))
                                

                            
                            box = wx.RadioBox(self,-1,sboxname,choices=choices,
                            majorDimension = items[n+1][1],style=majordim)
                            for funcname,f in funcs:
                                f2=lambda obj,evt,arg,box=box:f(obj,evt,arg,box)
                                messenger.connect(currentFilter,funcname,f2)
                            box.itemToDesc=itemToDesc
                            func=lambda evt,its=item,f=currentFilter:self.onSelectRadioBox(evt,its,f)
                                
                                
                            box.Bind(wx.EVT_RADIOBOX,func)
                            sboxname=""
                            itemsizer.Add(box,(0,0))
                        elif itemType == SLICE:
                            text = currentFilter.getDesc(itemName)
                            box = wx.BoxSizer(wx.VERTICAL)
                            lbl = wx.StaticText(self,-1,text)
                            box.Add(lbl)
                            
                            val = currentFilter.getDefaultValue(itemName)
                            minval,maxval = currentFilter.getRange(itemName)
                            print "Value for ",itemName,"=",val,"range=",minval,maxval
                            x=200
                            slider = wx.Slider(self,-1, value=val, minValue=minval, maxValue=maxval,
                            style = wx.SL_HORIZONTAL|wx.SL_LABELS|wx.SL_AUTOTICKS,
                            size=(x,-1))
                            func = lambda evt, its=item, f=currentFilter:self.onSetSliderValue(evt,its,f)
                            slider.Bind(wx.EVT_SCROLL,func)
                            f=lambda obj,evt,arg, slider=slider, i=itemName, s=self: s.onSetSlice(slider,i,arg)
                                

                            messenger.connect(currentFilter,"set_%s"%itemName,f)

                            def updateRange(currentFilter,itemName, slider):
                                minval,maxval = currentFilter.getRange(itemName)
                                slider.SetRange(minval,maxval)

                            
                            f = lambda obj,evt, slider=slider, i=itemName,fi=currentFilter,s=self: updateRange(fi,i,slider)
                            messenger.connect(currentFilter,"update_%s"%itemName,f)
                            
                            box.Add(slider,1)
                            print "Adding box to ",y,0
                            itemsizer.Add(box,(y,0),flag=wx.EXPAND|wx.HORIZONTAL)
                            y+=1
                        elif itemType == FILENAME:
                            # Indicate that we need to skip next item
                            skip=2
                        
                            box = wx.BoxSizer(wx.VERTICAL)
                            text = currentFilter.getDesc(itemName)
                            val = currentFilter.getDefaultValue(itemName)
                    
                            func = lambda evt, its=item,f=currentFilter, i = itemName, s = self: s.onSetFileName(f, i, evt)

                            browse = filebrowse.FileBrowseButton(self, -1, size=(400,-1),
                            labelText = text, fileMask = items[n][2],
                            dialogTitle = items[n][1],
                            changeCallback = func)
                            browse.SetValue(val)
                            f=lambda obj,evt,arg, b=browse, i=itemName, s=self: s.onSetFileNameFromFilter(b,i,arg)
                            messenger.connect(currentFilter,"set_%s"%itemName,f) 
                            
                            box.Add(browse,1)                            
                            itemsizer.Add(box,(y,0),flag = wx.EXPAND|wx.HORIZONTAL)
                            y+=1
                        elif itemType == CHOICE:
                            box = wx.BoxSizer(wx.VERTICAL)
                            text = currentFilter.getDesc(itemName)
                            val = currentFilter.getDefaultValue(itemName)
                            
                            lbl = wx.StaticText(self,-1,text)
                            box.Add(lbl)

                            choices = currentFilter.getRange(itemName)
                            func = lambda evt, its=item,f=currentFilter, i = itemName, s = self: s.onSetChoice(f, i, evt)
                            choice = wx.Choice(self,-1,choices=choices)
                            
                            choice.SetSelection(val)
                            choice.Bind(wx.EVT_CHOICE,func)
                            
                            f=lambda obj,evt,arg, c=choice, i=itemName, s=self: s.onSetChoiceFromFilter(c,i,arg)
                            messenger.connect(currentFilter,"set_%s"%itemName,f) 
                            
                            
                            box.Add(choice,1)
                            itemsizer.Add(box,(y,0),flag=wx.EXPAND|wx.HORIZONTAL)
                            y+=1
                        elif itemType == ROISELECTION:
                            box = wx.BoxSizer(wx.VERTICAL)
                            text = currentFilter.getDesc(itemName)
                            val = 0
                            
                            lbl = wx.StaticText(self,-1,text)
                            box.Add(lbl)
                            rois = bxd.visualizer.getRegionsOfInterest()
                            choices = [x.getName() for x in rois]
                            
                            def updateROIs(currentFilter,itemName, choice):
                                rois = bxd.visualizer.getRegionsOfInterest()
                                choices = [x.getName() for x in rois]       
                                choice.Clear()                            
                                
                                choice.AppendItems(choices)
                            
                            func = lambda evt, its=item,f=currentFilter, i = itemName, r = rois, s = self: s.onSetROI(r,f, i, evt)
                            choice = wx.Choice(self,-1,choices=choices)
                            
                            choice.SetSelection(val)
                            choice.Bind(wx.EVT_CHOICE,func)
                            
                            f = lambda obj,evt, choice=choice, i=itemName,fi=currentFilter,s=self: updateROIs(fi,i,choice)
                            messenger.connect(currentFilter,"update_%s"%itemName,f)                            
                            messenger.connect(None,"update_annotations",f)
                            
                            #f=lambda obj,evt,arg, c=choice, i=itemName, s=self: s.onSetROIFromFilter(c,i,arg)
                            #messenger.connect(currentFilter,"set_%s"%itemName,f) 
                            
                            
                            box.Add(choice,1)
                            itemsizer.Add(box,(y,0),flag=wx.EXPAND|wx.HORIZONTAL)
                            y+=1
                            
                        elif itemType == PIXEL:
                            print "Creating pixel selection"
                            lbl = wx.StaticText(self,-1,"(%d,%d,%d)"%(0,0,0),size=(80,-1))
                            btn = wx.Button(self,-1,"Set seed")
                            def f(l):
                                l.selectPixel=1
                            func=lambda evt,l=lbl:f(l)
                            btn.Bind(wx.EVT_BUTTON,func)
                            box=wx.BoxSizer(wx.HORIZONTAL)
                            box.Add(lbl)
                            box.Add(btn)
                            itemsizer.Add(box,(0,0))
                            func = lambda obj,evt,rx,ry,rz,scalar,rval,gval,bval,r,g,b,alpha,currentCt,its=item,f=currentFilter:self.onSetPixel(obj,evt,rx,ry,rz,r,g,b,alpha,currentCt,its,f,lbl)
                            messenger.connect(None,"get_voxel_at",func)

                            f=lambda obj,evt,arg, lbl=lbl, i=itemName, s=self: s.onSetPixelFromFilter(lbl,i,arg)
                            messenger.connect(currentFilter,"set_%s"%itemName,f)

                            
                        elif itemType == PIXELS:
                            print "Creating multiple pixels selection"
                            pixelsizer = wx.GridBagSizer()
                            seedbox = wx.ListBox(self,-1,size=(150,150))
                            pixelsizer.Add(seedbox,(0,0),span=(2,1))
                            
                            addbtn = wx.Button(self,-1,"Add seed")
                            def f2(l):
                                l.selectPixel=1
                            func=lambda evt,l=seedbox:f2(l)
                            addbtn.Bind(wx.EVT_BUTTON,func)
                            pixelsizer.Add(addbtn,(0,1))
                            print "ITEM=",item
                            rmbtn = wx.Button(self,-1,"Remove")
                            seedbox.itemName = item
                            func=lambda evt,its=item,f=currentFilter:self.removeSeed(seedbox,f)
                            rmbtn.Bind(wx.EVT_BUTTON,func)
                            pixelsizer.Add(rmbtn,(1,1))
                            
                            #obj,event,x,y,z,scalar,rval,gval,bval,r,g,b,a,ctf)
                            func = lambda obj,evt,rx,ry,rz,scalar,rval,gval,bval,r,g,b,alpha,currentCt,its=item,f=currentFilter:self.onAddPixel(obj,evt,rx,ry,rz,r,g,b,alpha,currentCt,its,f,seedbox)
                            messenger.connect(None,"get_voxel_at",func)
                            itemsizer.Add(pixelsizer,(0,0))                            
                            f=lambda obj,evt,arg, seedbox=seedbox, i=itemName, s=self: s.onSetPixelsFromFilter(seedbox,i,arg)
                            messenger.connect(currentFilter,"set_%s"%itemName,f)                                                        
                            
                        elif itemType == THRESHOLD:
                            print "Creating threshold selection"
                            histogram = Histogram.Histogram(self)
                            self.histograms.append(histogram)
                            func=lambda evt,its=item,f=currentFilter:self.onSetThreshold(evt,its,f)
                            histogram.Bind(Histogram.EVT_SET_THRESHOLD,func)
                            
                            histogram.setThresholdMode(1)
                            du=self.filter.getDataUnit().getSourceDataUnits()[0]
                            print "Connecting",item[0],item[1]
                            flo=lambda obj,evt,arg, histogram=histogram, i=item[0], s=self: s.onSetHistogramValues(histogram,i,arg,valuetype="Lower")
                            messenger.connect(currentFilter,"set_%s"%item[0],flo)
                            fhi=lambda obj,evt,arg, histogram=histogram, i=item[1], s=self: s.onSetHistogramValues(histogram,i,arg,valuetype="Upper")
                            messenger.connect(currentFilter,"set_%s"%item[1],fhi)
                            
                            histogram.setDataUnit(du,noupdate=1)
                            itemsizer.Add(histogram,(0,0))
                        else:
                            groupsizer=wx.GridBagSizer()
                            x=0
                            for it in item:
                                self.processItem(currentFilter, groupsizer, it, x=x,y=0)
                                x+=1
                            span=(1,x)
                            itemsizer.Add(groupsizer,(y,0),span=span)
                            # If the name is an empty string, don't create a static box around
                
                # the items
                if sboxname:
                    sbox = wx.StaticBox(self,-1,sboxname)
                    sboxsizer=wx.StaticBoxSizer(sbox,wx.VERTICAL)
                
                    sizer.Add(sboxsizer,(gy,0),flag=wx.EXPAND)
                    sboxsizer.Add(itemsizer)
                else:
                    sizer.Add(itemsizer,(gy,0),flag=wx.EXPAND)            
            # If it's just a header name
            elif type(param) == types.StringType:
                lbl = wx.StaticText(self,-1,param)
                sizer.Add(lbl,(gy,0))
            gy+=1
        
    def buildChannelSelection(self):
        """
        Created: 17.04.2006, KP
        Description: Build a GUI for selecting the source channels
        """                     
        chmin,chmax = self.currentFilter.getNumberOfInputs()
        sizer = wx.GridBagSizer()
        y=0
        choices=["Input from filter stack"]
        for i,dataunit in enumerate(self.currentFilter.dataUnit.getSourceDataUnits()):
            choices.append(dataunit.getName())
        
        
        for i in range(1,chmax+1):
            lbl = wx.StaticText(self,-1,self.currentFilter.getInputName(i))
            sizer.Add(lbl,(y,0))
            chlChoice = wx.Choice(self,-1,choices=choices)
            sizer.Add(chlChoice,(y,1))
            chlChoice.SetSelection(i-1)
            self.currentFilter.setInputChannel(i,i-1)
            
            func=lambda evt,f=self.currentFilter,n=i: self.onSetInputChannel(f,n,evt)
            chlChoice.Bind(wx.EVT_CHOICE,func)

            y+=1
        return sizer
        
    def onSetChoice(self, filter, item, evt):
        """
        Created: 20.07.2006, KP
        Description: Set the parameter to the value of the choice widget
        """           
        value = evt.GetSelection()
        print "Setting parameter",item,"to",value
        filter.setParameter(item, value)        
        
    def onSetROI(self, rois, filter, item, evt):
        """
        Created: 20.07.2006, KP
        Description: Set the parameter to the ROI corresponding to the value of the choice widget
        """           
        value = evt.GetSelection()
        rois = bxd.visualizer.getRegionsOfInterest()
        filter.setParameter(item, (value,rois[value]))        
                
        
    def onSetFileName(self, filter, item, evt):
        """
        Method: onSetFileName
        Created: 12.07.2006, KP
        Description: Set the file name
        """           
        filename= evt.GetString()
        print "Setting parameter",item,"to",filename
        filter.setParameter(item, filename)
        
    def onSetChoiceFromFilter(self, cc, itemName, value):
        """
        Method: onSetChoiceFromFilter
        Created: 12.07.2006, KP
        Description: Set the file name
        """           
        cc.SetSelection(value)
    
        

    def onSetFileNameFromFilter(self, bb, itemName, value):
        """
        Method: onSetFileName
        Created: 12.07.2006, KP
        Description: Set the file name
        """           
        bb.SetValue(value)
        print "Setting value of filebrowse to",value
        
    def onSetRadioBox(self,box,item,value):
        """
        Method: onSetRadioBox
        Created: 05.06.2006, KP
        Description: Set the value for the GUI item 
        """         
        sval = box.itemToDesc[item]
        print "setradiobox",item,value
        if value:
            box.SetStringSelection(sval)
        
    def onSetSlice(self,slider,item,value):
        """
        Method: onSetSlice
        Created: 05.06.2006, KP
        Description: Set the value for the GUI item 
        """                 
        
        slider.SetValue(value)

    def onSetSpinFromFilter(self,spin,item,value):
        """
        Method: onSetSpinFromFilter
        Created: 21.06.2006, KP
        Description: Set the value for the GUI item 
        """                         
        spin.SetValue(value)

    def onSetInputChannel(self,currentFilter,inputNum,evt):
        """
        Created: 17.04.2006, KP
        Description: Set the input channel number #inputNum
        """              
        n = evt.GetSelection()
        self.currentFilter.setInputChannel(inputNum,n)
        
    def processItem(self,currentFilter, itemsizer, item, x,y):
        """
        Method: processItem
        Created: 15.04.2006, KP
        Description: Build the GUI related to one specific item
        """              
        desc = currentFilter.getDesc(item)
        
        itemType = currentFilter.getType(item)
        br = 0        
        if desc and desc[-1]=='\n':
            desc=desc[:-1]
            br = 1
        if  desc and itemType not in [types.BooleanType]:
            lbl = wx.StaticText(self,-1,desc)
        else:
            lbl = None
        defaultValue = currentFilter.getDefaultValue(item)
        
        if itemType in [types.IntType,types.FloatType]:
            input = self.createNumberInput(currentFilter, item, itemType, defaultValue, desc)
        elif itemType == types.BooleanType:
            input = self.createBooleanInput(currentFilter, item, itemType, defaultValue, desc)
        elif itemType == SPINCTRL:
            input  = self.createSpinInput(currentFilter, item, itemType, defaultValue, desc)
        else:
            raise "Unrecognized input type: %s"%str(itemType)
        txt = currentFilter.getLongDesc(item)
        if txt:
            input.SetHelpText(txt)

        x2=x
        if lbl:
            print "Adding label",desc," to ",(x,y)
            itemsizer.Add(lbl,(y,x))
            if not br:
                x2+=1
            else:
                y+=1
        print "Adding input to",x2,y
        itemsizer.Add(input,(y,x2))
        if br:
            y+=1
        return (x,y)
                        
    def createNumberInput(self,currentFilter,item,itemType,defaultValue,label = ""):
        """
        Method: createIntInput
        Created: 15.04.2006, KP
        Description: Return the input for int type
        """        
        input = wx.TextCtrl(self,-1,str(defaultValue))
        valid=lambda evt,f=currentFilter,p=item,t=itemType,i=input:self.validateAndPassOn(evt,i,p,itemType,f)
        input.Bind(wx.EVT_TEXT,valid)
        f=lambda obj,evt,arg, input=input, it=item, s=self: s.onSetNumber(input,it,arg)
        messenger.connect(currentFilter,"set_%s"%item,f)

        return input
        
                        
    def createSpinInput(self,currentFilter,itemName,itemType,defaultValue,label = ""):
        """
        Created: 15.04.2006, KP
        Description: Return the input for int type
        """        
        minval,maxval = currentFilter.getRange(itemName)
        
        spin = wx.SpinCtrl(self,-1, style=wx.SP_VERTICAL)
        func = lambda evt, its=itemName, sp=spin, f=currentFilter:self.onSetSpinValue(evt,sp,its,f)
        spin.Bind(wx.EVT_SPINCTRL,func)
        spin.Bind(wx.EVT_TEXT,func)
        
        f=lambda obj,evt,arg, spin=spin, i=itemName, s=self: s.onSetSpinFromFilter(spin,i,arg)
            
        messenger.connect(currentFilter,"set_%s"%itemName,f)

        def updateRange(currentFilter,itemName, spin):
            minval,maxval = currentFilter.getRange(itemName)
            Logging.backtrace()
            print "\n\n\n**** SET SPIN RANGE",minval,maxval
            spin.SetRange(minval,maxval)
        
        f = lambda obj,evt, spin=spin, i=itemName,fi=currentFilter,s=self: updateRange(fi,i,spin)
        messenger.connect(currentFilter,"update_%s"%itemName,f)
        
        return spin
        
    def onSetNumber(self, input, item, value):
        """
        Method: onSetNumber
        Created: 05.06.2006, KP
        Description: Set the value for the GUI item
        """             
        #print input,item,value
        input.SetValue(str(value))
    def onSetBool(self, input, item, value):
        """
        Method: onSetBool
        Created: 05.06.2006, KP
        Description: Set the value for the GUI item
        """             
        #print input,item,value
        input.SetValue(value)
    
    def createBooleanInput(self,currentFilter,item,itemType,defaultValue, label = ""):
        """
        Method: createBooleanInput
        Created: 15.04.2006, KP
        Description: Return the input for boolean type
        """        
        input = wx.CheckBox(self,-1,label)
        input.SetValue(defaultValue)
        valid=lambda evt,f=currentFilter,p=item,t=itemType,i=input:self.validateAndPassOn(evt,i,p,itemType,f)
        input.Bind(wx.EVT_CHECKBOX,valid)
        f=lambda obj,evt,arg, input=input, i=item, s=self: s.onSetBool(input,i,arg)
        messenger.connect(currentFilter,"set_%s"%item,f)       
        return input
        
    def removeSeed(self,listbox,currFilter):
        """
        Method: removeSeed
        Created: 29.05.2006, KP
        Description: Remove a seed from filter
        """         
        item=listbox.itemName
        print "item in removeSeed=",item
        n = listbox.GetSelection()
        if n != wx.NOT_FOUND:
            s = listbox.GetString(n)
            seedpt = eval(s)
            listbox.Delete(n)
            
        print "Getting parameter",item[0]
        seeds = currFilter.getParameter(item[0])   
        print "Removing ",seedpt,"from ",seeds
        seeds.remove(seedpt)
        currFilter.setParameter(item[0],seeds)

    def onAddPixel(self,obj,evt,rx,ry,rz,r,g,b,alpha,ctf,item,currFilter,listbox):
        """
        Method: onAddPixel
        Created: 29.05.2006, KP
        Description: Add a value to the pixel listbox
        """             
        #print "Set pixel",obj,evt,rx,ry,rz,r,g,b,alpha,item,currFilter
        print "item=",item
        if listbox.selectPixel:
            seeds = currFilter.getParameter(item[0])
            seeds.append((rx,ry,rz))
            print "Settng parameter",item,"to",seeds            
            
            currFilter.setParameter(item[0],seeds)
            listbox.Append("(%d, %d, %d)"%(rx, ry, rz))            
            listbox.selectPixel = 0

            
    def onSetPixel(self,obj,evt,rx,ry,rz,r,g,b,alpha,ctf,item,currFilter,valuelbl):
        """
        Method: onSetPixel
        Created: 26.05.2006, KP
        Description: Set the value of the pixel label
        """             
        #print "Set pixel",obj,evt,rx,ry,rz,r,g,b,alpha,item,currFilter
        if valuelbl.selectPixel:
            print "Settng parameter",item,"to",rx,ry,rz
            
            currFilter.setParameter(item[0],(rx,ry,rz))
            valuelbl.SetLabel("(%d, %d, %d)"%(rx,ry,rz))
            valuelbl.selectPixel = 0
            
    def onSetPixelFromFilter(self,label, item, value):
        """
        Method: onSetPixelFromFilter
        Created: 06.06.2006, KP
        Description: Set the value of the pixel label from a variable
        """             
        rx,ry,rz = value
        #print "Set pixel",obj,evt,rx,ry,rz,r,g,b,alpha,item,currFilter
        label.SetLabel("(%d, %d, %d)"%(rx,ry,rz))

    def onSetPixelsFromFilter(self,listbox, item, value):
        """
        Method: onSetPixelsFromFilter
        Created: 06.06.2006, KP
        Description: Set the value of the pixel label from a variable
        """     
        listbox.Clear()
        print value
        for rx,ry,rz in value:
            listbox.Append("(%d, %d, %d)"%(rx,ry,rz))            

    def onSetHistogramValues(self,histogram, item, value,valuetype="Lower"):
        """
        Method: onSetHistogramValues
        Created: 06.06.2006, KP
        Description: Set the lower and upper threshold for histogram
        """             
        eval("histogram.set%sThreshold(value)"%valuetype)

            
    def onSetThreshold(self,evt,items,currentFilter):
        """
        Method: onSelectRadioBox
        Created: 15.04.2006, KP
        Description: Process an event from a radio box
        """      
        thresholds = evt.getThresholds()
        for i,item in enumerate(items):
            currentFilter.setParameter(item,thresholds[i])            
            
    def onSetSliderValue(self,evt,items,currentFilter):
        """
        Method: onSetSliderValue
        Created: 31.05.2006, KP
        Description: Set the slider value
        """      
        value = evt.GetPosition()
        currentFilter.setParameter(items, value)

    def onSetSpinValue(self,evt,spinbox,itemName,currentFilter):
        """
        Method: onSetSpinValue
        Created: 31.05.2006, KP
        Description: Set the spin value
        """      
        value = spinbox.GetValue()
        value = int(value)
        currentFilter.setParameter(itemName, value)
            

            
    def onSelectRadioBox(self,evt,items,currentFilter):
        """
        Method: onSelectRadioBox
        Created: 15.04.2006, KP
        Description: Process an event from a radio box
        """      
        sel = evt.GetSelection()
        
        for i,item in enumerate(items):
            flag=(i==sel)
            currentFilter.setParameter(item,flag)
        
    def validateAndPassOn(self,event,input,parameter,itemType,currentFilter):
        """
        Method: buildGUI
        Created: 13.04.2006, KP
        Description: Build the GUI for a given filter
        """
        if itemType == types.IntType:
            conv=int
        elif itemType == types.FloatType:
            conv=float
        elif itemType == types.BooleanType:
            conv = bool
        try:
            value=conv(input.GetValue())
        except:
            return
        currentFilter.setParameter(parameter,value)
