# This script generates new Sumo subnetwork net and rou xml files from existing xml Sumo network
# See http://sumo.dlr.de/wiki/Networks/SUMO_Road_Networks for reference in SUMO net.xml formatting

import re

#######################
# CONSTANTS. 
# Change customizable script parameters here.
#######################

# Boundary box parameters. Change them here
# For Luxembourg, x/y values typically range from 1000-11000
XMIN = 5000 
XMAX = 8000
YMIN = 5000
YMAX = 8000

# Change this to False to relax assertions on line counts expected of a well-formatted input XML.
# This script still makes some assumptions on xml formatting 
# (such as no spaces between '=' in 'junction id=val', 
# each node or network element starting on its own new line, etc.)
ASSERT_FORMATTING = True

# For debugging. Prints xml lines before removing them. Change to False to silence.
PRINT_REMOVED_LINES = False

# Original full network XML file locations. Change them here
net_xml = "/Users/crystalyan/codeRepos/flow-project/LuSTScenario/scenario/lust.net.xml"
rou_xml = "/Users/crystalyan/codeRepos/flow-project/LuSTScenario/scenario/DUARoutes/local.1.rou.xml"

print("...Using boundary box: x = [{}, {}] y = [{}, {}]".format(XMIN, XMAX, YMIN, YMAX))
print("...Using original net xml file at {}".format(net_xml))
print("...Using original rou xml file at {}".format(rou_xml))


########################
# SCRIPT OVERVIEW
# Step 1: [Net xml] Remove nodes (junctions) based off x, y positions. Take note of lanes attached to nodes
# Step 2: [Net xml] Remove traffic lights (tl) at corresponding removed junctions
# Step 3: [Net xml] Remove edges that contain lanes from removed nodes
# Step 4: [Net xml] Remove connections that contain edges, via, or traffic lights that were removed
# Step 5: [Rou xml] Remove vehicles
########################

nodes_keep = set()
nodes_remove = set()

lanes_keep = set()
lanes_remove = set()

edges_keep = set()
edges_remove = set()

mod_net_file = ""  # Mod_net_file is the file copy that is modified in-place during each step.

