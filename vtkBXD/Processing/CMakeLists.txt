#
# Source files
#
# Here is where you can add the name of your local imaging classes.
#

SET (Processing_SRCS
vtkDistanceRepresentationScaled2D.cxx
vtkExtTIFFReader.cxx
vtkImageAlphaFilter.cxx
vtkImageAutoThresholdColocalization.cxx
vtkImageMaskAutoThresholdColocalization.cxx
vtkImageColocalizationFilter.cxx
vtkImageColocalizationTest.cxx
vtkIntensityTransferFunction.cxx
vtkImageColorMerge.cxx
vtkImageLabelAverage.cxx
vtkImageMapToIntensities.cxx
vtkImageSimpleMIP.cxx
vtkImageSolitaryFilter.cxx
vtkLSMReader.cxx
vtkLIFReader.cxx
vtkImageLabelCount.cxx
vtkMRCReader.cxx
vtkImageIterativeDeconvolution3D.cxx
vtkImageDiffractionPSF3D.cxx
vtkImageLabelDistanceToSurface.cxx
vtkHandleColorTransferFunction.cxx
vtkTestMemory.cxx
vtkImageMathematicsClamp.cxx
vtkOMETIFFReader.cxx
vtkOMETIFFWriter.cxx
vtkExtXMLUtilities.cxx
)

# --------------------------------------------------------------------------
# You probably do not need to modify anything below this line

# Create the vtkBXDProcessing C++ library
ADD_LIBRARY (vtkBXDProcessing ${Processing_SRCS})

SET_TARGET_PROPERTIES (vtkBXDProcessing
  PROPERTIES  INSTALL_NAME_DIR "${CMAKE_INSTALL_PREFIX}/lib"
)

TARGET_LINK_LIBRARIES(vtkBXDProcessing vtkImaging vtkCommon vtkIO vtkWidgets vtkFiltering  )

# Create the vtkBXDBioImageXD Python library.
IF (VTK_WRAP_PYTHON AND VTKBXD_WRAP_PYTHON)
  VTK_WRAP_PYTHON3 (vtkBXDProcessingPython ProcessingPython_SRCS "${Processing_SRCS}")
  ADD_LIBRARY (vtkBXDProcessingPythonD ${ProcessingPython_SRCS})
  ADD_LIBRARY (vtkBXDProcessingPython MODULE vtkBXDProcessingPythonInit.cxx)

SET_TARGET_PROPERTIES (vtkBXDProcessingPython
  PROPERTIES  INSTALL_NAME_DIR "${CMAKE_INSTALL_PREFIX}/lib"
)
# Python extension modules on Windows must have the extension ".pyd"
# instead of ".dll" as of Python 2.5.  Older python versions do support
# this suffix.
IF(WIN32 AND NOT CYGWIN)
  SET_TARGET_PROPERTIES(vtkBXDProcessingPython PROPERTIES SUFFIX ".pyd")
ENDIF(WIN32 AND NOT CYGWIN)

SET_TARGET_PROPERTIES (vtkBXDProcessingPythonD
  PROPERTIES  INSTALL_NAME_DIR "${CMAKE_INSTALL_PREFIX}/lib"
)


  TARGET_LINK_LIBRARIES(vtkBXDProcessingPythonD vtkBXDProcessing vtkImaging vtkImagingPythonD vtkCommon vtkCommonPythonD vtkIO vtkIOPythonD vtkWidgets vtkWidgetsPythonD vtkFiltering vtkFilteringPythonD)
  TARGET_LINK_LIBRARIES(vtkBXDProcessingPython vtkBXDProcessingPythonD)

  INSTALL(TARGETS vtkBXDProcessing vtkBXDProcessingPythonD
    RUNTIME DESTINATION bin 
    LIBRARY DESTINATION lib 
    ARCHIVE DESTINATION lib 
  )
  INSTALL(TARGETS vtkBXDProcessingPython
    RUNTIME DESTINATION bin
    LIBRARY DESTINATION lib/python2.6/site-packages/vtkbxd
    ARCHIVE DESTINATION lib/python2.6/site-packages/vtkbxd
  )
ENDIF (VTK_WRAP_PYTHON AND VTKBXD_WRAP_PYTHON)

# Create the vtkBXDBioImageXD Java library.
IF (VTK_WRAP_JAVA AND VTKBXD_WRAP_JAVA)
  #INCLUDE(${VTK_CMAKE_DIR}/vtkWrapJava.cmake)
  #SET(VTK_WRAP_JAVA3_INIT_DIR "${PROJECT_SOURCE_DIR}")
  SET(VTK_JAVA_HOME ${PROJECT_BINARY_DIR}/java/${PROJECT_NAME})
  MAKE_DIRECTORY(${VTK_JAVA_HOME})
  VTK_WRAP_JAVA3(vtkBXDProcessingJava ProcessingJava_SRCS "${Processing_SRCS}")
  ADD_LIBRARY (vtkBXDProcessingJava ${ProcessingJava_SRCS})

  SET_TARGET_PROPERTIES (vtkBXDProcessingJava
    PROPERTIES  INSTALL_NAME_DIR "${CMAKE_INSTALL_PREFIX}/lib"
  )

  TARGET_LINK_LIBRARIES(vtkBXDProcessingJava vtkBXDProcessing vtkImaging vtkImagingJava vtkCommon vtkCommonJava vtkIO vtkIOJava vtkWidgets vtkWidgetsJava vtkFiltering vtkFilteringJava)

  INSTALL(TARGETS vtkBXDProcessing vtkBXDProcessingJava
    RUNTIME DESTINATION bin 
    LIBRARY DESTINATION lib 
    ARCHIVE DESTINATION lib 
  )

ENDIF (VTK_WRAP_JAVA AND VTKBXD_WRAP_JAVA)
