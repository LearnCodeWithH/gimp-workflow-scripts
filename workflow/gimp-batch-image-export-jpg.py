#!/usr/bin/env python

from gimpfu import *
import os
import re

class JpegExportOptions:
	def __init__(self, quality=0.95, smoothing=0.0, optimize=1, progressive=1,comment='',subsampling=2, baseline=0, restart_markers=0, dct_method=0):
		self.quality               = quality
		self.smoothing          = smoothing
		self.optimize             = optimize
		self.progressive        =  progressive 
		self.comment            = comment
		self.subsampling       = subsampling
		self.baseline             = baseline
		self.restart_markers  = restart_markers
		self.dct_method        = dct_method
		
	def __repr__(self):
		return self.__str__()
	
	def __str__(self):
		return "JpegExpOpt: mode '%s', qual '%s', smooth '%s', optim '%s', prog '%s', comm '%s', subsmpl '%s', baseline '%s', restartmark '%s', dctmeth '%s" % (self.export_mode, self.quality, self.smoothing, self.optimize, self.progressive, self.comment, self.subsampling, self.baseline, self.restart_markers, self.dct_method)

def disable_text_groups(image):
	txt_group = re.compile('Text Group', re.IGNORECASE)
	for layer in image.layers:
		if pdb.gimp_item_is_group(layer) and txt_group.search(layer.name) is not None:
			pdb.gimp_item_set_visible(layer, False)
			
	return image
	
def disable_non_text_groups(image):
	txt_group = re.compile('Text Group', re.IGNORECASE)
	for layer in image.layers:
		if txt_group.search(layer.name) is None:
			pdb.gimp_item_set_visible(layer, False)
			
	return image

def generate_new_filename_map(fileList):
	oldFileList = []
	newFileList = []
	xform = re.compile('\.(xcf)', re.IGNORECASE)
	# Find all of the xcf files in the list & make jpg file names
	for fname in fileList:
		fnameLow = fname.lower()
		if fnameLow.endswith('.xcf'):
			oldFileList.append(fname)
			newFileList.append(xform.sub('.jpg',fname))
	# Dictionary - old & new file names
	fileDict = dict(zip(oldFileList, newFileList))
	return fileDict
	
def save_to_jpeg(image_to_save, fullNewFile, export_opts):
	CLIP_TO_IMAGE = 1
	theDrawable = pdb.gimp_image_merge_visible_layers(image_to_save, CLIP_TO_IMAGE)
	pdb.file_jpeg_save(image_to_save, theDrawable, fullNewFile, fullNewFile, export_opts.quality, export_opts.smoothing, export_opts.optimize, export_opts.progressive, export_opts.comment, export_opts.subsampling, export_opts.baseline, export_opts.restart_markers, export_opts.dct_method)
	
	
def export_xcf_in_directory_to_jpg(srcPath, dstPath, exportCleaned, exportText, export_opts):
    open_images, image_ids = pdb.gimp_image_list()
    if open_images > 0:
        pdb.gimp_message ("Close open Images & Rerun")
    else:
		# Ensure 2.7 byte strings are unicode
		srcPath = unicode(srcPath, "utf-8")
		# list all of the files in source & target directories
		allFileList = os.listdir(srcPath)
		fileDict = generate_new_filename_map(allFileList)
		# Loop on jpegs, open each, prep & save as xcf
		for oldFile in fileDict.keys():
			# os.path.join inserts the right kind of file separator
			
			fullNewFile = os.path.join(dstPath, fileDict[oldFile])
			fullOldFile = os.path.join(srcPath, oldFile)
			theImage = pdb.gimp_xcf_load(0, fullOldFile, fullOldFile)
			try:
				image_to_save = theImage
				if exportCleaned:
					image_to_save = disable_text_groups(theImage)
				if exportText:
					image_to_save = disable_non_text_groups(theImage)
					
				save_to_jpeg(image_to_save, fullNewFile, export_opts)
			finally:
				if theImage is not None:
					pdb.gimp_image_delete(theImage)
						
def batch_xcf_export_jpg(srcPath, dstPath, exportCleaned, exportText, Quality, Smoothing, Optimize, Progressive, Comment, Subsampling, DctMethod):
	export_opts = JpegExportOptions( \
	quality = Quality / 100.0, \
	smoothing = Smoothing / 100.0, \
	optimize = Optimize, \
	 progressive = Progressive, \
	comment = Comment, \
	subsampling = Subsampling, \
	dct_method = DctMethod \
	)
	export_xcf_in_directory_to_jpg(srcPath, dstPath, exportCleaned, exportText, export_opts)

register (
    "batch_xcf_export_jpg",         # Name registered in Procedure Browser
    N_("Export all xcf in a source directory to jpg into a destination dir."), # Widget title
    "Export all xcf in a source directory to jpg into a destination dir.", # 
    "LearnCodeWithH",         # Author
    "LearnCodeWithH",         # Copyright Holder
    "Jan 2019",            # Date
    N_("Export all .xcf to .jpg"), # Menu Entry
    "",     # Image Type - No image required
    [
    ( PF_DIRNAME, "srcPath", "Source .xcf Directory:", "/" ),
    ( PF_DIRNAME, "dstPath", "Destination .jpg Directory:", "/" ),
    ( PF_BOOL, "exportCleaned", "Export Cleaned? (Disabling any layer groups with 'Text Group' in them before export):", False ),
    ( PF_BOOL, "exportText", "Export Text Only? (Disabling any layers without 'Text Group' in them before export):", False ),
	
	( PF_SLIDER, "Quality", "Quality:", 95, (0, 100, 1) ),
	( PF_SLIDER, "Smoothing", "Smoothing:", 0, (0, 100, 1) ),
	( PF_TOGGLE, "Optimize", "Optimize?:", 1 ),
	( PF_TOGGLE, "Progressive", "Progressive?:", 1 ),
	( PF_TEXT, "Comment", "Comment:", "Created with GIMP." ),
	( PF_OPTION, "Subsampling", "Subsampling:", 2, ("4:2:0 (chroma quartered)", "4:2:2 Horizontal (chroma halved)", "4:4:4 (best quality)", "4:2:2 Vertical (chroma halved)") ),
	( PF_OPTION, "DctMethod", "Dct Method:", 0, ("Integer", "Fixed", "Float") ),
    ],
    [],
    batch_xcf_export_jpg,   # Matches to name of function being defined
    menu = "<Image>/Image/Batch Image Prep"  # Menu Location
    )   # End register
	
main()
