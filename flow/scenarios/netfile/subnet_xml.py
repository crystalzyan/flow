# This script generates new Sumo subnetwork net and rou xml files from existing xml Sumo network

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
# (such as no spaces between '=' in 'junction id=val', or
# id, x, and y fields being in same line as junction begin clause, etc.)
ASSERT_FORMATTING = True

# For debugging. Prints xml lines before removing them. Change to False to silence.
PRINT_REMOVED_LINES = True

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
mod_net_file = ""  # Mod_net_file is the file copy that is modified in-place during each step.

with open(net_xml, 'r') as net_file:
	orig_net_file = net_file.read()
	orig_net_lst = orig_net_file.split('\n')
	mod_net_file = orig_net_file

	########################
	# Step 1: Process nodes/junctions in netfile, 
	# throw out nodes whose absolute positions are outside of boundary box,
	# record lanes attached to nodes
	########################

	print("*** STEP 1 of 5: REMOVING OUT-OF-BOUNDS JUNCTIONS (NODES) *******************")

	num_junctions_simple = 0 
	num_junctions_nested = 0

	for line in orig_net_lst:
		node_pattern = '<junction id=".*?"' # Beginning of a junction clause, includes id string
		node_found = re.search(node_pattern, line)
		if node_found:
			# Parse node id string, x and y position
			id_pattern = 'id=".*?"'
			node_id = re.search(id_pattern, line).group(0).split('"')[1]
			x_pattern = 'x=".*?"'
			x = float(re.search(x_pattern, line).group(0).split('"')[1])
			y_pattern = 'y=".*?"'
			y = float(re.search(y_pattern, line).group(0).split('"')[1])
			#print(node_id, x, y) # For debugging/viewing the node data

			if x < XMIN or x > XMAX or y < YMIN or y > YMAX:
				nodes_remove.add(node_id)

				# Replace junction clause with empty string
				# Junction has two format cases:
				# <junction .../>
				# and
				# <junction ...> <inner field/> </junction>

				# Simple junction clause case
				remove_pattern1 = '<junction id="'+node_id+'" [^<]*?/>\n' # Must not contain inner clause '<'

				if PRINT_REMOVED_LINES and re.search(remove_pattern1, mod_net_file):
					print(re.search(remove_pattern1, mod_net_file).group(0)) 
				
				remove_net_file, num_replaced1 = re.subn(remove_pattern1, '', mod_net_file, count=1) 
				num_junctions_simple += num_replaced1

				# Failed -> nested junction clause case
				if num_replaced1 == 0:
					# Current junction includes inner clause
					remove_pattern2 = 'junction id="'+node_id+'" [\s\S]*?</junction>\n' # Allows newline within clause

					if PRINT_REMOVED_LINES and re.search(remove_pattern2, mod_net_file):
						print(re.search(remove_pattern2, mod_net_file).group(0)) 
					
					remove_net_file, num_replaced2 = re.subn(remove_pattern2, '', mod_net_file, count=1) 
					num_junctions_nested += 1
					assert num_replaced2 == 1 # Only simple or nested junction case exist

				mod_net_file = remove_net_file

			else:
				nodes_keep.add(node_id)

	print("... Number of nodes kept: {} vs. nodes removed: {}".format(len(nodes_keep), len(nodes_remove)))
	print("... Number of junction clauses removed: {} simple vs. {} nested" \
			.format(num_junctions_simple, num_junctions_nested)) 

	if ASSERT_FORMATTING:
		# Check at least (number_of_nodes_removed) lines were removed from the net xml
		assert len(mod_net_file.split('\n')) <= len(orig_net_lst) - len(nodes_remove)

		# Check at least one line was removed for every simple junction, and three lines for every nested
		assert len(mod_net_file.split('\n')) <= len(orig_net_lst) - num_junctions_simple - (3*num_junctions_nested)


	########################
	# Step 2: Process traffic lights in netfile,
	# throw out traffic light nested clauses placed at removed nodes
	########################

	print("*** STEP 2 of 5: REMOVING OUT-OF-BOUNDS TRAFFIC LIGHTS *******************")

	dejunct_net_lst = mod_net_file.split('\n')
	num_tl_kept = 0
	num_tl_removed = 0
	for line in dejunct_net_lst:
		tl_pattern = '<tlLogic id=".*?"'
		tl_found = re.search(tl_pattern, line)
		if tl_found:
			# Parse tl's junction id
			id_pattern = 'id=".*?"'
			node_id = re.search(id_pattern, line).group(0).split('"')[1]

			if node_id in nodes_remove:
				full_tl_pattern = '<tlLogic [\s\S]*?</tlLogic>\n' # Allows newline within clause

				if PRINT_REMOVED_LINES and re.search(full_tl_pattern, mod_net_file):
					print(re.search(full_tl_pattern, mod_net_file).group(0))

				remove_net_file, num_replaced = re.subn(full_tl_pattern, '', mod_net_file, count=1)
				num_tl_removed += 1
				assert num_replaced == 1

				mod_net_file = remove_net_file
			else:
				num_tl_kept += 1

	print("... Number of traffic lights kept: {} vs. traffic lights removed: {}" \
			.format(num_tl_kept, num_tl_removed))

	if ASSERT_FORMATTING:
		# Since traffic lights are nested, assert at least three lines removed for every traffic light
		assert len(mod_net_file.split('\n')) <= len(dejunct_net_lst) - (3*num_tl_removed)


	# ########################
	# # Step 3: Process edges in netfile, 
	# # throw out edges that contain out-of-bounds nodes that were removed
	# ########################
	#
	# denode_net_lst = mod_net_file.split('\n')
	# for line in denode_net_lst:
	# 	edge_pattern = '<edge .*?</edge>\n'
	# 	edge_found = re.search(edge_pattern, line)
	# 	if edge_found:
	# 		# Parse edge id, lane ids
	# 		...
