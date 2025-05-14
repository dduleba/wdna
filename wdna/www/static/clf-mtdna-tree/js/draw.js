// Add global variable for mutations visibility
var showMutations = false; // Set to false by default
var showBreeds = true; // Set breeds visible by default
var root; // Add global root variable

// Add new constants for layout configuration
var MAX_ROWS_PER_COLUMN = 15; // Maximum number of items in a column
var MIN_COLUMN_WIDTH = 25; // Optimized value (changed from 30 to 25)
var COLUMN_SPACING = 18; // Increased spacing between columns (from 15 to 18)
var NODE_BASE_SEPARATION = 68; // Reduced base node separation (from 75 to 68)

function toggle() {
	var ele = document.getElementById("toggleText");
	var text = document.getElementById("displayText");
	if(ele.style.display == "block") {
    		ele.style.display = "none";
		text.innerHTML = "Legend";
  	}
	else {
		ele.style.display = "block";
		text.innerHTML = "Hide Legend";
	}
} 

// Add mutations toggle function
function toggleMutations() {
    var checkbox = document.getElementById("toggle-mutations");
    showMutations = checkbox.checked;
    updateVisibilityAndLayout();
}

function toggleBreeds() {
    var checkbox = document.getElementById("toggle-breeds");
    showBreeds = checkbox.checked;
    updateVisibilityAndLayout();
}

function init_root(json_root, width){
    root = json_root; // Store root globally
    root.x0 = 0;
    root.y0 = 0;
    expandAll(root);
    
    // Set initial checkbox states
    var mutationsCheckbox = document.getElementById("toggle-mutations");
    var breedsCheckbox = document.getElementById("toggle-breeds");
    if (mutationsCheckbox) {
        mutationsCheckbox.checked = false;
    }
    if (breedsCheckbox) {
        breedsCheckbox.checked = true;
    }
    
    // Precalculate node widths for all nodes before first render
    // This ensures proper spacing on initial layout
    calculateAllNodeWidths(root);
    
    update(root);
    
    // Set initial tree container height based on table visibility
    var tableToggle = document.getElementById("toggle-table");
    updateTreeContainerHeight(!tableToggle || !tableToggle.checked);
    
    // Scroll the tree container instead of the window
    var treeContainer = document.getElementById("tree-container");
    var scrollPosition = width*5/6 - window.innerWidth/2;
    if (treeContainer) {
        setTimeout(function() {
            treeContainer.scrollLeft = scrollPosition;
        }, 100);
    }
}

// Add a new function to calculate node widths for all nodes
function calculateAllNodeWidths(node) {
    if (!node) return;
    
    // Process this node
    calculateNodeWidth(node);
    
    // Process all children
    if (node.children) {
        node.children.forEach(calculateAllNodeWidths);
    }
    if (node._children) {
        node._children.forEach(calculateAllNodeWidths);
    }
}