with open(net_xml, 'r') as net_file:
	orig_net_file = net_file.read()
	mod_net_file = orig_net_file

	########################
	# Step 1: Process nodes/junctions in netfile, 
	# throw out nodes whose absolute positions are outside of boundary box,
	# record lanes attached to nodes
	########################

	print("*** STEP 1 of 5: REMOVING OUT-OF-BOUNDS JUNCTIONS (NODES) *******************")

	num_junctions_simple = 0 
	num_junctions_nested = 0

	# Junction has two format cases:
	# Simple and one-line: <junction .../>
	# and
	# Nested and multi-line: <junction ...> <inner field/> </junction>

	# Step 1a) Find and process all simple one-line junction cases
	print("*** ... Step 1a: Removing simple junctions ... ***")
	simple_node_pattern = '<junction [^<]*?/>\n' # [^<] must not contain inner clause '<'
	for simple_node_found in re.finditer(simple_node_pattern, orig_net_file):
		simple_node = simple_node_found.group(0) # Substring in orig_net_file matching regex

		# Parse node id string, x and y position
		id_pattern = 'id=".*?"'
		node_id = re.search(id_pattern, simple_node).group(0).split('"')[1]
		x_pattern = 'x=".*?"'
		x = float(re.search(x_pattern, simple_node).group(0).split('"')[1])
		y_pattern = 'y=".*?"'
		y = float(re.search(y_pattern, simple_node).group(0).split('"')[1])
		#print(node_id, x, y) # For debugging/viewing the node data

		# Parse lanes
		incLanes_pattern = 'incLanes=".*?"' # Incoming lanes
		incLanes = re.search(incLanes_pattern, simple_node).group(0).split('"')[1]
		incLanes_lst = incLanes.split(' ')

		intLanes_pattern = 'intLanes=".*?"' # Internal lanes
		intLanes = re.search(intLanes_pattern, simple_node).group(0).split('"')[1]
		intLanes_lst = intLanes.split(' ')

		lanes_lst = incLanes_lst + intLanes_lst

		if x < XMIN or x > XMAX or y < YMIN or y > YMAX:
			# Record-keeping
			nodes_remove.add(node_id)
			lanes_remove.update(lanes_lst)

			remove_pattern1 = '<junction id="'+node_id+'" [^<]*?/>\n'

			if PRINT_REMOVED_LINES and re.search(remove_pattern1, mod_net_file):
				print(re.search(remove_pattern1, mod_net_file).group(0)) 
			
			remove_net_file, num_replaced1 = re.subn(remove_pattern1, '', mod_net_file, count=1) 
			assert num_replaced1 == 1
			num_junctions_simple += num_replaced1

			mod_net_file = remove_net_file

		else:
			# Record-keeping
			nodes_keep.add(node_id)
			lanes_keep.update(lanes_lst)

	desimp_net_file = mod_net_file

	# Step 1b) Find and process all nested multi-line junction cases. 
	# All simple out-of-bounds junctions must be gone, 
	# as newline regex would otherwise overrun simple junctions
	# and remove multiple junction clauses (and everything in between) at once
	print("*** ... Step 1b: Removing nested junctions ... ***")
	nested_node_pattern = '<junction [\s\S]*?</junction>\n' # [\s\S] allows newline within clause
	for nested_node_found in re.finditer(nested_node_pattern, desimp_net_file):
		nested_node = nested_node_found.group(0) # Substring in orig_net_file matching regex

		# Parse node id string, x and y position
		id_pattern = 'id=".*?"'
		node_id = re.search(id_pattern, nested_node).group(0).split('"')[1]
		x_pattern = 'x=".*?"'
		x = float(re.search(x_pattern, nested_node).group(0).split('"')[1])
		y_pattern = 'y=".*?"'
		y = float(re.search(y_pattern, nested_node).group(0).split('"')[1])
		#print(node_id, x, y) # For debugging/viewing the node data

		# Parse lanes
		incLanes_pattern = 'incLanes=".*?"' # Incoming lanes
		incLanes = re.search(incLanes_pattern, simple_node).group(0).split('"')[1]
		incLanes_lst = incLanes.split(' ')

		intLanes_pattern = 'intLanes=".*?"' # Internal lanes
		intLanes = re.search(intLanes_pattern, simple_node).group(0).split('"')[1]
		intLanes_lst = intLanes.split(' ')

		lanes_lst = incLanes_lst + intLanes_lst

		if x < XMIN or x > XMAX or y < YMIN or y > YMAX:
			# Record-keeping
			nodes_remove.add(node_id)
			lanes_remove.update(lanes_lst)

			remove_pattern2 = '<junction id="'+node_id+'" [\s\S]*?</junction>\n'

			if PRINT_REMOVED_LINES and re.search(remove_pattern2, mod_net_file):
				print(re.search(remove_pattern2, mod_net_file).group(0)) 
			
			remove_net_file, num_replaced2 = re.subn(remove_pattern2, '', mod_net_file, count=1) 
			assert num_replaced2 == 1
			num_junctions_nested += num_replaced2

			mod_net_file = remove_net_file

		else:
			# Record-keeping
			nodes_keep.add(node_id)
			lanes_keep.update(lanes_lst)

	# If lanes to-keep and to-remove intersect, default to removing the lane
	lanes_keep = lanes_keep - lanes_remove


	print("... Number of nodes kept: {} vs. nodes removed: {}".format(len(nodes_keep), len(nodes_remove)))
	print("... Number of lanes kept: {} vs. lanes removed: {}".format(len(lanes_keep), len(lanes_remove)))
	print("... Number of junction clauses removed: {} simple vs. {} nested" \
			.format(num_junctions_simple, num_junctions_nested)) 

	# Check to-keep and to-remove lists do not intersect
	assert not bool(nodes_keep & nodes_remove)
	assert not bool(lanes_keep & lanes_remove)

	if ASSERT_FORMATTING:
		num_mod_lines = len(mod_net_file.split('\n'))
		num_orig_lines = len(orig_net_file.split('\n'))

		# Check at least (number_of_nodes_removed) lines were removed from the net xml
		assert num_mod_lines <= num_orig_lines - len(nodes_remove)

		# Check at least one line was removed for every simple junction, and three lines for every nested
		assert num_mod_lines <= num_orig_lines - num_junctions_simple - (3*num_junctions_nested)


	########################
	# Step 2: Process traffic lights in netfile,
	# throw out traffic light nested clauses placed at removed nodes
	########################

	print("*** STEP 2 of 5: REMOVING OUT-OF-BOUNDS TRAFFIC LIGHTS *******************")

	dejunct_net_file = mod_net_file

	num_tl_kept = 0
	num_tl_removed = 0

	tl_pattern = '<tlLogic [\s\S]*?</tlLogic>\n' # [\s\S] allows newline within clause
	for tl_found in re.finditer(tl_pattern, dejunct_net_file):
		tl = tl_found.group(0)

		# Parse tl's junction id
		id_pattern = 'id=".*?"'
		node_id = re.search(id_pattern, tl).group(0).split('"')[1]

		if node_id in nodes_remove:
			remove_pattern = remove_pattern2 = '<tlLogic id="'+node_id+'" [\s\S]*?</tlLogic>\n'

			if PRINT_REMOVED_LINES and re.search(remove_pattern, mod_net_file):
				print(re.search(remove_pattern, mod_net_file).group(0))

			remove_net_file, num_replaced = re.subn(remove_pattern, '', mod_net_file, count=1)
			num_tl_removed += 1
			assert num_replaced == 1

			mod_net_file = remove_net_file
		else:
			num_tl_kept += 1


	print("... Number of traffic lights kept: {} vs. traffic lights removed: {}" \
			.format(num_tl_kept, num_tl_removed))

	if ASSERT_FORMATTING:
		num_mod_lines = len(mod_net_file.split('\n'))
		num_dejunct_lines = len(dejunct_net_file.split('\n'))
		# Since traffic lights are nested, assert at least three lines removed for every traffic light
		assert num_mod_lines <= num_dejunct_lines - (3*num_tl_removed)


	########################
	# Step 3: Process edges in netfile, 
	# throw out edges that contain out-of-bounds nodes that were removed
	########################

	print("*** STEP 3 of 5: REMOVING OUT-OF-BOUNDS EDGES BY LANES *******************")
	
	denode_net_file = mod_net_file

	edge_pattern = '<edge [\s\S]*?</edge>\n' # Edges are multi-line with nested lane tags
	for edge_found in re.finditer(edge_pattern, denode_net_file):
		edge = edge_found.group(0)


