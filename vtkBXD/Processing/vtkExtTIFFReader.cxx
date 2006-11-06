/*=========================================================================

  Program:   Visualization Toolkit
  Module:    $RCSfile: vtkExtTIFFReader.cxx,v $
  Language:  C++
  Date:      $Date: 2003/08/22 14:46:02 $
  Version:   $Revision: 1.39 $


Copyright (c) 1993-2001 Ken Martin, Will Schroeder, Bill Lorensen 
Copyright (c) 2005 Kalle Pahajoki Modifications for raw mode support
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

 * Redistributions of source code must retain the above copyright notice,
   this list of conditions and the following disclaimer.

 * Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution.

 * Neither name of Ken Martin, Will Schroeder, or Bill Lorensen nor the names
   of any contributors may be used to endorse or promote products derived
   from this software without specific prior written permission.

 * Modified source versions must be plainly marked as such, and must not be
   misrepresented as being the original software.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS ``AS IS''
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
ARE DISCLAIMED. IN NO EVENT SHALL THE AUTHORS OR CONTRIBUTORS BE LIABLE FOR
ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

=========================================================================*/
#include "vtkExtTIFFReader.h"

#include "vtkImageData.h"
#include "vtkObjectFactory.h"

#include <sys/stat.h>

extern "C" {
#include "vtk_tiff.h"
}


//-------------------------------------------------------------------------
vtkStandardNewMacro(vtkExtTIFFReader);
vtkCxxRevisionMacro(vtkExtTIFFReader, "$Revision: 1.39 $");

class vtkExtTIFFReaderInternal
{
public:
  vtkExtTIFFReaderInternal();
  int Initialize();
  void Clean();
  int CanRead();
  int Open( const char *filename );
  TIFF *Image;
  unsigned int Width;
  unsigned int Height;
  unsigned short SamplesPerPixel;
  unsigned short Compression;
  unsigned short BitsPerSample;
  unsigned short Photometrics;
  unsigned short PlanarConfig;
  unsigned long int TileDepth;
  static void ErrorHandler(const char* module, const char* fmt, va_list ap);
};


extern "C" {
void vtkExtTIFFReaderInternalErrorHandler(const char* vtkNotUsed(module), 
                                const char* vtkNotUsed(fmt), 
                                va_list vtkNotUsed(ap))
{
  // Do nothing
  // Ignore errors
}
}

int vtkExtTIFFReaderInternal::Open( const char *filename )
{
  this->Clean();
  struct stat fs;
  if ( stat(filename, &fs) )
    {
    return 0;
    }
  this->Image = TIFFOpen(filename, "r");
  if ( !this->Image)
    {
    this->Clean();
    return 0;
    }
  if ( !this->Initialize() )
    {
    this->Clean();
    return 0;
    }
  return 1;
}

void vtkExtTIFFReaderInternal::Clean()
{
  if ( this->Image )
    {
    TIFFClose(this->Image);
    }
  this->Image=NULL;
  this->Width = 0;
  this->Height = 0;
  this->SamplesPerPixel = 0;
  this->Compression = 0;
  this->BitsPerSample = 0;
  this->Photometrics = 0;
  this->PlanarConfig = 0;
  this->TileDepth = 0;
}

vtkExtTIFFReaderInternal::vtkExtTIFFReaderInternal()
{
  this->Image           = NULL;
  TIFFSetErrorHandler(&vtkExtTIFFReaderInternalErrorHandler);
  TIFFSetWarningHandler(&vtkExtTIFFReaderInternalErrorHandler);
  this->Clean();
}

int vtkExtTIFFReaderInternal::Initialize()
{
  if ( this->Image )
    {
    if ( !TIFFGetField(this->Image, TIFFTAG_IMAGEWIDTH, &this->Width) ||
         !TIFFGetField(this->Image, TIFFTAG_IMAGELENGTH, &this->Height) )
      {
      return 0;
      }
    TIFFGetField(this->Image, TIFFTAG_SAMPLESPERPIXEL, 
                 &this->SamplesPerPixel);
    TIFFGetField(this->Image, TIFFTAG_COMPRESSION, &this->Compression);
    TIFFGetField(this->Image, TIFFTAG_BITSPERSAMPLE, 
                 &this->BitsPerSample);
    TIFFGetField(this->Image, TIFFTAG_PHOTOMETRIC, &this->Photometrics);
    TIFFGetField(this->Image, TIFFTAG_PLANARCONFIG, &this->PlanarConfig);
//      printf("Planar configuration=%d\n",this->PlanarConfig);
    if ( !TIFFGetField(this->Image, TIFFTAG_TILEDEPTH, &this->TileDepth) )
      {
      this->TileDepth = 0;
      }
    }
  return 1;
}

