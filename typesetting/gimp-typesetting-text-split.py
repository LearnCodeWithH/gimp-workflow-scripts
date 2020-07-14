#!/usr/bin/env python
# -*- coding: utf-8 -*-

import xml.etree.ElementTree as ET
import copy 
import itertools

from gimpfu import *
import os
import re
import math

class glyph_font_attributes:
	__default_color = gimpcolor.RGB(0.0,0.0,0.0,1.0)
	# (font/size/b/i/u/s/color)
	def __init__(self, name = 'Times New Roman', size = 30, gimp_color = None, bold = False, italic = False, underline = False, strikethrough = False):
		self.name = name
		self.size = size # Unused until gimp exposes font sizes through markup...
		if gimp_color is None:
			gimp_color = glyph_font_attributes.__default_color
		self.gimp_color = gimp_color
		self.bold = bold
		self.italic = italic
		self.underline = underline
		self.strikethrough = strikethrough
		
	def __repr__(self):
		return self.__str__()
	
	def __str__(self):
		return "Font Attr+ name: '%s' | size: '%s' | clr: '%s' | b: '%s' | i: '%s' | u: '%s' | s: '%s'" % (self.name, self.size, self.gimp_color, self.bold, self.italic, self.underline, self.strikethrough)
		
	def set_font_attribute(self, attribute_str, value):
		if attribute_str == 'b':
			self.bold = value
		elif attribute_str == 'i':
			self.italic = value
		elif attribute_str == 'u':
			self.underline = value
		elif attribute_str == 's':
			self.strikethrough = value
		else:
			raise ValueError("Valid font attributes are 'b', 'i', 'u', 's'. '%s' is not a valid attribute" % attribute_str)
		


class glyph_packet:
	def __init__(self, glyph = None, font_attributes = None):
		self.glyph = glyph
		self.font_attributes = font_attributes
		
	def __repr__(self):
		return self.__str__()
		
	def __str__(self):
		return "GPacket+ glyph: '%s' | fattr: '%s'" % (self.glyph.encode('utf-8'), self.font_attributes)

class gimp_markup_parser:
	default_font_attributes = glyph_font_attributes()
	font_attributes = ['b','i','u','s']
	font_tag = 'font'
	color_tag = 'foreground'
	blank_re = re.compile('[\s]+', re.UNICODE)

	def __init__(self, root_xml):
		self.__root_xml = root_xml
		
	@staticmethod
	def from_markup_text(markup_text):
		# requires plain str
		root = ET.fromstring(markup_text.encode('utf-8'))
		if root.tag != 'markup':
			root = root.find('markup')
			
		return gimp_markup_parser(root)
		
	@staticmethod
	def __process_markup_xml_to_packets(node, settings_font_attributes, action_lambda):
		if node is None:
			return
	
		if node.tag in gimp_markup_parser.font_attributes:
			settings_font_attributes.set_font_attribute(node.tag, True)
			
			if node.text is not None:
				action_lambda(node, settings_font_attributes)
			for child in node:
				gimp_markup_parser.__process_markup_xml_to_packets(child, settings_font_attributes, action_lambda)
				
			settings_font_attributes.set_font_attribute(node.tag, False)
		else:
			if gimp_markup_parser.font_tag in node.attrib:
				settings_font_attributes.name = node.attrib[gimp_markup_parser.font_tag]
				
			if gimp_markup_parser.color_tag in node.attrib:
				hex_color = node.attrib[gimp_markup_parser.color_tag]
				settings_font_attributes.gimp_color = gimpcolor.rgb_parse_hex(hex_color)
			
			if node.text is not None:
				action_lambda(node, settings_font_attributes)
			for child in node:
				gimp_markup_parser.__process_markup_xml_to_packets(child, settings_font_attributes, action_lambda)
				
	@staticmethod
	def glyph_packets_from_text(unicode_text, settings_font_attributes):
		glyph_packets = []
		for glyph in unicode_text:
			local_font_attributes = copy.copy(settings_font_attributes)
			local_packet = glyph_packet(glyph, local_font_attributes)
			glyph_packets.append(local_packet)
		return glyph_packets
	
	def get_glyph_packets(self, default_font_attributes=None):
		if default_font_attributes is None:
			default_font_attributes = gimp_markup_parser.default_font_attributes
		settings_font_attributes = copy.copy(default_font_attributes)
		
		glyph_packets_list = []
		def gather_glyph_packets(node, settings_font_attributes):
			# gives us back unicode for text after parse.
			local_glyph_list = gimp_markup_parser.glyph_packets_from_text(node.text, settings_font_attributes)
			glyph_packets_list.extend(local_glyph_list)
		
		gimp_markup_parser.__process_markup_xml_to_packets(self.__root_xml, settings_font_attributes, gather_glyph_packets)
		
		return glyph_packets_list
		