// Function to calculate width for a single node - without excessive compression
function calculateNodeWidth(node) {
    if (!node || !node.mods) return;
    
    var maxBreedsLength = 0;
    var maxBreedTextWidth = 0;
    var totalNodeWidth = 0;
    
    var sorted = sortMods(node.mods);
    
    // Calculate mutations width - only if they are visible
    var mutationsTotalWidth = 0;
    if (showMutations && sorted.mutations.length > 0) {
        var mutationColumns = organizeIntoColumns(sorted.mutations, MAX_ROWS_PER_COLUMN);
        
        // Calculate actual width considering additional spacing between columns
        var columnCount = mutationColumns.length;
        mutationsTotalWidth = mutationColumns.reduce(function(sum, column) {
            return sum + column.width;
        }, 0);
        
        // Add additional spacing between columns
        if (columnCount > 1) {
            mutationsTotalWidth += (columnCount - 1) * 25; // Significantly increased column spacing (from 15 to 25)
        }
        
        // Better compression for the entire node
        mutationsTotalWidth *= 0.9; // Reduced compression for better readability (from 0.85 to 0.9)
    }
    
    // Calculate breeds width - only if they are visible
    var breedsTotalWidth = 0;
    if (showBreeds && sorted.breeds.length > 0) {
        var breedColumns = organizeIntoColumns(sorted.breeds, MAX_ROWS_PER_COLUMN);
        
        // Calculate actual width considering additional spacing between columns
        var columnCount = breedColumns.length;
        breedsTotalWidth = breedColumns.reduce(function(sum, column) {
            return sum + column.width;
        }, 0);
        
        // Add additional spacing between columns
        if (columnCount > 1) {
            breedsTotalWidth += (columnCount - 1) * 25; // Significantly increased column spacing (from 15 to 25)
        }
        
        // Better compression for the entire node
        breedsTotalWidth *= 0.9; // Reduced compression for better readability (from 0.85 to 0.9)
        
        // Collect information about text length and width
        breedColumns.forEach(function(column) {
            column.items.forEach(function(breed) {
                maxBreedsLength = Math.max(maxBreedsLength, breed.length);
                var breedText = breed.substring(6);
                var textWidth = getTextWidth(breedText, ymodsize);
                maxBreedTextWidth = Math.max(maxBreedTextWidth, textWidth);
            });
        });
    }
    
    // Calculate total node width - include additional margin for multiple columns
    totalNodeWidth = Math.max(breedsTotalWidth, mutationsTotalWidth);
    
    // Additional safety margin for nodes with labels
    if (totalNodeWidth > 0) {
        // Optimal safety margins
        var extraMargin = 10; // Increased base margin (from 8 to 10)
        
        if (sorted.breeds.length > 10 || sorted.mutations.length > 10) {
            extraMargin = 20; // Increased margin for nodes with many labels (from 15 to 20)
        } else if (sorted.breeds.length > 5 || sorted.mutations.length > 5) {
            extraMargin = 15; // Increased margin for nodes with medium number of labels (from 12 to 15)
        }
        
        totalNodeWidth += extraMargin;
    }
    
    // Store calculated values in the node
    node.maxBreedsLength = maxBreedsLength;
    node.maxBreedTextWidth = maxBreedTextWidth;
    node.totalNodeWidth = totalNodeWidth;
    
    // Also save the number of labels for use in separation
    node.breedCount = showBreeds ? sorted.breeds.length : 0;
    node.mutationCount = showMutations ? sorted.mutations.length : 0;
}

// ************** Generate the tree diagram  *****************
var margin = {top: 20, right: 0, bottom: 20, left: 20},
 width = 11000 - margin.right - margin.left,
 height = 1900 - margin.top - margin.bottom,
 ydep = 140,  // Increased vertical spacing between levels (from 130 to 140)
 ymodsize = 7.5;  // Slightly increased font size for better readability (from 7 to 7.5)
var i = 0,
    duration = 750;