int vtkExtTIFFReaderInternal::CanRead()
{
    return ( this->Image && ( this->Width > 0 ) && ( this->Height > 0 ) &&
           ( this->SamplesPerPixel > 0 ) && 
           ( this->Compression == COMPRESSION_NONE ) &&
           ( this->Photometrics == PHOTOMETRIC_RGB ||
             this->Photometrics == PHOTOMETRIC_MINISWHITE ||
             this->Photometrics == PHOTOMETRIC_MINISBLACK ||
             this->Photometrics == PHOTOMETRIC_PALETTE ) &&
           this->PlanarConfig == PLANARCONFIG_CONTIG &&
           ( !this->TileDepth ) &&
           ( this->BitsPerSample == 8) );
}

vtkExtTIFFReader::vtkExtTIFFReader()
{
  this->InitializeColors();
  this->InternalImage = new vtkExtTIFFReaderInternal;
  this->InternalExtents = 0;
  this->RawMode = 0;
}

vtkExtTIFFReader::~vtkExtTIFFReader()
{
  delete this->InternalImage;
}

void vtkExtTIFFReader::ExecuteInformation()
{    
  this->InitializeColors();

  this->ComputeInternalFileName(this->DataExtent[4]);
  if (this->InternalFileName == NULL)
    {
    return;
    }
  
  if ( !this->InternalImage->Open(this->InternalFileName) )
    {  
    vtkErrorMacro("Unable to open file " <<this->InternalFileName );
    this->DataExtent[0] = 0;
    this->DataExtent[1] = 0;
    this->DataExtent[2] = 0;
    this->DataExtent[3] = 0;
    this->DataExtent[4] = 0;
    this->DataExtent[5] = 0;
    this->SetNumberOfScalarComponents(1);
    this->vtkImageReader2::ExecuteInformation();
    return;
    }

  // pull out the width/height, etc.
  this->DataExtent[0] = 0;
  this->DataExtent[1] = this->GetInternalImage()->Width - 1;
  this->DataExtent[2] = 0;
  this->DataExtent[3] = this->GetInternalImage()->Height - 1;

  if(this->GetInternalImage()->BitsPerSample==16) {
    this->SetDataScalarTypeToUnsignedShort();
  }  else this->SetDataScalarTypeToUnsignedChar();     
      
    
//  printf("Image format = %d\n",this->GetFormat());
  switch ( this->GetFormat() )
    {
    case vtkExtTIFFReader::RAW:
    case vtkExtTIFFReader::GRAYSCALE:
    case vtkExtTIFFReader::PALETTE_GRAYSCALE:
      this->SetNumberOfScalarComponents( 1 );
//      printf("One scalarcomponent\n");
      break;
    case vtkExtTIFFReader::RGB:      
      this->SetNumberOfScalarComponents( 
        this->GetInternalImage()->SamplesPerPixel );
//       printf("RGB, Number of scalar components = %d\n",this->GetInternalImage()->SamplesPerPixel);
      break;
    case vtkExtTIFFReader::PALETTE_RGB:      
      this->SetNumberOfScalarComponents( 3 );
      break;
    default:
//        printf("By default number of scalar components=4\n");
      this->SetNumberOfScalarComponents( 4 );
    }

  if ( !this->GetInternalImage()->CanRead() )
    {
//        printf("Cannot read internal image\n");
        if(this->GetInternalImage()->BitsPerSample!=16) {
            this->SetNumberOfScalarComponents( 4 );
        }
    }

  this->vtkImageReader2::ExecuteInformation();

    
  // close the file
  this->GetInternalImage()->Clean();
}