class center_points:
	def __init__(self, generator):
		self.__generator = generator
		self.__iter = generator()
		
	@staticmethod
	def layer_center_position(layer):
		width = layer.offsets[0] + (layer.width / 2.0)
		height = layer.offsets[1] + (layer.height / 2.0)
		center_point = (width, height)
		def center_point_gen():
			while 1:
				yield center_point
		return center_points(center_point_gen)
		
	
	@staticmethod
	def vector_interpolate_even(vector, num_points):
		if vector is None:
			raise ValueError("vector does not exist.")
			
		count, strokes = pdb.gimp_vectors_get_strokes(vector)
		if count is 0:
			raise ValueError("vector has no strokes.")
		
		precision = 0.00001
		first_stroke_id = strokes[0]
		first_stroke_length = pdb.gimp_vectors_stroke_get_length(vector, first_stroke_id, precision)
			
		points = []
		spacing = 0.0
		if num_points > 1:
			spacing = first_stroke_length / (num_points - 1)
		for segment in xrange(0, num_points-1):
			distance = segment*spacing
			x, y, slope, valid = pdb.gimp_vectors_stroke_get_point_at_dist(vector, first_stroke_id, distance, precision)
			points.append((x,y))
			
		# End of line can hit precision issues
		x, y, slope, valid = pdb.gimp_vectors_stroke_get_point_at_dist(vector, first_stroke_id, first_stroke_length, precision)
		points.append((x,y))
			
		def interpolate_even_gen():
			for point in points:
				yield point
			raise StopIteration()
			
		return center_points(interpolate_even_gen)
		
	def get_next_center_point(self):
		return next(self.__iter)
		
class font_size_interpolation_params:
	def __init__(self, start_size, end_size, lower_limit, upper_limit):
		if lower_limit > start_size or lower_limit > end_size:
			raise ValueError("Lower Font Size Limit must be less than or equal to Start Size and End Size")
		if upper_limit < end_size or upper_limit < end_size:
			raise ValueError("Upper Font Size Limit must be greater than or equal to Start Size and End Size")
		self.start_size = start_size
		self.end_size = end_size
		self.lower_limit = lower_limit
		self.upper_limit = upper_limit
		
def clamp(n, lower_limit, upper_limit): return max(lower_limit, min(n, upper_limit))
		