// Create tree layout with customized separation function
var tree = d3.layout.tree()
    .nodeSize([65,50])
    .separation(function(a, b) {
        // Use the total node width for spacing calculation
        var aWidth = a.totalNodeWidth || a.maxBreedTextWidth || 0;
        var bWidth = b.totalNodeWidth || b.maxBreedTextWidth || 0;
        
        // Base minimum separation for nodes without labels
        var minSeparation = 1.3; // Optimized base separation (from 1.5 to 1.3)
        
        // If either node has width, calculate additional separation
        if (aWidth > 0 || bWidth > 0) {
            // Use actual node widths
            var additionalSeparation = (aWidth + bWidth) / 90; // Optimized divisor (from 100 to 90)
            
            // Add minimum threshold for nodes with labels
            var minThreshold = 1.4; // Optimized threshold (from 1.5 to 1.4)
            
            // Check label count and adjust distance
            var aCount = (a.breedCount || 0) + (a.mutationCount || 0);
            var bCount = (b.breedCount || 0) + (b.mutationCount || 0);
            
            // Dynamic separation based on label count
            if (aCount > 10 || bCount > 10) {
                minThreshold = 1.6; // Optimized distance for nodes with many labels (from 1.8 to 1.6)
                additionalSeparation *= 1.6; // Optimized separation (from 1.8 to 1.6)
            } else if (aCount > 5 || bCount > 5) {
                minThreshold = 1.5; // Optimized minimum separation (from 1.6 to 1.5)
                additionalSeparation *= 1.4; // Optimized separation (from 1.5 to 1.4)
            }
            
            // Consider column count as well
            var aColumns = Math.ceil((a.breedCount || 0) / MAX_ROWS_PER_COLUMN);
            var bColumns = Math.ceil((b.breedCount || 0) / MAX_ROWS_PER_COLUMN);
            
            // For nodes with multiple columns, add more space inside the node, not between nodes
            if (aColumns > 1 || bColumns > 1) {
                additionalSeparation *= (1 + Math.max(aColumns, bColumns) * 0.15); // Optimized multiplier (from 0.2 to 0.15)
            }
            
            return Math.max(minThreshold, 1.3 + additionalSeparation); // Optimized base value (from 1.5 to 1.3)
        }
        
        return minSeparation;
    });

var diagonal = d3.svg.diagonal()
    .projection(function(d) { return [d.x, d.y]; });
// Get page height
var pageHeight = Math.max(
    document.documentElement.clientHeight,
    document.documentElement.scrollHeight,
    document.documentElement.offsetHeight
);

// Get table container height
// var tableHeight = document.getElementById('table-container').offsetHeight || 0;

// Add function to update SVG height based on table visibility
function updateTreeContainerHeight(isTableHidden) {
    try {
        var pageHeight = Math.max(
            document.documentElement.clientHeight || 0,
            document.documentElement.offsetHeight || 0
        );

        var tableContainer = document.getElementById('table-container');
        if (!tableContainer) return;
        
        var tableHeight = tableContainer.offsetHeight || 70;
        var margins = margin.top + margin.bottom;
        var newHeight = isTableHidden ? (pageHeight - margins - 70) : Math.max(pageHeight - margins - tableHeight, pageHeight - margins - 820);
        
        if (outerSvg && newHeight > 0) {
            console.log('newHeight', newHeight, 'pageHeight', pageHeight, 'margins', margins, 'tableHeight', tableHeight, 'scrollHeight', document.documentElement.scrollHeight);
            outerSvg.attr("height", newHeight);
        }
    } catch (error) {
        console.warn('Error updating tree container height:', error);
    }
}

// Create outer SVG container that will handle zooming
var outerSvg = d3.select("#tree-container").append("svg")
    .attr("width", width + margin.right + margin.left)
    .attr("height", pageHeight * 0.5);

// Add a background rect to catch zoom events
outerSvg.append("rect")
    .attr("class", "zoom-background")
    .attr("width", width + margin.right + margin.left)
    .attr("height", height + margin.top + margin.bottom)
    .style("fill", "none")
    .style("pointer-events", "all");

// Create inner SVG group that will be transformed
var svg = outerSvg.append("g")
    .attr("transform", "translate(" + width*5/6 + "," + margin.top + ")");

// Initialize zoom behavior
var zoom = d3.behavior.zoom()
    .scaleExtent([0.1, 3])
    .on("zoom", function() {
        svg.attr("transform", 
            "translate(" + d3.event.translate + ")scale(" + d3.event.scale + ")");
    });

// Apply zoom behavior to the outer SVG
outerSvg.call(zoom);

// Initialize zoom state
var initialTranslate = [width*5/6, margin.top];
zoom.translate(initialTranslate);

