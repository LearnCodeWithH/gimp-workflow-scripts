#!/usr/bin/env python

from gimpfu import *
import os
import re

def create_selection(image, layer):
	if pdb.gimp_item_is_text_layer(layer):
		selection_from_text_path(image, layer)
	else:
		# Replace selection using layer's alpha channel
		ReplaceSelection = 2
		pdb.gimp_image_select_item(image, ReplaceSelection, layer)

def selection_from_text_path(image, layer):
	text_vector = pdb.gimp_vectors_new_from_text_layer(image, layer)
	pdb.gimp_image_insert_vectors(image, text_vector, None, 0)
	# Replace selection with text vector
	antialias = True; feather = False; ReplaceSelection = 2;
	pdb.gimp_vectors_to_selection(text_vector, ReplaceSelection, antialias, feather, 0.0, 0.0)
													
def add_layer_beneath(image, layer):
	layer_parent = pdb.gimp_item_get_parent(layer)
	layer_position = pdb.gimp_image_get_item_position(image, layer)
	
	if image.base_type is RGB:
		type = RGBA_IMAGE
	else:
		type = GRAYA_IMAGE
		
	new_layer = gimp.Layer(image, "Outline '%s'" % (layer.name), image.width, image.height, type, 100, NORMAL_MODE)
	pdb.gimp_image_insert_layer(image, new_layer, layer_parent, layer_position+1)
	return new_layer

def fill_selection(layer, outlineColor):
	old_fg = pdb.gimp_palette_get_foreground()
	try:	
		pdb.gimp_palette_set_foreground(outlineColor)	
		ForegroundBucketFill = 0; NormalMode = 0; SampleMerged = False;
		pdb.gimp_edit_bucket_fill(layer, ForegroundBucketFill, NormalMode, 100.0, 255, SampleMerged, 0, 0)	
	finally:
		pdb.gimp_palette_set_foreground(old_fg)	
		
def solid_outline_layer_single_layer(image, layer, outlineColor, outlinePxSize, mergeLayers):
	# get a path of current layer edges or alpha layer
	create_selection(image, layer)
	# make new layer below current layer
	new_layer = add_layer_beneath(image, layer)
	# grow selection by outlinePxSize
	pdb.gimp_selection_grow(image, outlinePxSize)
	# fill selection on new layer with outlineColor
	fill_selection(new_layer, outlineColor)
	
	crop_layer = new_layer
	# merge if wanted, use base layer name.
	if mergeLayers:
		# Expand as needed when merging down
		ExpandAsNeeded = 0
		orig_layer_name = layer.name
		merged_layer = pdb.gimp_image_merge_down(image, layer, ExpandAsNeeded)
		merged_layer.name = orig_layer_name
		crop_layer = merged_layer
		
	pdb.plug_in_autocrop_layer(image, crop_layer)
	
def solid_outline_layer_group_layer(image, layer, outlineColor, outlinePxSize, mergeLayers):
	for child_layer in layer.layers:
		if pdb.gimp_item_is_group(child_layer):
			solid_outline_layer_group_layer(image, child_layer, outlineColor, outlinePxSize, mergeLayers)
		elif pdb.gimp_item_is_layer(child_layer) or pdb.gimp_item_is_text_layer(child_layer):
			solid_outline_layer_single_layer(image, child_layer, outlineColor, outlinePxSize, mergeLayers)

def solid_outline_layer(image, outlineColor, outlinePxSize, mergeLayers):
	# Workaround for cant pickle layer groups...
	layer = pdb.gimp_image_get_active_layer(image)
	pdb.gimp_image_undo_group_start(image)
	try:
		if pdb.gimp_item_is_group(layer):
			solid_outline_layer_group_layer(image, layer, outlineColor, outlinePxSize, mergeLayers)
		elif pdb.gimp_item_is_layer(layer) or pdb.gimp_item_is_text_layer(layer):
			solid_outline_layer_single_layer(image, layer, outlineColor, outlinePxSize, mergeLayers)
		else:
			pdb.gimp_message("Layer '%s' must be text, layer, or layer group to outline." % layer.name)
	finally:
		pdb.gimp_image_undo_group_end(image)
		
	return
	
register (
    "solid_outline_layer",         # Name registered in Procedure Browser
    N_("Outline layer with solid and possibly merge outline layers"), # Widget title
    "Outlines layer with specified growth with solid color, and merges if specified.", # 
    "LearnCodeWithH",         # Author
    "LearnCodeWithH",         # Copyright Holder
    "Jan 2019",            # Date
    N_("Solid Outline Layer"), # Menu Entry
    "",     # Image Type - No image required
    [
	( PF_IMAGE, "Image", "Image", None ),
    ( PF_COLOR, "outlineColor", "Outline Color:", gimpcolor.RGB(1.0,1.0,1.0,1.0) ),
    ( PF_SPINNER, "outlinePxSize", "Outline Pixel Size:", 4, (-3000, 3000, 1) ),
    ( PF_BOOL, "mergeLayers", "Merge Layers?:", False )
    ],
    [],
    solid_outline_layer,   # Matches to name of function being defined
    menu = "<Image>/Filters/Typesetting"  # Menu Location
    )   # End register
	
main()