class font_size_functions:
	CONSTANT = "Constant"
	LINEAR = "Linear"
	EXP = "Exponential"
	SQUARE_NORM = "Square Normalized X"
	NEG_SQUARE_NORM = "Negative Square Normalized X"
	SQUARE = "Square"
	NEG_SQUARE = "Negative Square"
	PRECISION = 0.00000001

	def __init__(self, generator):
		self.__generator = generator
		self.__iter = generator()

	@staticmethod
	def function_by_name(func_name, interpolation_params, total_steps):
		params = interpolation_params
		if func_name == font_size_functions.CONSTANT:
			return font_size_functions.constant_size_function(params.start_size)
		if func_name == font_size_functions.LINEAR:
			return font_size_functions.linear_size_function(params.start_size, params.end_size, params.lower_limit, params.upper_limit, total_steps)
		if func_name == font_size_functions.SQUARE:
			return font_size_functions.square_size_function(params.start_size, params.end_size, params.lower_limit, params.upper_limit, total_steps, False, True)
		if func_name == font_size_functions.NEG_SQUARE:
			return font_size_functions.square_size_function(params.start_size, params.end_size, params.lower_limit, params.upper_limit, total_steps, False, False)
		if func_name == font_size_functions.SQUARE_NORM:
			return font_size_functions.square_size_function(params.start_size, params.end_size, params.lower_limit, params.upper_limit, total_steps, True, True)
		if func_name == font_size_functions.NEG_SQUARE_NORM:
			return font_size_functions.square_size_function(params.start_size, params.end_size, params.lower_limit, params.upper_limit, total_steps, True, False)
		if func_name == font_size_functions.EXP:
			return font_size_functions.exp_size_function(params.start_size, params.end_size, params.lower_limit, params.upper_limit, total_steps)
		else:
			raise ValueError("No interpolation function found by name '%s'" % func_name)
		
	@staticmethod
	def constant_size_function(constant_size):
		def constant_size_gen():
			while 1:
				yield constant_size
		return font_size_functions(constant_size_gen)

	@staticmethod
	def linear_size_function(start_size, end_size, lower_limit, upper_limit, total_steps):
		def linear_size_gen():
			if total_steps <= 1:
				yield start_size
				raise StopIteration()
			elif total_steps == 2:
				yield start_size
				yield end_size
				raise StopIteration()
			x = start_size
			step_count = 0
			x_step = (end_size - start_size)/float(total_steps-1)
			while 1:
				step_count+=1
				yield x
				if step_count >= total_steps:
					raise StopIteration()
				x += x_step
				x = clamp(x, lower_limit, upper_limit)
		return font_size_functions(linear_size_gen)
		
	
	@staticmethod
	def square_size_function(start_size, end_size, lower_limit, upper_limit, total_steps, even_x_distribution, positive_curve):
		# squared works by scaling the square functions such that the difference between x of start_size and end_size is equal to total_steps-1
		# x can be evenly distributed or weightedly distibuted.
		curve_direction = -1
		mid_const = upper_limit
		if positive_curve:
			curve_direction = 1
			mid_const = lower_limit
			
		rise_percent = 0.5
		fall_percent = 0.5
		if not even_x_distribution:
			start_x_value = math.sqrt(start_size - curve_direction*mid_const)
			end_x_value = math.sqrt(end_size - curve_direction*mid_const)
			rise_percent = start_x_value/(start_x_value+end_x_value)
			fall_percent = end_x_value/(start_x_value+end_x_value)
	
		def square_size_gen():
			if total_steps <= 1:
				yield start_size
				raise StopIteration()
			elif total_steps == 2:
				yield start_size
				yield end_size
				raise StopIteration()
				
			x_step = 1.0
			x_start = -(total_steps-1)*rise_percent
			x_end = (total_steps-1)*fall_percent
			rise_scale = (start_size - mid_const)/(curve_direction*x_start*x_start)
			fall_scale = (end_size - mid_const)/(curve_direction*x_end*x_end)

			x = x_start
			y = (curve_direction*rise_scale*(x*x) + mid_const)
			while 1:
				yield y
				x += x_step
				if x > x_end+font_size_functions.PRECISION:
					raise StopIteration()
				if x <= 0.0:
					y = (curve_direction*rise_scale*(x*x) + mid_const)
				else:
					y = (curve_direction*fall_scale*(x*x) + mid_const)
				y = clamp(y, lower_limit, upper_limit)
				
		
		return font_size_functions(square_size_gen)
		
	
	@staticmethod
	def exp_size_function(start_size, end_size, lower_limit, upper_limit, total_steps):
		def exp_size_gen():
			if total_steps <= 1:
				yield start_size
				raise StopIteration()
			elif total_steps == 2:
				yield start_size
				yield end_size
				raise StopIteration()
				
			x_start = math.log(start_size)
			x_end = math.log(end_size)
			x_step = (x_end - x_start)/float(total_steps-1)
			
			x = x_start
			y = math.exp(x)
			step_count = 0
			while 1:
				step_count+=1
				yield y
				x += x_step
				if step_count >= total_steps:
					raise StopIteration()
				y = math.exp(x)
				y = clamp(y, lower_limit, upper_limit)
		return font_size_functions(exp_size_gen)
		
	def get_next_size(self):
		next_val = next(self.__iter)
		if next_val <= 0:
			next_val = 1
		return next_val
	