// Handle scrolling
outerSvg.on("wheel.zoom", function() {
    d3.event.preventDefault();
    d3.event.stopPropagation();
    
    var currentTranslate = zoom.translate();
    
    // Handle horizontal scrolling normally
    currentTranslate[0] -= d3.event.deltaX || 0;
    
    // For vertical scrolling, check if we would scroll above COY
    var deltaY = d3.event.deltaY || 0;
    var proposedYTranslate = currentTranslate[1] - deltaY;
    
    // Get the COY node position
    if (root && root.name === "COY") {
        // Calculate the minimum allowed Y translate value
        // This prevents scrolling above the COY node
        var minAllowedY = margin.top;
        
        // Only allow scrolling down (positive deltaY) or 
        // scrolling up (negative deltaY) if we're not going above COY
        if (deltaY > 0 || proposedYTranslate <= minAllowedY) {
            currentTranslate[1] = proposedYTranslate;
        }
    } else {
        // If COY node isn't available for some reason, allow normal scrolling
        currentTranslate[1] -= deltaY;
    }
    
    zoom.translate(currentTranslate);
    zoom.event(outerSvg);
});

// Add zoom control handlers
d3.select("#zoom-in").on("click", function() {
    var currentTranslate = zoom.translate();
    var currentScale = zoom.scale();
    var newScale = currentScale * 1.2;
    zoom.scale(newScale);
    zoom.translate(currentTranslate);
    zoom.event(outerSvg);
});

d3.select("#zoom-out").on("click", function() {
    var currentTranslate = zoom.translate();
    var currentScale = zoom.scale();
    var newScale = currentScale * 0.8;
    zoom.scale(newScale);
    zoom.translate(currentTranslate);
    zoom.event(outerSvg);
});

d3.select("#zoom-reset").on("click", function() {
    zoom.scale(1);
    zoom.translate(initialTranslate);
    zoom.event(outerSvg);
    
    // Force update of the tree with current visibility states
    if (root) {
        update(root);
    }
});

// Store sequences data globally
var sequences_data = [];

// Instead of loading sequences.json, we'll get data from jqGrid
function loadTreeData() {
  // Update status message
  $("#tree-update-status").text("Updating tree visualization...");
  
  // Get data from jqGrid
  var grid = $("#sequences");
  sequences_data = [];
  
  // Get current filter settings
  var postData = grid.jqGrid('getGridParam', 'postData');
  var filters = postData.filters ? JSON.parse(postData.filters) : null;
  
  // Get all filtered data
  function getAllFilteredData() {
    var allData = [];
    var allGridData = grid.jqGrid('getGridParam', 'data');
    
    if (allGridData) {
      allGridData.forEach(function(row) {
        if (matchesFilters(row, filters)) {
          allData.push(row);
        }
      });
    }
    
    return allData;
  }
  
  // Helper function to check if a row matches the current filters
  function matchesFilters(row, filters) {
    if (!filters || !filters.rules || filters.rules.length === 0) {
      return true;
    }
    
    return filters.rules.every(function(rule) {
      var fieldValue = row[rule.field];
      var filterValue = rule.data;
      
      // Convert both values to lowercase strings for case-insensitive comparison
      var fieldValueStr = String(fieldValue || '').toLowerCase();
      var filterValueStr = String(filterValue || '').toLowerCase();
      
      switch(rule.op) {
        case 'eq': return fieldValueStr === filterValueStr;
        case 'ne': return fieldValueStr !== filterValueStr;
        case 'bw': return fieldValueStr.startsWith(filterValueStr);
        case 'bn': return !fieldValueStr.startsWith(filterValueStr);
        case 'ew': return fieldValueStr.endsWith(filterValueStr);
        case 'en': return !fieldValueStr.endsWith(filterValueStr);
        case 'cn': return fieldValueStr.includes(filterValueStr);
        case 'nc': return !fieldValueStr.includes(filterValueStr);
        default: return true;
      }
    });
  }
  
  if (filters && filters.rules && filters.rules.length > 0) {
    sequences_data = getAllFilteredData();
  } else {
    sequences_data = grid.jqGrid('getGridParam', 'data');
  }
  
  console.log("Tree using " + sequences_data.length + " sequences");
  
  // After getting sequences, load tree data
  d3.json("data/tree.json", function(error, json_tree) {
    if (error) {
      console.log("Error loading tree data:", error);
      $("#tree-update-status").text("Error loading tree data: " + error);
      return;
    }
    
    root = json_tree[0];
    // Augment tree nodes with sequence information
    augmentTreeWithSequences(root);
    // Clean up the tree by removing nodes with no breeds
    cleanupTree(root);
    init_root(json_tree[0], width);
    
    // Update status message after tree is loaded
    $("#tree-update-status").text("Tree updated with " + sequences_data.length + " sequences. Filter or sort the table to update the tree visualization.");
  });
}

