// Add global variable for mutations visibility
var showMutations = false; // Set to false by default
var showBreeds = true; // Set breeds visible by default
var root; // Add global root variable

// Add new constants for layout configuration
var MAX_ROWS_PER_COLUMN = 15; // Maximum number of items in a column
var MIN_COLUMN_WIDTH = 20; // Minimum width for a column in pixels
var COLUMN_SPACING = 10; // Spacing between columns in pixels

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
    if (root) {
        update(root); // Update tree visualization
    }
}

function toggleBreeds() {
    var checkbox = document.getElementById("toggle-breeds");
    showBreeds = checkbox.checked;
    if (root) {
        update(root);
    }
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
    
    update(root);
    
    // Scroll the tree container instead of the window
    var treeContainer = document.getElementById("tree-container");
    var scrollPosition = width*5/6 - window.innerWidth/2;
    if (treeContainer) {
        setTimeout(function() {
            treeContainer.scrollLeft = scrollPosition;
        }, 100);
    }
}

// ************** Generate the tree diagram  *****************
var margin = {top: 20, right: 0, bottom: 20, left: 20},
 width = 11000 - margin.right - margin.left,
 height = 1900 - margin.top - margin.bottom,
 ydep = 150,
 ymodsize = 8;
var i = 0,
    duration = 750;

var tree = d3.layout.tree()
    .nodeSize([75,50]);
var diagonal = d3.svg.diagonal()
    .projection(function(d) { return [d.x, d.y]; });

// Create outer SVG container that will handle zooming
var outerSvg = d3.select("#tree-container").append("svg")
    .attr("width", width + margin.right + margin.left)
    .attr("height", height + margin.top + margin.bottom);

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
    
    // Handle both horizontal and vertical scrolling
    currentTranslate[0] -= d3.event.deltaX || 0;  // Horizontal scrolling
    currentTranslate[1] -= d3.event.deltaY || 0;  // Vertical scrolling
    
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
  if (node._children) {
    node._children.forEach(augmentTreeWithSequences);
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
            return typeof mod !== 'string' || !mod.startsWith("BREED:" + breed + " (");
          });
          // Add new entry with updated count
          node.mods.push("BREED:" + breed + " (" + node.breedCounts[breed] + ")");
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

// Helper function to organize items into columns
function organizeIntoColumns(items, maxRowsPerColumn) {
    if (!items || items.length === 0) return [];
    
    // Calculate maximum text width for proper column sizing
    var maxWidth = 0;
    items.forEach(function(item) {
        var text = typeof item === 'string' && item.startsWith('BREED:') ? 
            item.substring(6) : item;
        var width = getTextWidth(text, ymodsize);
        maxWidth = Math.max(maxWidth, width);
    });
    
    // Calculate number of columns needed
    var columnWidth = Math.max(MIN_COLUMN_WIDTH, maxWidth + COLUMN_SPACING);
    var numColumns = Math.ceil(items.length / maxRowsPerColumn);
    
    // Organize items into columns
    var columns = [];
    for (var i = 0; i < numColumns; i++) {
        var columnItems = items.slice(i * maxRowsPerColumn, (i + 1) * maxRowsPerColumn);
        columns.push({
            items: columnItems,
            width: columnWidth
        });
    }
    
    return columns;
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
        .attr("x", -7)
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
        
        // Handle mutations first (they go above breeds)
        var mutationsGroup = container.append("g")
            .attr("class", "mutations-group")
            .style("display", showMutations ? "block" : "none");
            
        if (sorted.mutations.length > 0) {
            var mutationColumns = organizeIntoColumns(sorted.mutations, MAX_ROWS_PER_COLUMN);
            var currentX = 0;
            
            mutationColumns.forEach(function(column) {
                column.items.forEach(function(mutation, rowIndex) {
                    mutationsGroup.append("text")
                        .attr("x", currentX)
                        .attr("y", -(sorted.breeds.length + rowIndex + 1) * ymodsize)
                        .attr("font-size", ymodsize)
                        .attr("text-anchor", "start")
                        .attr("fill", "black")
                        .text(mutation);
                });
                currentX += column.width;
            });
        }

        // Handle breeds
        var breedsGroup = container.append("g")
            .attr("class", "breeds-group")
            .style("display", showBreeds ? "block" : "none");
            
        if (sorted.breeds.length > 0) {
            var breedColumns = organizeIntoColumns(sorted.breeds, MAX_ROWS_PER_COLUMN);
            var currentX = 0;
            
            breedColumns.forEach(function(column) {
                column.items.forEach(function(breed, rowIndex) {
                    breedsGroup.append("text")
                        .attr("x", currentX)
                        .attr("y", -(rowIndex + 1) * ymodsize)
                        .attr("font-size", ymodsize)
                        .attr("text-anchor", "start")
                        .attr("fill", "blue")
                        .text(breed.substring(6));
                });
                currentX += column.width;
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
        .style("display", function() {
            console.log('Updating mutations visibility:', showMutations); // Debug log
            return showMutations ? null : "none";
        });

    nodeUpdate.selectAll(".breeds-group")
        .style("display", function() {
            console.log('Updating breeds visibility:', showBreeds); // Debug log
            return showBreeds ? null : "none";
        });

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

    // Update mutations visibility
    svg.selectAll(".mutations-group")
        .style("display", showMutations ? "block" : "none");

    svg.selectAll(".breeds-group")
        .style("display", showBreeds ? "block" : "none");
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
