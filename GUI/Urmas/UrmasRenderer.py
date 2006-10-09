#! /usr/bin/env python
# -*- coding: iso-8859-1 -*-

"""
 Unit: UrmasRenderer
 Project: BioImageXD
 Created: 04.04.2005, KP
 Description:

 URM/AS - The Unified Rendering Manager / Animator for Selli
 
 This is a timeline based GUI for controlling the rendering of datasets. The GUI allows users
 to specify a path for the camera to follow (using Heikki Uuksulainen's MayaVi animator code)
 and also allows them to produce videos of the rendering using ffmpeg.
 
 This module contains the class that takes a datastructure representation
 of the timeline and renders it to a movie or set of images. 
 
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
__version__ = "$Revision: 1.22 $"
__date__ = "$Date: 2005/01/13 13:42:03 $"

import RenderingInterface
from UrmasControl import *
import time
import Dialogs
import wx
import messenger
import Interpolation
import vtk
import math

def distance(p1,p2):
    xd=p1[0]-p2[0]
    yd=p1[1]-p2[1]
    zd=p1[2]-p2[2]
    return math.sqrt(xd*xd+yd*yd+zd*zd)

class UrmasRenderer:
    """
    Class: UrmasRenderer
    Created: 04.04.2005, KP
    Description: This class takes a datastructure representation of the 
                 timeline and renders it to a movie or set of images.
    """
    def __init__(self,control):
        """
        Class: __init__
        Created: 04.04.2005, KP
        Description: Initialization
        """    
        self.control=control
        self.splineEditor=None
        self.renderingInterface = RenderingInterface.getRenderingInterface(1)
        self.renderingInterface.setVisualizer(control.visualizer)

        self.oldTimepoint=-1
        self.spf=1
        self.lastpoint=None
        self.firstpoint = None
        self.lastSplinePoint=None
        
        self.stopFlag=0
        # we need to keep a list of the camera positions
        # so we can ignore the interpolated camera positions
        # if the camera positions are the same (since the interpolated)
        # results will in that case be incorrect
        self.camPositions=[]
        
        self.currTrack=None
        self.lastSplinePosition=None
        messenger.connect(None,"render_time_pos",self.renderPreviewAt)
        messenger.connect(None,"stop_rendering",self.onStopRendering)
        self.pausedRendering=0
        self.rendering=0
        self.pauseFrame = 0
        self.pauseFlag=0
        self.currentIsPreview=0
        self.renderingPreviewFlag=0
        
        messenger.connect(None,"playback_pause",self.onPausePlayback)
        messenger.connect(None,"playback_play",self.onPlayPlayback)
        messenger.connect(None,"playback_stop",self.onStopPlayback)
       
    def onStopPlayback(self,obj,evt,*args):
        """
        Method: onStopPlayback
        Created: 30.1.2006, KP
        Description: A callback to stop rendering if it's currently underway
                     in a preview mode
        """        
        if self.rendering and self.currentIsPreview:
            print "\n\n**** ON STOP PLAYBACK"
            self.stopFlag=1
            self.renderPreviewAt(None,None,0)
            messenger.send(None,"set_preview_mode",0)
            print "\n\nPreview mode ends because preview stopped (btn)"
      
    def onPlayPlayback(self,obj,evt,*args):
        """
        Method: onPlayPlayback
        Created: 30.1.2006, KP
        Description: A callback to resume rendering if it's currently underway
                     but paused
        """  
        
        # If we wered paused, then continue the rendering from where
        # we left off
        if self.rendering and self.pausedRendering:
            print "\n\n*** CONTINUE RENDERING ***\n\n"
            self.pauseFlag=0
            self.doRenderFrames(self.currentIsPreview)
            #if self.currentIsPreview:
            #    messenger.send(None,"set_preview_mode",)
        #But if we weren't rendering, then do a rendering preview
        elif not self.rendering:
            print "\n\ *** RESTART RENDERING ***\n\n\n"
            self.renderingPreviewFlag=1
            
            self.render(self.control,preview=1)
            
            
    def onPausePlayback(self,obj,evt,*args):
        """
        Method: onPausePlayback
        Created: 30.1.2006, KP
        Description: A callback to pause rendering if it's currently underway
        """  
        if self.rendering:
            self.pauseFlag=1
        
    def isPaused(self):
        """
        Method: isPaused
        Created: 30.1.2006, KP
        Description: A query function that tells whether the rendering is paused
        """            
        return self.pausedRendering
        
    def onStopRendering(self,obj,evt,*args):
        """
        Method: onStopRendering
        Created: 30.1.2006, KP
        Description: Stop any rendering we're doing and exit
        """        
        self.stopFlag=1
        if self.renderingPreviewFlag:
            messenger.send(None,"set_preview_mode",0)
            self.renderingPreviewFlag=0
            
    def startAnimation(self,control):
        """
        Method: startAnimation
        Created: 20.04.2005, KP
        Description: Initialize the rendering
        """
        self.control = control
        self.dataUnit = control.getDataUnit()
        data = self.dataUnit.getTimePoint(0)
        #print "Setting dataunit to",self.dataUnit
        self.renderingInterface.setDataUnit(self.dataUnit)
        self.renderingInterface.setCurrentTimepoint(0)
        self.renderingInterface.setTimePoints([0])
        settings = self.dataUnit.getSettings()
#        ctf= settings.get("ColorTransferFunction")
#        self.renderingInterface.doRendering(preview=data,ctf = ctf)

        
    def render(self,control,preview=0,**kws):
        """
        Class: Render(control)
        Created: 04.04.2005, KP
        Description: Render the timeline
        """    
        self.startAnimation(self.control)
        self.lastSplinePosition = None
        renderpath="."
        self.stopFlag=0
        print "\n\n####IS PREVIEW",preview
        self.currentIsPreview=preview
        messenger.send(None,"report_progress_only",self)
        self.control = control
        self.dataUnit = control.getDataUnit()
        self.duration = duration = control.getDuration()
        self.frames = frames = control.getFrames()
        self.spf = duration / float(frames)
        if not preview and not self.renderingInterface.isVisualizationSoftwareRunning():
            Dialogs.showerror(self.control.window,"Cannot render project: visualization software is not running","Visualizer is not running")
            return -1
        if kws.has_key("size"):
            self.renderingInterface.setRenderWindowSize(kws["size"])
        if kws.has_key("renderpath"):renderpath=kws["renderpath"]
        if not preview:
            self.renderingInterface.setOutputPath(renderpath)
            self.renderingInterface.setCurrentTimepoint(0)
            
            self.renwin = self.renderingInterface.getRenderWindow() 
#            print "self.renwin=",self.renwin
            self.ren = self.renderingInterface.getRenderer()
            if self.renderingInterface.isVisualizationModuleLoaded() == False:
                Dialogs.showwarning(self.control.window,"A visualization module needs to be loaded for rendering","No visualization modules loaded")
                return

            if not self.ren:
                Dialogs.showwarning(self.control.window,"No renderer in main render window!! This should not be possible!","Oops!")
                return
#            self.dlg = wx.ProgressDialog("Rendering","Rendering at %.2fs / %.2fs (frame %d / %d)"%(0,0,0,0),maximum = frames, parent = self.control.window)
#            self.dlg.Show()

        self.splineEditor = control.getSplineEditor()
        self.initializeCameraInterpolator()
        if preview:
            cam = self.splineEditor.getCamera()
            self.ren = self.splineEditor.renderer
        else:
            self.ren = self.renderingInterface.getRenderer()
            cam = self.ren.GetActiveCamera()
        self.cam = cam
        #cam.SetViewUp(self.splineEditor.get_camera().GetViewUp())
        
        
#        cam.ComputeViewPlaneNormal()
#        cam.OrthogonalizeViewUp()

        self.doRenderFrames(preview)
        
    def doRenderFrames(self,preview):
        """
        Class: doRenderFrames()
        Created: 31.01.2006, KP
        Description: Method that only does the rendering.
                     This is separate from render() to make it
                     easier to pause/resume rendering
        """ 
        status="Rendering done."
        start=0
        if self.currentIsPreview:
            messenger.send(None,"set_preview_mode",1)
        if self.pausedRendering:
            if self.currentIsPreview:
                messenger.send(None,"set_preview_mode",1)
            print "\n\n --- RESTORING PAUSED POS ",self.pauseFrame
            start=self.pauseFrame
            self.pausedRendering=0
        self.rendering=1
        for n in range(start,self.frames+1):
            print "Now rendering frame ",n,"spf=",self.spf
            if self.stopFlag:
                print "\n\n*** ABORT RENDERING"
                self.stopFlag=0
                
                status = "Rendering aborted at frame %d / %d."%(n,self.frames)
                break
            if self.pauseFlag:
                status = "Rendering paused at frame %d / %d."%(n,self.frames)
                self.pauseFrame = n
                self.pausedRendering = 1
                return
            messenger.send(None,"set_timeslider_value",(n+1))
            self.renderFrame(n,(n+1)*self.spf,self.spf,preview=preview)            
            messenger.send(self,"update_progress",(n+1)/float(self.frames+1),"Rendering frame %d / %d. Time: %.1fs"%(n,self.frames,(n+1)*self.spf))        
        self.rendering=0
        self.pausedRendering = 0
        self.pauseFrame=0
        
        if self.currentIsPreview:
            print "\n\nPreview mode ends because we're at end"
            messenger.send(None,"set_preview_mode",0)
        messenger.send(None,"report_progress_only",None)
        if not preview:
            messenger.send(None,"update_progress",1.0,status)
        else:
            messenger.send(None,"update_progress",1.0,"")
#            self.dlg.Destroy()
        
        messenger.send(None,"rendering_done")
        
    def initializeCameraInterpolator(self):
        """
        Method: initializeCameraInterpolator
        Created: 18.08.2005, KP
        Description: Initialize the camera interpolator if there are keyframes
        """           
        tracks=self.getKeyframes()
        if not tracks:
            self.interpolator = None
            return
        self.interpolator = vtk.vtkCameraInterpolator()
        self.interpolator.SetInterpolationTypeToSpline()
        self.camPositions=[]
        for track in tracks:
            items=track.getItems()
            for item in items[:-1]:
                start,end=item.getPosition()
                campos=item.cam.GetPosition()
                self.camPositions.append((start,campos))
                self.interpolator.AddCamera(start,item.cam)
            # The last item is the end of track-item
            if len(items):
                item=items[-1]
                start,end=item.getPosition()
                campos=item.cam.GetPosition()
                self.camPositions.append((start,campos))                
                self.interpolator.AddCamera(start,item.cam)
        
    def renderPreviewAt(self,evt,obj,timepos):
        """
        Method: renderPreviewAt
        Created: 15.08.2005, KP
        Description: Renders a preview at given time position
        """           
        self.initializeCameraInterpolator()
        if not self.splineEditor:
            self.splineEditor = self.control.getSplineEditor()
        
        ## if the view mode is "camera path", do not render
        #if not self.splineEditor.viewMode:
        #    return
        
        if self.renderingInterface.visualizer.mode=="3d":
            self.renwin = self.renderingInterface.getRenderWindow() 
#            print "self.renwin=",self.renwin
            self.ren = self.renderingInterface.getRenderer()
            self.cam = self.ren.GetActiveCamera()
            do_use_cam=1
        else:
            self.cam = self.splineEditor.getCamera()
            self.ren = self.splineEditor.renderer       
            do_use_cam=0
        duration = self.control.getDuration()
        frames = self.control.getFrames()
        self.spf = duration / float(frames)        
        frame=timepos/self.spf
        if self.pausedRendering:
            print "\n\n\n**** SETTING PAUSE FRAME TO ",frame,"spf=",self.spf
            self.pauseFrame=frame
        self.renderFrame(frame,timepos,self.spf,preview=1,use_cam=do_use_cam) 
        messenger.send(None,"view_camera",self.cam)
         
    def getTimepointAt(self,time):
        """
        Method: getTimepointAt(time)
        Created: 05.04.2005, KP
        Description: Returns the timepoint used at given time
        Parameters:
        time    The current time in the timeline
        """            
        tracks = self.control.timeline.getTimepointTracks()
        timepoint = 0
        for track in tracks:
            for item in track.getItems():
                start,end=item.getPosition()
                if time >= start and time <= end:
                    timepoint = item.getTimepoint()
        return timepoint
        
    def getKeyframes(self):
        """
        Method: getKeyframes
        Created: 18.08.2005, KP
        Description: Return the keyframes if there is a keyframe track
        """
        tracks=self.control.timeline.getKeyframeTracks()
        return tracks
        
    def getSplinepointsAt(self,time,get_first = 0):
        """
        Method: getSplinepointAt(time)
        Created: 05.04.2005, KP
        Description: Returns two splinepoints between wich the camera is located at this time
        Parameters:
        time    The current time in the timeline
        """            
        tracks = self.control.timeline.getSplineTracks()
        points=[]
        first_dict = {}
        for track in tracks:           
            for item in track.getItems():
                start,end=item.getPosition()
                if get_first:
                    first_dict[start] = item
                    break
                #print "time=",time,"item.pos=",start,end
                if time >= start and time <= end:
                    if track != self.currTrack:
                        # Reset camera everytime we switch tracks
                        self.cam.SetFocalPoint(0,0,0)        
                        self.cam.SetViewUp((0,0,1))        
                        self.ren.ResetCamera()

                        self.currTrack=track
                        track.showSpline()
                    return item
                    
        if get_first:
            keys=first_dict.keys()
            if not keys:return None
            return first_dict[min(keys)]
        return None
        
    def renderFrame(self,frame,timepos,spf,preview=0,use_cam=0):
        """
        Method: renderFrame(frame,time)
        Created: 04.04.2005, KP
        Description: This renders a given frame
        Parameters:
        frame   The frame we're rendering
        time    The current time in the timeline
        spf     Seconds per one frame
        """            
        interpolated=0
        pos=None
        if not self.firstpoint:
            self.firstpoint = self.getSplinepointsAt(0, get_first = 1)
        timepoint = self.getTimepointAt(timepos)
        if (not preview) or use_cam:
            Logging.info("Using self.ren as renderer",kw="animator")
            cam = self.ren.GetActiveCamera()
            ren=self.ren
        else:
            Logging.info("Using splineEditor as renderer",kw="animator")
            cam = self.splineEditor.getCamera()
            ren=self.splineEditor.renderer
            
        if not preview and (timepoint != self.oldTimepoint):
            Logging.info("Switching to timepoint",timepoint,kw="animator")
            # Set the timepoint to be used
            self.renderingInterface.setCurrentTimepoint(timepoint)
            # and update the renderer to use the timepoint
            self.renderingInterface.updateDataset()
            self.oldTimepoint = timepoint
        point = self.getSplinepointsAt(timepos)
        minT = -1
        maxT = -1
        if self.interpolator:
            # if we didn't find camera position, maybe we need to use
            # keyframe interpolation
            minT=self.interpolator.GetMinimumT()
            maxT=self.interpolator.GetMaximumT()

        # If we found no splinepoint definining the position
        # and there has been no previous splinepoint
        print "point=",point,"lastpos=",self.lastSplinePosition,"firstpoint=",self.firstpoint
        if (not point) and (not self.lastSplinePosition) and self.firstpoint:
            first_start,first_end = self.firstpoint.getPosition()
            # then if there is no camera interpolator that would define 
            # a timepoint that is earlier than the first splinepoint
            # then we use the splinepoint
            if minT <0 or minT > first_start:
                point = self.firstpoint
                print "*** Using first splinepoint"
            # else we fall back to using the earliest point
            # defined by the camera interpolator
            
                
        if point and not point.isStopped():
                
            p0=point.getPoint()
            #self.dlg.Update(frame,"Rendering at %.2fs / %.2fs (frame %d / %d)"%(timepos,self.duration,frame,self.frames))
            Logging.info("Rendering frame %d using timepoint %d, time is %f"%(frame,timepoint,timepos),kw="animator")
            start,end=point.getPosition()
            # how far along this part of spline we are
            d=timepos-start
            # how long is it in total
            n = end-start
            # gives us a percent of the length we've traveled
            percentage = d/float(n)
            #print "time %.2f is %.3f%% between %.2f and %.2f"%(timepos,percentage,start,end)
            n=point.getItemNumber()
            p,pos = self.control.splineEditor.getCameraPosition(n,p0,percentage)
            x,y,z=pos
            self.lastSplinePosition=(x,y,z)

            self.lastSplinePoint=point
            
        elif point:
            Logging.info("Camera is motionless, using last position",kw="animator")
            x,y,z=self.lastSplinePosition
            point=(x,y,z)
        else:
                
                # We use this so that the camera point is always defined, 
                # if nothing else was found for the item
                if timepos < minT:
                    timepos=minT
                    print "*** Using first interpolated point!"
                    print "point=",point,"lastpos=",self.lastSplinePosition,"firstpoint=",self.firstpoint
                #print "maxT=",maxT,"timepos=",timepos
                if minT <= timepos and maxT >= timepos:
                    interpolated=1
                    Logging.info("Interpolating camera at ",timepos,kw="animator")
                    self.interpolator.InterpolateCamera(timepos,cam)                    
                    
                    # we check the stored camera positions
                    for i,pos in enumerate(self.camPositions[:-1]):                        
                        t,camPos=pos
                        if timepos>=t:
                            t2,camPos2=self.camPositions[i+1]
                            # if the distance between the two consecutive
                            # camera positions is < 1.0 then the first
                            # position is used instead of an interpolated
                            # one since the interpolated position may be
                            # wrong
                            if distance(camPos,camPos2) < 1.0:
                                Logging.info("Using original camera position instead of interpolated",kw="animator")
                                cam.SetPosition(camPos)
                            break
                    
                    self.ren.ResetCameraClippingRange()
                    
                else:
                    Logging.info("No camera position, using last position",kw="animator")
                    point=self.lastpoint

        focal = self.splineEditor.getCameraFocalPointCenter()
        
        Logging.info("focal=",focal,"pos=",pos,kw="animator")
        if not interpolated and pos:
            self.setCameraParameters(cam,ren, pos, focal)
            
        if (not preview) or use_cam:
            print "Calling renderingInterface.render()"
            self.renderingInterface.render()     
        else:
            Logging.info("splineEditor.render()")
            self.splineEditor.render()
            time.sleep(0.1)
            
        if not preview:
            # With this we can be sure that all of the props will be visible.
            
            curr_file_name = self.renderingInterface.getFilename(frame)
            Logging.info("Saving to ",curr_file_name,kw="animator")
            self.renderingInterface.saveFrame(curr_file_name)
        
    def setCameraParameters(self,cam,renderer,point,focal):
        """
        Method: setCameraParameters(camera,renderer, point, focal)
        Created: 04.04.2005, KP
        Description: Sets the camera parameters
        """
        if point:
            cam.SetPosition(point)        
        cam.SetFocalPoint(focal)
        #viewUp,focalPoint=orientation
        #cam.SetFocalPoint(focalPoint)
        
        # if the track wishes to maintain up direction
        #cam.SetViewUp(viewUp)
        if self.currTrack and self.currTrack.maintainUpDirection:
            Logging.info("Orthogonalize view up",kw="animator")
            cam.SetViewUp((0,0,1))
            cam.ComputeViewPlaneNormal()
            cam.OrthogonalizeViewUp()
        elif self.currTrack:
            # if there's movement in z direction
#            print "lastpoint=",self.lastpoint,"point=",point
            if self.lastpoint and abs(self.lastpoint[2]-point[2])>2:
                #print "Orthogonalizing because old z=",self.lastpoint[2],"!= new z",point[2]
                Logging.info("Orthogonalize because oldz!=newz",kw="animator")
                cam.OrthogonalizeViewUp()
        self.lastpoint=point
        
        renderer.ResetCameraClippingRange()
        

                    

        