// Function to augment tree nodes with sequence information
function augmentTreeWithSequences(node) {
  if (!node) return;
  
  // Add breeds info to this node
  node.breeds = [];
  node.breedCounts = {};
  
  // First, process children to ensure breeds are assigned to the most specific nodes first
  if (node.children) {
    node.children.forEach(augmentTreeWithSequences);
  }
  
  // Find sequences that match this haplogroup exactly
  if (node.name) {
    var nodeName = node.name.replace('*', ''); // Remove asterisk if present
    
    // Get all child haplogroup names to exclude breeds already assigned to more specific nodes
    var childHaplogroups = [];
    function collectChildHaplogroups(n) {
      if (n.name) {
        childHaplogroups.push(n.name.replace('*', ''));
      }
      if (n.children) {
        n.children.forEach(collectChildHaplogroups);
      }
      if (n._children) {
        n._children.forEach(collectChildHaplogroups);
      }
    }
    
    if (node.children) {
      node.children.forEach(collectChildHaplogroups);
    }
    if (node._children) {
      node._children.forEach(collectChildHaplogroups);
    }
    
    sequences_data.forEach(function(seq) {
      if (seq.Haplogroup) {
        var haplogroup = seq.Haplogroup;
        
        // Only add breeds that match this exact node and aren't more specific to a child node
        var isExactMatch = haplogroup === nodeName;
        var isMostSpecific = isExactMatch || 
          (haplogroup.startsWith(nodeName) && 
           !childHaplogroups.some(function(childHaplo) {
             return haplogroup.startsWith(childHaplo);
           }));
        
        if (isMostSpecific && seq["Breed of dog"]) {
          var breed = seq["Breed of dog"];
          node.breeds.push(breed);
          
          // Count occurrences of each breed
          node.breedCounts[breed] = (node.breedCounts[breed] || 0) + 1;
          
          // Add breed to mods array with count
          if (!node.mods) node.mods = [];
          // Remove any existing entry for this breed
          node.mods = node.mods.filter(function(mod) {
            return typeof mod !== 'string' || !mod.startsWith("BREED:" + breed);
          });
          // Add new entry with updated count, only show count if > 1, use ' xN' notation
          var breedLabel = breed;
          if (node.breedCounts[breed] > 1) {
            breedLabel += " (" + node.breedCounts[breed] + ")";
          }
          node.mods.push("BREED:" + breedLabel);
        }
      }
    });
  }
}

// Function to clean up the tree by removing nodes with no breeds
function cleanupTree(node) {
  if (!node) return false;

  // Process children first
  if (node.children) {
    // Filter out children that should be removed
    node.children = node.children.filter(function(child) {
      return cleanupTree(child);
    });
  }
  if (node._children) {
    // Filter out _children that should be removed
    node._children = node._children.filter(function(child) {
      return cleanupTree(child);
    });
  }

  // Node should be kept if:
  // 1. It has breeds assigned directly to it, or
  // 2. It has any remaining children after cleanup
  return node.breeds.length > 0 || 
         (node.children && node.children.length > 0) || 
         (node._children && node._children.length > 0);
}