template <class OT>
void vtkExtTIFFReaderUpdate2(vtkExtTIFFReader *self, OT *outPtr,
                          int *outExt, vtkIdType* vtkNotUsed(outInc), long)
{
  if ( !self->GetInternalImage()->Open(self->GetInternalFileName()) )
    {
    return;
    }
  self->InitializeColors();
    
  self->ReadImageInternal(self->GetInternalImage()->Image, 
                          outPtr, outExt, sizeof(OT) );

  // close the file
//    printf("Closing the file\n");
  self->GetInternalImage()->Clean();
//    printf("Done\n");
}

//----------------------------------------------------------------------------
// This function reads in one data of data.
// templated to handle different data types.
template <class OT>
void vtkExtTIFFReaderUpdate(vtkExtTIFFReader *self, vtkImageData *data, OT *outPtr)
{
  vtkIdType outIncr[3];
  int outExtent[6];
  OT *outPtr2;

  data->GetExtent(outExtent);
  data->GetIncrements(outIncr);

  long pixSize = data->GetNumberOfScalarComponents()*sizeof(OT);  
  
  outPtr2 = outPtr;
  int idx2;
  for (idx2 = outExtent[4]; idx2 <= outExtent[5]; ++idx2)
    {
    self->ComputeInternalFileName(idx2);
    // read in a TIFF file
//    printf("Reading slice %d\n",idx2);
    vtkExtTIFFReaderUpdate2(self, outPtr2, outExtent, outIncr, pixSize);
    self->UpdateProgress((idx2 - outExtent[4])/
                         (outExtent[5] - outExtent[4] + 1.0));
    outPtr2 += outIncr[2];
    }
}


//----------------------------------------------------------------------------
// This function reads a data from a file.  The datas extent/axes
// are assumed to be the same as the file extent/order.
void vtkExtTIFFReader::ExecuteData(vtkDataObject *output)
{
  vtkImageData *data = this->AllocateOutputData(output);

//    printf("data estimated size=%d\n",data->GetActualMemorySize());
  if (this->InternalFileName == NULL)
    {
    vtkErrorMacro("Either a FileName or FilePrefix must be specified.");
    return;
    }

  this->ComputeDataIncrements();
  
  // Call the correct templated function for the output
  void *outPtr;

  // Call the correct templated function for the input
  outPtr = data->GetScalarPointer();
  switch (data->GetScalarType())
    {
    vtkTemplateMacro3(vtkExtTIFFReaderUpdate, this, data, (VTK_TT *)(outPtr));
    default:
      vtkErrorMacro("UpdateFromFile: Unknown data type");
    }   
}

unsigned int vtkExtTIFFReader::GetFormat( )
{
  unsigned int cc; 
  if ( this->ImageFormat != vtkExtTIFFReader::NOFORMAT )
    {
    return this->ImageFormat;
    }


  switch ( this->GetInternalImage()->Photometrics )
    {
    case PHOTOMETRIC_RGB: 
    case PHOTOMETRIC_YCBCR: 
      this->ImageFormat = vtkExtTIFFReader::RGB;
      return this->ImageFormat;
    case PHOTOMETRIC_MINISWHITE:
    case PHOTOMETRIC_MINISBLACK:
      this->ImageFormat = vtkExtTIFFReader::GRAYSCALE;
      return this->ImageFormat;
    case PHOTOMETRIC_PALETTE:
      for( cc=0; cc<256; cc++ ) 
        {
        unsigned short red, green, blue;
        this->GetColor( cc, &red, &green, &blue );
        if ( red != green || red != blue )
          {
          this->ImageFormat = vtkExtTIFFReader::PALETTE_RGB;
          return this->ImageFormat;
          }
        }
      this->ImageFormat = vtkExtTIFFReader::PALETTE_GRAYSCALE;
      return this->ImageFormat;
    }
  this->ImageFormat = vtkExtTIFFReader::OTHER;
  return this->ImageFormat;
}