##############################

def add_text_layer_from_glyph(image, insert_parent, insert_position, glyph_packet, copy_layer):
	if gimp_markup_parser.blank_re.match(glyph_packet.glyph) is not None:
		return None

	Pixels = 0;
	glyph_attributes = glyph_packet.font_attributes
	split_layer = None
	old_handler = pdb.gimp_message_get_handler(); ConsoleHandler = 1; # Console handler doesnt do a pop up.
	pdb.gimp_message_set_handler(ConsoleHandler)
	try:
		split_layer = pdb.gimp_text_layer_new(image, glyph_packet.glyph, glyph_attributes.name, glyph_attributes.size, Pixels)
	except RuntimeError as re:
		return None # whitespace and control characters fail to create layers, ignore and proceed.
	finally:
		pdb.gimp_message_set_handler(old_handler)
	pdb.gimp_image_insert_layer(image, split_layer, insert_parent, insert_position)
	
	pdb.gimp_text_layer_set_color(split_layer, glyph_attributes.gimp_color)
	pdb.gimp_text_layer_set_font(split_layer, glyph_attributes.name)
	
	base_direction = pdb.gimp_text_layer_get_base_direction(split_layer)
	pdb.gimp_text_layer_set_base_direction(split_layer,base_direction)
	antialias = pdb.gimp_text_layer_get_antialias(split_layer)
	pdb.gimp_text_layer_set_antialias(split_layer, antialias)
	hint_style = pdb.gimp_text_layer_get_hint_style(split_layer)
	pdb.gimp_text_layer_set_hint_style(split_layer, hint_style)
	hinting = pdb.gimp_text_layer_get_hinting(split_layer)
	pdb.gimp_text_layer_set_hinting(split_layer, hinting[0], hinting[1])
	indent = pdb.gimp_text_layer_get_indent(split_layer)
	pdb.gimp_text_layer_set_indent(split_layer, indent)
	justify = pdb.gimp_text_layer_get_justification(split_layer)
	pdb.gimp_text_layer_set_justification(split_layer, justify)
	kerning = pdb.gimp_text_layer_get_kerning(split_layer)
	pdb.gimp_text_layer_set_kerning(split_layer, kerning)
	language = pdb.gimp_text_layer_get_language(split_layer)
	pdb.gimp_text_layer_set_language(split_layer, language)
	letter_spacing = pdb.gimp_text_layer_get_letter_spacing(split_layer)
	pdb.gimp_text_layer_set_letter_spacing(split_layer, letter_spacing)
	line_spacing = pdb.gimp_text_layer_get_line_spacing(split_layer)
	pdb.gimp_text_layer_set_line_spacing(split_layer, line_spacing)
	
	pdb.gimp_text_layer_set_text(split_layer, glyph_packet.glyph)
	
	return split_layer
	
	
def center_layer_on_point(layer, point_tuple):
	split_offset_x = point_tuple[0] - (layer.width / 2.0)
	split_offset_y = point_tuple[1] - (layer.height / 2.0)
	pdb.gimp_layer_set_offsets(layer, split_offset_x, split_offset_y)
	
def default_attributes_from_layer(layer, font_size):
	name = pdb.gimp_text_layer_get_font(layer)
	gimp_color = pdb.gimp_text_layer_get_color(layer)
	settings = glyph_font_attributes(name, font_size, gimp_color)
	return settings
	
