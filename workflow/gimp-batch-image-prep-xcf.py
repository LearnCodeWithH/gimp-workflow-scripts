#!/usr/bin/env python

from gimpfu import *
import os
import re

def prep(image, base_layer_pos):
	add_layer(image, 'Clean Layer', None, base_layer_pos - 1)
	
	corrections_group = add_layer_group(image, 'Corrections', base_layer_pos - 2)
	add_layer(image, 'Clean Corrections', corrections_group, 0)
	add_layer(image, 'Line Corrections', corrections_group, -1)
	add_layer_group(image, 'SFX Text Group', base_layer_pos - 3)
	add_layer_group(image, 'Text Group', base_layer_pos - 4)
	
def add_layer_group(image, title, position):
	group = pdb.gimp_layer_group_new(image)
	group.name = title

	pdb.gimp_image_insert_layer(image, group, None, position)
	return group
	
def add_layer(image, title, parent, position):
	layer = gimp.Layer(image, title,
							image.width, image.height,
							RGBA_IMAGE, 100, NORMAL_MODE)

	pdb.gimp_image_insert_layer(image, layer, parent, position)
	return layer

def prep_image(image):
	base_layer_pos = 0
	
	prep(image, base_layer_pos)
	
	return image

def generate_new_filename_map(fileList):
	oldFileList = []
	newFileList = []
	xform = re.compile('\.(jpg|jpeg|png)', re.IGNORECASE)
	# Find all of the jpg/jpeg/png files in the list & make xcf file names
	for fname in fileList:
		fnameLow = fname.lower()
		if fnameLow.endswith('.jpg') or fnameLow.endswith('.jpeg') or fnameLow.endswith('.png'):
			oldFileList.append(fname)
			newFileList.append(xform.sub('.xcf',fname))
	# Dictionary - old & new file names
	fileDict = dict(zip(oldFileList, newFileList))
	return fileDict
	
def prep_images_to_xcf(imgPath):
    open_images, image_ids = pdb.gimp_image_list()
    if open_images > 0:
        pdb.gimp_message ("Close open Images & Rerun")
    else:
		# Ensure 2.7 byte strings are unicode
		imgPath = unicode(imgPath, "utf-8")
		# list all of the files in source & target directories
		allFileList = os.listdir(imgPath)
		fileDict = generate_new_filename_map(allFileList)
		# Loop on jpegs, open each, prep & save as xcf
		for oldFile in fileDict.keys():
			# Don't overwrite existing, might be work in Progress
			if fileDict[oldFile] not in allFileList:
				# os.path.join inserts the right kind of file separator
				
				fullNewFile = os.path.join(imgPath, fileDict[oldFile])
				fullOldFile = os.path.join(imgPath, oldFile)
				
				theImage = None
				oldFileLower = oldFile.lower()
				if oldFileLower.endswith('.jpg') or oldFileLower.endswith('.jpeg'):
					theImage = pdb.file_jpeg_load(fullOldFile, fullOldFile)
				elif oldFileLower.endswith('.png'):
					theImage = pdb.file_png_load(fullOldFile, fullOldFile)
				
				if theImage is None:
					pdb.gimp_message ("Skipping unsupported format: %s" % oldFile)
					continue;
					
				image_type = pdb.gimp_image_base_type(theImage)
				if image_type is not 0: #RGB
					pdb.gimp_image_convert_rgb(theImage)
				preppedImage = None
				try:
					preppedImage = prep_image(theImage)
					theDrawable = preppedImage.active_drawable
					pdb.gimp_xcf_save(0, preppedImage, theDrawable, fullNewFile, fullNewFile)
				finally:
					if preppedImage is not None:
						pdb.gimp_image_delete(preppedImage)

def prep_xcf_layers(Image):
	pdb.gimp_image_undo_group_start(Image)
	try:
		image_type = pdb.gimp_image_base_type(Image)
		if image_type is not 0: #RGB
			pdb.gimp_image_convert_rgb(Image)
			pdb.gimp_message("Converted Image Mode to RGB to allow layer groups.")
		preppedImage = prep_image(Image)
	finally:
		pdb.gimp_image_undo_group_end(Image)

register (
    "prep_images_to_xcf",         # Name registered in Procedure Browser
    N_("Insert Layers into Jpg/Jpeg/Png Images and Saves to .xcf"), # Widget title
    "Adds a Cleaning Layer, a Text Layer Group, then saves to .xcf for every jpg/jpeg/png image in a directory.", # 
    "LearnCodeWithH",         # Author
    "LearnCodeWithH",         # Copyright Holder
    "Jan 2019",            # Date
    N_("Insert Layers and Save to Xcf"), # Menu Entry
    "",     # Image Type - No image required
    [
    ( PF_DIRNAME, "imgPath", "Image Directory:", "/" )
    ],
    [],
    prep_images_to_xcf,   # Matches to name of function being defined
    menu = "<Image>/Image/Batch Image Prep"  # Menu Location
    )   # End register
	
	
register (
    "prep_xcf_layers",         # Name registered in Procedure Browser
    N_("Adds a Cleaning Layer, a Text Layer Group to this .xcf"), # Widget title
    "Adds a Cleaning Layer, a Text Layer Group to this .xcf", # 
    "LearnCodeWithH",         # Author
    "LearnCodeWithH",         # Copyright Holder
    "Jan 2019",            # Date
    N_("Insert Layers to this .xcf"), # Menu Entry
    "",     # Image Type - No image required
    [
    ( PF_IMAGE, "Image", "Image", None )
    ],
    [],
    prep_xcf_layers,   # Matches to name of function being defined
    menu = "<Image>/Image/Layer Prep This .xcf"  # Menu Location
    )   # End register
	
main()