// Helper function to sort mods array
function sortMods(mods) {
    if (!mods) return { breeds: [], mutations: [] };
    
    // Separate breeds and mutations
    let breeds = mods.filter(mod => typeof mod === 'string' && mod.startsWith('BREED:'));
    let mutations = mods.filter(mod => !(typeof mod === 'string' && mod.startsWith('BREED:')));
    
    return { breeds, mutations };
}

function getVisibleMods(mods) {
    if (!mods) return [];
    return mods.filter(mod => {
        var isBreed = typeof mod === 'string' && mod.startsWith("BREED:");
        return (isBreed && showBreeds) || (!isBreed && showMutations);
    });
}

// Helper function to calculate text width
function getTextWidth(text, fontSize) {
    var canvas = document.createElement('canvas');
    var context = canvas.getContext('2d');
    context.font = fontSize + 'px Arial'; // Match the font used in the visualization
    return context.measureText(text).width;
}

// Update the organizeIntoColumns function to ensure proper spacing
function organizeIntoColumns(items, maxRowsPerColumn) {
    if (!items || items.length === 0) return [];
    
    // Calculate maximum text width for proper column sizing
    var maxWidth = 0;
    items.forEach(function(item) {
        var text = typeof item === 'string' && item.startsWith('BREED:') ? 
            item.substring(6) : item;
            
        // Limit text length for width calculation
        // if (text.length > 25) {
        //     text = text.substring(0, 22) + "...";
        // }
        
        var width = getTextWidth(text, ymodsize);
        maxWidth = Math.max(maxWidth, width);
    });
    
    // Add additional width buffer to ensure no overlap
    maxWidth += 5; // Additional 5px for each text
    
    // Stronger compression for readability
    var compressionFactor = 0.95; // Reduced compression for better readability (from 0.9 to 0.95)
    if (items.length > 10) {
        compressionFactor = 0.9; // Reduced compression for large number of items (from 0.8 to 0.9)
    } else if (items.length > 5) {
        compressionFactor = 0.92; // Reduced compression (from 0.85 to 0.92)
    }
    
    // Minimum column width to ensure readability without excess
    var columnWidth = Math.max(MIN_COLUMN_WIDTH, (maxWidth + COLUMN_SPACING) * compressionFactor);
    
    // Maintain standard row count to avoid vertical compression
    var numColumns = Math.ceil(items.length / MAX_ROWS_PER_COLUMN);
    
    // Organize items into columns
    var columns = [];
    for (var i = 0; i < numColumns; i++) {
        var columnItems = items.slice(i * MAX_ROWS_PER_COLUMN, (i + 1) * MAX_ROWS_PER_COLUMN);
        columns.push({
            items: columnItems,
            width: columnWidth + 15 // Increased column spacing (from 10 to 15)
        });
    }
    
    return columns;
}

// Add this function to handle visibility changes and update tree layout
function updateVisibilityAndLayout() {
    // Update mutations visibility
    svg.selectAll(".mutations-group")
        .style("display", showMutations ? "block" : "none");

    // Update breeds visibility
    svg.selectAll(".breeds-group")
        .style("display", showBreeds ? "block" : "none");
    
    // Recalculate all node widths with the new visibility settings
    if (root) {
        calculateAllNodeWidths(root);
        update(root);
    }
}