def create_split_text_layer_group(image, layer):
	layer_parent = pdb.gimp_item_get_parent(layer)
	layer_position = pdb.gimp_image_get_item_position(image, layer)
	group_title = "Split '%s'" % layer.name
	text_group = pdb.gimp_layer_group_new(image)
	text_group.name = group_title

	pdb.gimp_image_insert_layer(image, text_group, layer_parent, layer_position + 1)
	return text_group
		
def create_glyph_packet_from_source(default_settings, raw_text, markup):
	glyph_packets = []
	if raw_text is not None:
		raw_text = raw_text.encode('utf-8')
		raw_text_packets = gimp_markup_parser.glyph_packets_from_text(raw_text, default_settings)
		glyph_packets.extend(raw_text_packets)
	elif markup is not None:
		markup_packets = gimp_markup_parser.from_markup_text(markup).get_glyph_packets(default_settings)
		glyph_packets.extend(markup_packets)
		
	return glyph_packets
	
def create_position_generator(image, layer, space_on_path, point_count):
	if space_on_path:
		active_vector = pdb.gimp_image_get_active_vectors(image)
		if active_vector is None:
			raise ValueError("No active vector to path along.")
		return center_points.vector_interpolate_even(active_vector, point_count)
	else:
		return center_points.layer_center_position(layer)
		
def get_displayable_glyph_positions_add_to_group(image, layer, spaceOnPath, text_group, glyph_packets):
	# roll through list and add each layer according to attributes(can't set markup, so cant use all font attributes...), positioned at current layer.
	displayable_positions = []
	position_gen = create_position_generator(image, layer, spaceOnPath, len(glyph_packets))
	text_layer_position = 0
	for packet in glyph_packets:
		# create text layer, add to image, copy all attributes of layer
		# can't check if text layer is "visible" b/c we don't know what regex they use to filter, just try to create layer and skip on exceptions
		glyph_layer = add_text_layer_from_glyph(image, text_group, text_layer_position, packet, layer)
		# position layer if it wasnt skipped, keep spacing for unprinted characters so advance generator.
		center_point = position_gen.get_next_center_point()
		if glyph_layer is not None:
			displayable_positions.append(center_point)
		text_layer_position += 1
		
	return displayable_positions
		
def layer_text_by_letter_with_font_step(image, layer, fontSize, spaceOnPath, fontStepParams, interpolationFunc):
	if not pdb.gimp_item_is_text_layer(layer):
		pdb.gimp_message ("Requires a text layer. '%s' is not a text layer." % layer.name)
		return
	# Layer doesnt convert to markup until some deviation from layer's font, check both.
	raw_text = pdb.gimp_text_layer_get_text(layer)
	markup = pdb.gimp_text_layer_get_markup(layer)
	if markup is None and raw_text is None:
		pdb.gimp_message ("Could not find any text in layer '%s'." % layer.name)
		return

	Pixels = 0;
	pdb.gimp_image_undo_group_start(image)
	try:
		# run through markup and build list of unicode characters with attributes (font/size/b/i/u/s/color)
		default_settings = default_attributes_from_layer(layer, fontSize)
		glyph_packets = create_glyph_packet_from_source(default_settings, raw_text, markup)
		# make new layer group with layer name
		text_group = create_split_text_layer_group(image, layer)
		displayable_positions = get_displayable_glyph_positions_add_to_group(image, layer, spaceOnPath, text_group, glyph_packets)
		
		# go through font sizes.
		total_steps = len(text_group.layers)
		font_step = font_size_functions.function_by_name(interpolationFunc, fontStepParams, total_steps)
		
		layer_index = 0
		for glyph_layer in text_group.layers:
			# only want font steps on printable characters.
			next_step = font_step.get_next_size()
			pdb.gimp_text_layer_set_font_size(glyph_layer, next_step, Pixels)
			
			center_layer_on_point(glyph_layer, displayable_positions[layer_index])
			layer_index += 1
		
	finally:
		pdb.gimp_image_undo_group_end(image)
		
	return
	