void vtkExtTIFFReader::GetColor( int index, unsigned short *red, 
                                 unsigned short *green, unsigned short *blue )
{
  *red   = 0;
  *green = 0;
  *blue  = 0;
  if ( index < 0 ) 
    {
    vtkErrorMacro("Color index has to be greater than 0");
    return;
    }
  if ( this->TotalColors > 0 && 
       this->ColorRed && this->ColorGreen && this->ColorBlue )
    {
    if ( index >= this->TotalColors )
      {
      vtkErrorMacro("Color index has to be less than number of colors ("
                    << this->TotalColors << ")");
      return;
      }
    *red   = *(this->ColorRed   + index);
    *green = *(this->ColorGreen + index);
    *blue  = *(this->ColorBlue  + index);
    return;
    }

  unsigned short photometric;
  
  if (!TIFFGetField(this->GetInternalImage()->Image, TIFFTAG_PHOTOMETRIC, &photometric)) 
    {
    if ( this->GetInternalImage()->Photometrics != PHOTOMETRIC_PALETTE )
      {
      vtkErrorMacro("You can only access colors for palette images");
      return;
      }
    }
  
  unsigned short *red_orig, *green_orig, *blue_orig; 
  
  switch (this->GetInternalImage()->BitsPerSample) 
    {
    case 1: case 2: case 4:
    case 8: case 16:
        break;
    default:
      vtkErrorMacro( "Sorry, can not image with " 
                     << this->GetInternalImage()->BitsPerSample
                     << "-bit samples" );
        return;
    }
  if (!TIFFGetField(this->GetInternalImage()->Image, TIFFTAG_COLORMAP,
                    &red_orig, &green_orig, &blue_orig)) 
    {
    vtkErrorMacro("Missing required \"Colormap\" tag");
    return;
    }
//  printf("Bits per sample = %d\n",this->GetInternalImage()->BitsPerSample);
  this->TotalColors = (1L << this->GetInternalImage()->BitsPerSample);

  if ( index >= this->TotalColors )
    {
    vtkErrorMacro("Color index has to be less than number of colors ("
                  << this->TotalColors << ")");
    return;
    }
  this->ColorRed   =   red_orig;
  this->ColorGreen = green_orig;
  this->ColorBlue  =  blue_orig;
  
  *red   = *(red_orig   + index);
  *green = *(green_orig + index);
  *blue  = *(blue_orig  + index);
}

void vtkExtTIFFReader::InitializeColors()
{
  this->ColorRed    = 0;
  this->ColorGreen  = 0;
  this->ColorBlue   = 0;
  this->TotalColors = -1;  
  if(RawMode) { this->ImageFormat = vtkExtTIFFReader::RAW; }
  else this->ImageFormat = vtkExtTIFFReader::NOFORMAT;
}

