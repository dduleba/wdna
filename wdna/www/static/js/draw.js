function toggle() {
	var ele = document.getElementById("toggleText");
	var text = document.getElementById("displayText");
	if(ele.style.display == "block") {
    		ele.style.display = "none";
		text.innerHTML = "show legend";
  	}
	else {
		ele.style.display = "block";
		text.innerHTML = "hide legend";
	}
} 


function init_root(root, width){
  root.x0 = 0;
  root.y0 = 0;
  expandAll(root);
  update(root);
  
  // Scroll the tree container instead of the window
  var treeContainer = document.getElementById("tree-container");
  var scrollPosition = width*5/6 - window.innerWidth/2;
  if (treeContainer) {
    // Delay the scroll operation to ensure the SVG is fully rendered
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
    .nodeSize([75,50])
var diagonal = d3.svg.diagonal()
 .projection(function(d) { return [d.x, d.y]; });
var svg = d3.select("#tree-container").append("svg")
 .attr("width", width + margin.right + margin.left)
 .attr("height", height + margin.top + margin.bottom)
  .append("g")
 .attr("transform", "translate(" + width*5/6 + "," + margin.top + ")");

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
    
    // Mark nodes for removal if they have no breeds
    if (!node.children && !node._children && node.breeds.length === 0) {
      node.remove = true;
    }
    
    // For internal nodes, check if they have any valid children or breeds
    function hasValidChildren(n) {
      if (!n) return false;
      if (n.children) {
        return n.children.some(function(child) { return !child.remove; });
      }
      if (n._children) {
        return n._children.some(function(child) { return !child.remove; });
      }
      return false;
    }
    
    if (!node.breeds.length && !hasValidChildren(node)) {
      node.remove = true;
    }
  }
}

function update(source) {
  // Filter out removed nodes before computing layout
  function filterRemovedNodes(node) {
    if (!node) return null;
    
    // Filter children arrays if they exist
    if (node.children) {
      node.children = node.children.filter(function(child) { return !child.remove; });
      node.children.forEach(filterRemovedNodes);
    }
    if (node._children) {
      node._children = node._children.filter(function(child) { return !child.remove; });
      node._children.forEach(filterRemovedNodes);
    }
    
    return node;
  }
  
  // Apply filter before computing layout
  filterRemovedNodes(root);
  
  // Compute the new tree layout.
  var nodes = tree.nodes(root).reverse(),
      links = tree.links(nodes);
  // Normalize for fixed-depth.
  nodes.forEach(function(d) { 
    d.y = d.depth * ydep;
  });
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
      .style("stroke",function(d) { return d.children ? "green":"red"})
  nodeEnter.append("text")
      .attr("dy", ".35em")
      .attr("x", -7)
      .attr("text-anchor", "end" )
      .text(function(d) { return d.name; })
      .style("fill-opacity", 1e-6);
  text3 = nodeEnter.append("text")
      .attr('y',function(d){
        return d.mods && d.mods.length*ymodsize > 2*ydep? -ymodsize-Math.floor(ymodsize*d.mods.length)/3:0 
      })
      .each(function(d){
        if (d.mods && d.mods.length * ymodsize > 2*ydep){
          start_i = Math.floor((2*d.mods.length)/3);
          for (var i=start_i; i<d.mods.length; i++){
            var mod = d.mods[i];
            var isBreed = typeof mod === 'string' && mod.startsWith("BREED:");
            
            var displayText = mod;
            if (isBreed) {
              var breedName = mod.substring(6);
              displayText = breedName;
            }
            
            d3.select(this)
              .append("tspan")
              .attr("dy", ymodsize)
              .attr("x", 70)
              .attr("font-size", ymodsize)
              .attr("text-anchor", "start")
              .attr("fill", isBreed ? "blue" : "black")
              .text(displayText);
          }
        }
      })
  
  text2 = nodeEnter.append("text")
      .attr('y',function(d){
        if (d.mods && d.mods.length * ymodsize > ydep){
          if (d.mods && d.mods.length * ymodsize > 2*ydep){
            return -ymodsize-Math.floor(ymodsize*d.mods.length)/3;
          }else{
            return -ymodsize-Math.floor(ymodsize*d.mods.length)/2;
          }
        }else{
          return 0
        }
      })
      .each(function(d){
        if (d.mods && d.mods.length * ymodsize > ydep){
          if (d.mods && d.mods.length * ymodsize > 2*ydep){
            start_i = Math.floor(d.mods.length/3);
            end_i = Math.floor((2*d.mods.length)/3);
          }else{
            start_i = Math.floor(d.mods.length/2);
            end_i = d.mods.length;
          }
          for (var i=start_i; i<end_i; i++){
            var mod = d.mods[i];
            var isBreed = typeof mod === 'string' && mod.startsWith("BREED:");
            
            var displayText = mod;
            if (isBreed) {
              var breedName = mod.substring(6);
              displayText = breedName;
            }
            
            d3.select(this)
              .append("tspan")
              .attr("dy", ymodsize)
              .attr("x", 35)
              .attr("font-size", ymodsize)
              .attr("text-anchor", "start")
              .attr("fill", isBreed ? "blue" : "black")
              .text(displayText);
          }
        }
      })
  text = nodeEnter.append("text")
      .attr("y", function(d){ 
        if (d.mods){
          if(d.mods.length * ymodsize > ydep){
            if (d.mods && d.mods.length * ymodsize > 2*ydep){
              return -ymodsize-Math.floor(ymodsize*d.mods.length)/3;
            }else{
              return -ymodsize-Math.floor(ymodsize*d.mods.length)/2;
            }
          }else{
            return -(d.mods.length+1)*ymodsize;
          }
        }else{
          return 0
        }
      })
      .each(function(d){
        if (d.mods){
          if(d.mods.length * ymodsize > ydep){
            if (d.mods.length * ymodsize > 2*ydep){
              max_element = Math.floor(d.mods.length/3);
            }else{
              max_element = Math.floor(d.mods.length/2);
            }
          }else{
            max_element = d.mods.length;
          }
          for (var i=0; i<max_element; i++){
            var mod = d.mods[i];
            var isBreed = typeof mod === 'string' && mod.startsWith("BREED:");
            
            var displayText = mod;
            if (isBreed) {
              var breedName = mod.substring(6);
              displayText = breedName;
            }
            
            d3.select(this)
              .append("tspan")
              .attr("dy", ymodsize)
              .attr("x", 0)
              .attr("font-size", ymodsize)
              .attr("text-anchor", "start")
              .attr("fill", isBreed ? "blue" : "black")
              .text(displayText);
          }
        }
      })
      
  // Add breeds display in a simpler way - just one column with limit
  nodeEnter.append("text")
      .attr("class", "breeds-text")
      .attr("y", 0)
      .attr("x", 0)
      .style("fill-opacity", 0);  // Hide this element

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
      .style("stroke",function(d) { return d.children || d._children  ? "green":"red"});
  nodeUpdate.select("text")
      .style("fill-opacity", 1);
  // Make sure breeds text transitions properly
  nodeUpdate.select(".breeds-text")
      .style("fill-opacity", 1);
  // Transition exiting nodes to the parent's new position.
  var nodeExit = node.exit().transition()
      .duration(duration)
      .attr("transform", function(d) { return "translate(" + source.x + "," + source.y + ")"; })
      .remove();
  nodeExit.select("circle")
      .attr("r", 1e-6);
  nodeExit.select("text")
      .style("fill-opacity", 1e-6);
  nodeExit.select(".breeds-text")
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
