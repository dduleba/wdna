function init_root(root, width){
  root.x0 = 0;
  root.y0 = 0;
  hide(root, 'KIM');
  update(root);
  window.scrollTo(width*5/6-window.innerWidth/2,0);
}

// ************** Generate the tree diagram  *****************
var margin = {top: 20, right: 0, bottom: 20, left: 20},
 width = 7000 - margin.right - margin.left,
 height = 1900 - margin.top - margin.bottom,
 ydep = 150,
 ymodsize = 8;
var i = 0,
    duration = 750;
var tree = d3.layout.tree()
    .nodeSize([75,50])
var diagonal = d3.svg.diagonal()
 .projection(function(d) { return [d.x, d.y]; });
var svg = d3.select("body").append("svg")
 .attr("width", width + margin.right + margin.left)
 .attr("height", height + margin.top + margin.bottom)
  .append("g")
 .attr("transform", "translate(" + width*5/6 + "," + margin.top + ")");

d3.json("data/tree.json", function(error, json_tree) {
  if (error){
    console.log(error);
  }
  root=json_tree[0]
  init_root(json_tree[0], width); 
});

function update(source) {
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
          for (var i=Math.floor((2*d.mods.length)/3); i<d.mods.length; i++){
            d3.select(this)
              .append("tspan")
              .attr("dy", ymodsize)
              .attr("x", 70)
              .attr("font-size", ymodsize)
              .attr("text-anchor", "start")
              .text(d.mods[i])
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
            d3.select(this)
              .append("tspan")
              .attr("dy", ymodsize)
              .attr("x", 35)
              .attr("font-size", ymodsize)
              //.attr("text-anchor", "middle")
              .attr("text-anchor", "start")
              .text(d.mods[i])
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
            if ( d.mods.length * ymodsize > 2*ydep){
              max_element = Math.floor((d.mods.length)/3);
            }else{
              max_element = Math.floor(d.mods.length/2);
            }
          }else{
            max_element = d.mods.length
          }
          for (var i=0; i<max_element; i++){
            d3.select(this)
              .append("tspan")
              .attr("dy", ymodsize)
              .attr("x", 0)
              .attr("font-size", ymodsize)
              //.attr("text-anchor", "middle")
              .attr("text-anchor", "start")
              .text(d.mods[i])
          }
        }
      })
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
      //if(!d.children){
      //}
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