// Modify the update function to handle the new layout
function update(source) {
    // Compute the new tree layout.
    var nodes = tree.nodes(root).reverse(),
        links = tree.links(nodes);

    // Normalize for fixed-depth.
    nodes.forEach(function(d) { d.y = d.depth * ydep; });

    // Update the nodes…
    var node = svg.selectAll("g.node")
        .data(nodes, function(d) { return d.id || (d.id = ++i); });

    // Enter any new nodes at the parent's previous position.
    var nodeEnter = node.enter().append("g")
        .attr("class", "node")
        .attr("transform", function(d) { return "translate(" + source.x0 + "," + source.y0 + ")"; })
        .on("click", click);

    nodeEnter.append("circle")
        .attr("r", 1e-6)
        .style("fill", function(d) { return d._children ? "lightsteelblue" : "#fff"; })
        .style("stroke", function(d) { return d.children ? "green" : "red"; });

    nodeEnter.append("text")
        .attr("dy", ".35em")
        .attr("x", -5)  // Reduced label spacing from node (from -7 to -5)
        .attr("text-anchor", "end")
        .text(function(d) { return d.name; })
        .style("fill-opacity", 1e-6);

    // Modify the mods group creation and handling
    var modsGroup = nodeEnter.append("g")
        .attr("class", "mods-group");
  
    // Add breeds and mutations with column layout
    modsGroup.each(function(d) {
        if (!d.mods) return;
        var sorted = sortMods(d.mods);
        var container = d3.select(this);
        
        // Recalculate node width to ensure it's up-to-date
        calculateNodeWidth(d);
        
        // Handle mutations first (they go above breeds)
        var mutationsGroup = container.append("g")
            .attr("class", "mutations-group")
            .style("display", showMutations ? "block" : "none");
            
        if (sorted.mutations.length > 0) {
            var mutationColumns = organizeIntoColumns(sorted.mutations, MAX_ROWS_PER_COLUMN);
            var currentX = 0;
            
            mutationColumns.forEach(function(column, columnIndex) {
                column.items.forEach(function(mutation, rowIndex) {
                    // Improve vertical spacing for mutations
                    mutationsGroup.append("text")
                        .attr("x", currentX)
                        .attr("y", -(sorted.breeds.length + rowIndex + 1) * (ymodsize+0.8)) // Increased vertical spacing (from 0.5 to 0.8)
                        .attr("font-size", ymodsize)
                        .attr("text-anchor", "start")
                        .attr("fill", "black")
                        .text(mutation);
                });
                currentX += column.width + 20; // Significantly increased column spacing (from 8 to 20)
            });
        }

        // Handle breeds
        var breedsGroup = container.append("g")
            .attr("class", "breeds-group")
            .style("display", showBreeds ? "block" : "none");
            
        if (sorted.breeds.length > 0) {
            var breedColumns = organizeIntoColumns(sorted.breeds, MAX_ROWS_PER_COLUMN);
            var currentX = 0;
            
            breedColumns.forEach(function(column, columnIndex) {
                column.items.forEach(function(breed, rowIndex) {
                    var breedText = breed.substring(6);
                    breedsGroup.append("text")
                        .attr("x", currentX)
                        .attr("y", -(rowIndex + 1) * (ymodsize+0.8)) // Increased vertical spacing (from 0.5 to 0.8)
                        .attr("font-size", ymodsize)
                        .attr("text-anchor", "start")
                        .attr("fill", "blue")
                        .text(breedText);
                });
                currentX += column.width + 20; // Significantly increased column spacing (from 8 to 20)
            });
        }
    });
   
    
    // Transition nodes to their new position.
    var nodeUpdate = node.transition()
        .duration(duration)
        .attr("transform", function(d) { return "translate(" + d.x + "," + d.y + ")"; });

    nodeUpdate.select("circle")
        .attr("r", 4.5)
        .style("fill", function(d) { 
            if(d._children){
                if (d.children){
                    if (d._children.length == 1){
                        return "#fff";
                    }else{
                        return "lightgreen";
                    }
                }else{
                    return "lightgreen";
                }
            }else{
                return "#fff";
            }
        })
        .style("stroke", function(d) { return d.children || d._children ? "green" : "red"; });

    nodeUpdate.select("text")
        .style("fill-opacity", 1);

    // Update mutations and breeds visibility in the transition
    nodeUpdate.selectAll(".mutations-group")
        .style("display", showMutations ? "block" : "none");

    nodeUpdate.selectAll(".breeds-group")
        .style("display", showBreeds ? "block" : "none");

    // Transition exiting nodes to the parent's new position.
    var nodeExit = node.exit().transition()
        .duration(duration)
        .attr("transform", function(d) { return "translate(" + source.x + "," + source.y + ")"; })
        .remove();

    nodeExit.select("circle")
        .attr("r", 1e-6);

    nodeExit.select("text")
        .style("fill-opacity", 1e-6);

    // Update the links…
    var link = svg.selectAll("path.link")
        .data(links, function(d) { return d.target.id; });

    // Enter any new links at the parent's previous position.
    link.enter().insert("path", "g")
        .attr("class", "link")
        .attr("d", function(d) {
            var o = {x: source.x0, y: source.y0};
            return diagonal({source: o, target: o});
        });

    // Transition links to their new position.
    link.transition()
        .duration(duration)
        .attr("d", diagonal);

    // Transition exiting nodes to the parent's new position.
    link.exit().transition()
        .duration(duration)
        .attr("d", function(d) {
            var o = {x: source.x, y: source.y};
            return diagonal({source: o, target: o});
        })
        .remove();

    // Stash the old positions for transition.
    nodes.forEach(function(d) {
        d.x0 = d.x;
        d.y0 = d.y;
    });
}