void vtkExtTIFFReader::ReadImageInternal( void* vtkNotUsed(in), void* outPtr, 
                                       int* outExt, 
                                       unsigned int size )
{
  if ( this->GetInternalImage()->Compression == COMPRESSION_OJPEG )
      {
      vtkErrorMacro("This reader cannot read old JPEG compression");
      return;
      }

    int width  = this->GetInternalImage()->Width;
    int height = this->GetInternalImage()->Height;
    this->InternalExtents = outExt;
    unsigned int isize = TIFFScanlineSize(this->GetInternalImage()->Image);
//      printf("isize=%d, height=%d\n",isize,height);
    unsigned int cc;
    int row, inc = 1;
    tdata_t buf = _TIFFmalloc(isize);      
    
     // special case for 16-bit grayscale
    if(this->GetInternalImage()->BitsPerSample==16 && this->GetFormat()== vtkExtTIFFReader::GRAYSCALE)
    {
    isize /= 2;
    unsigned short* image;
    int tot=0;
        image = (unsigned short*)outPtr;
            
    if (InternalImage->PlanarConfig == PLANARCONFIG_CONTIG)
      {
//          printf("Contig planes\n");
          image = (unsigned short*)outPtr;
      for ( row = 0; row < (int)height; row ++ )
        {
        if (TIFFReadScanline(InternalImage->Image, buf, row, 0) <= 0)
          {
	    vtkErrorMacro( << "Problem reading the row: " << row <<"of file"<<GetInternalFileName());
          break;
          }
          unsigned short* buf2 = (unsigned short*)buf;
          //image = reinterpret_cast<unsigned short*>(outPtr) + width * inc * (height - (row + 1));
//          image = reinterpret_cast<unsigned short*>(outPtr) + row * width * inc;

        //printf("Copying %d doublebytes\n",isize);
          
          for(cc = 0; cc < isize; cc += InternalImage->SamplesPerPixel) {
                    //image[cc]=((unsigned short*)buf)[cc];
                *image++ = *buf2++;
              tot+=1;
          }
          /*
        for (cc = 0; cc < isize;
             cc += InternalImage->SamplesPerPixel )
          {
          inc = this->EvaluateImageAt( image,
                                       static_cast<unsigned short *>(buf) +
                                       cc );
          image += inc;
          }*/
          
        }
//        printf("Copied %d doublebytes\n",tot);
          _TIFFfree(buf);
        return;
      }
    else if(InternalImage->PlanarConfig == PLANARCONFIG_SEPARATE)
      {
//          printf("Separate planes\n");
      unsigned long s, nsamples;
      TIFFGetField(InternalImage->Image, TIFFTAG_SAMPLESPERPIXEL, &nsamples);
      for (s = 0; s < nsamples; s++)
        {
        for ( row = 0; row < (int)height; row ++ )
          {
          if (TIFFReadScanline(InternalImage->Image, buf, row, s) <= 0)
            {
            vtkErrorMacro( << "Problem reading the row: " << row );
            break;
            }
            
          
            inc = 3;
            image = reinterpret_cast<unsigned short*>(outPtr) + width * inc * (height - (row + 1));
            //image = reinterpret_cast<unsigned short*>(outPtr) + row * width * inc;
          for (cc = 0; cc < isize; 
               cc += InternalImage->SamplesPerPixel )
            {
            inc = this->EvaluateImageAt( image, 
                                         static_cast<unsigned short *>(buf) +
                                         cc );      
            image += inc;
            }
          }
        }
      }
  }
      
  else if ( !this->GetInternalImage()->CanRead() )
    {
    uint32 *tempImage 
      = static_cast<uint32*>( outPtr );
    
    if ( this->InternalExtents[0] != 0 || 
         this->InternalExtents[1] != width -1 ||
         this->InternalExtents[2] != 0 || 
         this->InternalExtents[3] != height-1 )
      {
      tempImage = new uint32[ width * height ];
      }
    if ( !TIFFReadRGBAImage(this->GetInternalImage()->Image, 
                            width, height, 
                            tempImage, 0 ) )
      {
      vtkErrorMacro("Problem reading RGB image");
      if ( tempImage != outPtr )
        {
        delete [] tempImage;
        }
      
      return;
      }
    int xx, yy;
    unsigned char *simage = (unsigned char *)tempImage;
    uint32* ssimage = tempImage;
    unsigned char *fimage = (unsigned char *)outPtr;
    for ( yy = 0; yy < height; yy ++ )
      {
      for ( xx = 0; xx < width; xx++ )
        {
        if ( xx >= this->InternalExtents[0] && 
             xx <= this->InternalExtents[1] &&
             yy >= this->InternalExtents[2] && 
             yy <= this->InternalExtents[3] )
          {       
          /*
          unsigned char red   = *(simage);
          unsigned char green = *(simage+1);
          unsigned char blue  = *(simage+2);
          unsigned char alpha = *(simage+3);
          */
          unsigned char red   = static_cast<unsigned char>(TIFFGetR(*ssimage));
          unsigned char green = static_cast<unsigned char>(TIFFGetG(*ssimage));
          unsigned char blue  = static_cast<unsigned char>(TIFFGetB(*ssimage));
          unsigned char alpha = static_cast<unsigned char>(TIFFGetA(*ssimage));

          *(fimage  ) = red;//red;
          *(fimage+1) = green;//green;
          *(fimage+2) = blue;//blue;
          *(fimage+3) = alpha;//alpha;
          fimage += 4;
          }
        simage += 4;
        ssimage ++;
        }
      }
    
    if ( tempImage != 0 && tempImage != outPtr )
      {
      delete [] tempImage;
      }
    return;
    }

  unsigned int format = this->GetFormat();  
    

  if ( this->GetInternalImage()->Compression == COMPRESSION_PACKBITS )
    {
    height /= this->GetInternalImage()->BitsPerSample;
    }

  switch ( format )
    {
    case vtkExtTIFFReader::RAW:
    case vtkExtTIFFReader::GRAYSCALE:
    case vtkExtTIFFReader::RGB: 
    case vtkExtTIFFReader::PALETTE_RGB:
    case vtkExtTIFFReader::PALETTE_GRAYSCALE:      
      this->ReadGenericImage( outPtr, width, height, size );
      break;
    default:
      return;
    }
}