def layer_text_by_letter(image, layer, fontSize, spaceOnPath):
	font_step_params = font_size_interpolation_params(fontSize, fontSize, fontSize, fontSize)
	layer_text_by_letter_with_font_step(image, layer, fontSize, spaceOnPath, font_step_params, font_size_functions.CONSTANT)
	
def layer_text_by_letter_with_font_size_interpolation(image, layer, interpolationFunc, startSize, endSize, lowerSizeLimit, upperSizeLimit, spaceOnPath):
	font_step_params = font_size_interpolation_params(startSize, endSize, lowerSizeLimit, upperSizeLimit)
	layer_text_by_letter_with_font_step(image, layer, startSize, spaceOnPath, font_step_params, interpolationFunc)
	

register (
    "layer_text_by_letter",         # Name registered in Procedure Browser
    N_("Splits a text layer into multiple layers with 1 letter each."), # Widget title
    "Splits a text layer into multiple layers with 1 letter each.", # 
    "LearnCodeWithH",         # Author
    "LearnCodeWithH",         # Copyright Holder
    "Jan 2019",            # Date
    N_("Layer Text by Letter"), # Menu Entry
    "",     # Image Type - No image required
    [
	( PF_IMAGE, "Image", "Image", None ),
	( PF_DRAWABLE, "Layer", "Layer", None ),
    ( PF_SPINNER, "fontSize", "Font Size:", 30, (1, 3000, 1)),
    ( PF_BOOL, "spaceOnPath", "Space on Active Path?:", False )
    ],
    [],
    layer_text_by_letter,   # Matches to name of function being defined
    menu = "<Image>/Filters/Typesetting"  # Menu Location
    )   # End register
	
register (
    "layer_text_by_letter_with_font_size_interpolation",         # Name registered in Procedure Browser
    N_("Splits a text layer into multiple layers with 1 letter each, changing font size according to the given function for each glyph."), # Widget title
    "Splits a text layer into multiple layers with 1 letter each, changing font size according to the given function for each glyph.", # 
    "LearnCodeWithH",         # Author
    "LearnCodeWithH",         # Copyright Holder
    "Jan 2019",            # Date
    N_("Layer Text by Letter, Interpolate Font Size"), # Menu Entry
    "",     # Image Type - No image required
    [
	( PF_IMAGE, "Image", "Image", None ),
	( PF_DRAWABLE, "Layer", "Layer", None ),
    ( PF_RADIO, "interpolationFunc", "Interpolation Function:", font_size_functions.LINEAR,
            (
                 (font_size_functions.LINEAR, font_size_functions.LINEAR),
                 (font_size_functions.SQUARE, font_size_functions.SQUARE),
                 (font_size_functions.NEG_SQUARE, font_size_functions.NEG_SQUARE),
                 (font_size_functions.SQUARE_NORM, font_size_functions.SQUARE_NORM),
                 (font_size_functions.NEG_SQUARE_NORM, font_size_functions.NEG_SQUARE_NORM),
                 (font_size_functions.EXP, font_size_functions.EXP)
            ) ),
    ( PF_SPINNER, "startSize", "Start Font Size:", 30, (1, 3000, 1)),
    ( PF_SPINNER, "endSize", "End Font Size:", 30, (1, 3000, 1) ),
    ( PF_SPINNER, "lowerSizeLimit", "Lower Font Size Limit:", 5, (1, 3000, 1)),
    ( PF_SPINNER, "upperSizeLimit", "Upper Font Size Limit:", 50, (1, 3000, 1) ),
    ( PF_BOOL, "spaceOnPath", "Space on Active Path?:", False )
    ],
    [],
    layer_text_by_letter_with_font_size_interpolation,   # Matches to name of function being defined
    menu = "<Image>/Filters/Typesetting"  # Menu Location
    )   # End register

main()
