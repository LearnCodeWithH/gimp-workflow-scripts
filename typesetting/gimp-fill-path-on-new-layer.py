#!/usr/bin/env python
# -*- coding: utf-8 -*-

from gimpfu import *
import os

def add_layer_above(image, layer, layer_name=None):
	layer_parent = pdb.gimp_item_get_parent(layer)
	layer_position = pdb.gimp_image_get_item_position(image, layer)
	if layer_name is None:
		layer_name = layer.name
	
	if image.base_type is RGB:
		type = RGBA_IMAGE
	else:
		type = GRAYA_IMAGE
		
	new_layer = gimp.Layer(image, "Filled '%s'" % (layer_name), image.width, image.height, type, 100, NORMAL_MODE)
	pdb.gimp_image_insert_layer(image, new_layer, layer_parent, layer_position)
	return new_layer

def fill_selection(layer, outlineColor=None):
	old_fg = pdb.gimp_palette_get_foreground()
	if outlineColor is None:
		outlineColor = old_fg
	try:	
		pdb.gimp_palette_set_foreground(outlineColor)	
		ForegroundBucketFill = 0; NormalMode = 0; SampleMerged = False;
		pdb.gimp_edit_bucket_fill(layer, ForegroundBucketFill, NormalMode, 100.0, 255, SampleMerged, 0, 0)	
	finally:
		pdb.gimp_palette_set_foreground(old_fg)	
	
def fill_path_on_new_layer(image, activeLayer):
	pdb.gimp_image_undo_group_start(image)
	try:
		# get active vector
		active_vector = pdb.gimp_image_get_active_vectors(image)
		if active_vector is None:
			raise ValueError("No active vector to path along.")
		# make new layer above
		new_layer = add_layer_above(image, activeLayer, active_vector.name)
		# vector to selection
		REPLACE = 2
		pdb.gimp_vectors_to_selection(active_vector, REPLACE, True, False, 0.0, 0.0)
		# fill with foreground color
		fill_selection(new_layer)
		
		if pdb.gimp_vectors_get_visible(active_vector):
			pdb.gimp_vectors_set_visible(active_vector, False)
		
		pdb.plug_in_autocrop_layer(image, crop_layer)
	finally:
		pdb.gimp_image_undo_group_end(image)

register (
    "fill_path_on_new_layer",         # Name registered in Procedure Browser
    N_("Creates a new layer, and fills the path with foreground color."), # Widget title
    "Creates a new layer, and fills the path with foreground color.", # 
    "LearnCodeWithH",         # Author
    "LearnCodeWithH",         # Copyright Holder
    "Jan 2019",            # Date
    N_("Fill Path on New Layer"), # Menu Entry
    "",     # Image Type - No image required
    [
	( PF_IMAGE, "Image", "Image", None ),
    ( PF_DRAWABLE, "ActiveLayer", "ActiveLayer", None)
    ],
    [],
    fill_path_on_new_layer,   # Matches to name of function being defined
    menu = "<Image>/Filters/Typesetting"  # Menu Location
    )   # End register
	
main()