void vtkExtTIFFReader::ReadGenericImage( void *out, 
                                      unsigned int vtkNotUsed(width), 
                                      unsigned int height, 
                                      unsigned int vtkNotUsed(size) )
{
  unsigned int isize = TIFFScanlineSize(this->GetInternalImage()->Image);
  unsigned int cc;
  int row, inc;
  int xx=0, yy=0;
  tdata_t buf = _TIFFmalloc(isize);
  unsigned char *image = (unsigned char *)out;

  if ( this->GetInternalImage()->PlanarConfig == PLANARCONFIG_CONTIG )
    {
    for ( row = height-1; row >= 0; row -- )
      {
      if (TIFFReadScanline(this->GetInternalImage()->Image, buf, row, 0) <= 0)
        {
        vtkErrorMacro("Problem reading the row: " << row);
        break;
        }
      for (cc = 0; cc < isize; 
           cc += this->GetInternalImage()->SamplesPerPixel )
        {
        if ( xx >= this->InternalExtents[0] && 
             xx <= this->InternalExtents[1] &&
             yy >= this->InternalExtents[2] && 
             yy <= this->InternalExtents[3] )
          {
          //unsigned char *c = static_cast<unsigned char *>(buf)+cc;
          inc = this->EvaluateImageAt( image, 
                                       static_cast<unsigned char *>(buf) +
                                       cc );      
          image += inc;
          }
        xx++;
        }
      xx=0;
      yy++;
      }
    }
  else 
    {
    vtkErrorMacro("This reader can only do PLANARCONFIG_CONTIG");
    }

  _TIFFfree(buf); 
}

int vtkExtTIFFReader::EvaluateImageAt( void* out, void* in )
{
  unsigned char *image = (unsigned char *)out;
  unsigned char *source = (unsigned char *)in;
  int increment = 0;
  unsigned short red, green, blue, alpha;
  switch ( this->GetFormat() )
    {
    case vtkExtTIFFReader::RAW:
    *image = *source;
    increment = 1;
    break;  
    case vtkExtTIFFReader::GRAYSCALE:
      if ( this->GetInternalImage()->Photometrics == 
           PHOTOMETRIC_MINISBLACK )
        {
        *image = *source;
        }
      else
        {
        *image = ~( *source );
        }
      increment = 1;
      break;
    case vtkExtTIFFReader::PALETTE_GRAYSCALE:
      this->GetColor(*source, &red, &green, &blue);
      *image = red;
      increment = 1;
      break;
    case vtkExtTIFFReader::RGB: 
      red   = *(source);
      green = *(source+1);
      blue  = *(source+2);
      *(image)   = red;
      *(image+1) = green;
      *(image+2) = blue;
      if ( this->GetInternalImage()->SamplesPerPixel == 4 )
        {
        alpha = *(source+3);
        *(image+3) = 255-alpha;       
        }
      increment = this->GetInternalImage()->SamplesPerPixel;
      break;
    case vtkExtTIFFReader::PALETTE_RGB:
      this->GetColor(*source, &red, &green, &blue);     
      *(image)   = static_cast<unsigned char>(red >> 8);
      *(image+1) = static_cast<unsigned char>(green >> 8);
      *(image+2) = static_cast<unsigned char>(blue >> 8);
      increment = 3;
      break;
    default:
      return 0;
    }
  
  return increment;
}

int vtkExtTIFFReader::CanReadFile(const char* fname)
{
  vtkExtTIFFReaderInternal tf;
  int res = tf.Open(fname);
  tf.Clean();
  if (res)
    {
    return 3;
    }
  return 0;
}

//----------------------------------------------------------------------------
void vtkExtTIFFReader::PrintSelf(ostream& os, vtkIndent indent)
{
  this->Superclass::PrintSelf(os,indent);
}