function hide(d, all){
  if (!d._children){
    d._children = d.children;
  }
  d.children = [];
  if (d._children){
    d._children.forEach(function(x){
      if (x.hide == false ){
        d.children.push(x);
      }
    });
  } 
  if (all){
    d.children.forEach(function(x){
      if (x.children){
        hide(x,all)
      }
    })
  }
}

function show(d, xall){
  if (xall == 'main_false'){
    if (d._children){
      all_elements=d._children.slice(0)
    }else if(d.children){
      d._children=d.children.slice(0)
      all_elements=d._children.slice(0)
    }else
      all_elements=null
    if (all_elements){
      all_elements.forEach(function(x){
        if (x.hide == false || x.hide == 'main_false'){
          show(x, xall);
          if (d.children && d.children.indexOf(x)==-1){
            d.children.push(x);
          }
        }else if (d.children){
          if (d.children.indexOf(x)>-1){
            d.children.splice(d.children.indexOf(x),1);
          }
        }
      })
    }
  } else{
    if (d._children){
      d._children.forEach(function(x){
        if(d.children && d.children.indexOf(x)>-1){
          if(x.children && xall==true){
            show(x, xall);
            d.children.push(x);
          }
        }else if(!xall){
          hide(x,xall)
        }
      })
      d.children = d._children;
      d._children = null;
    }
    else{
      if(d.children){
        d.children.forEach(function(x){
          show(x,xall)
        })
      }
    }
  }
}

// Toggle children on click.
function _click(d) {
  if ((d.children && !d._children) || (d.children && d.children.length==d._children.length)) {
    if (d.name == 'COY'){
      hide(d, 'KIM')
    }else{
      hide(d, false);
    }
  } else {
    if (d.name == "COY"){
      show(d, 'main_false');
    }else{
      show(d, false);
    }
  }
}

function click(d){
  _click(d);
  update(d);
}

// Add new function to expand all nodes
function expandAll(node) {
  if (node._children) {
    node.children = node._children;
    node._children = null;
    node.children.forEach(expandAll);
  } else if (node.children) {
    node.children.forEach(expandAll);
  }
}

// Table visibility toggle
$("#toggle-table").change(function() {
    var container = $("#table-container");
    if (this.checked) {
        container.css("max-height", container[0].scrollHeight + "px");
        updateTreeContainerHeight(false);
    } else {
        container.css("max-height", "70px");
        updateTreeContainerHeight(true);
    }
});
