// global variables
var width = 500;
var height = 300;
var data = null;
var svg = null; 
var simulation = null;
var current_state = null;
var node = null;
var link = null;
var text = null;

// graph settings
var link_distance = 40;
var link_width = 5;
var link_color = "black";
var node_color = "lightblue";
var current_node_color = "green";
var node_outline_color = "black";
var node_radius = 20;


function showForceGraph(link_list){
    // if no graphs exist, then create svg element otherwise clear existing svg
    if (svg == null){
        svg = d3.select("#graph")
            .append("svg")
            .attr("width", width)
            .attr("height", height);
    }
    else {
        clearGraph();
    }

    // create node names from link list
    node_names = [];
    link_list.forEach(function(link) {
        if (node_names.indexOf(link.source) < 0){ node_names.push(link.source); }
        if (node_names.indexOf(link.target) < 0){ node_names.push(link.target); }
    });
    // get graph data from nodes and links
    data = getData(node_names, link_list);

	drawChart(data, svg);
}

function getData(node_names, link_dict){
    var nodes = [];
    for(i = 0; i<node_names.length; i++){
        nodes.push({label:node_names[i], r:10});
    }
    var links = [];
    var node_dict = {};
    for(i=0; i<nodes.length; i++){ node_dict[nodes[i].label] = nodes[i]; }
    for(i=0; i < link_dict.length; i++){
        links.push({
            'source':node_dict[link_dict[i].source], 
            'target':node_dict[link_dict[i].target]
        });
    }
	var graphData = {
        'nodes':nodes,
        'links':links
	}
    return graphData;
}
    
function drawChart(data, svg) {
    current_state = data.nodes[0].label;

	simulation = d3.forceSimulation()
		.force("link", d3.forceLink().id(function(d) { return d.label }))
		.force("collide",d3.forceCollide( function(d){return d.r + link_distance }).iterations(16) )
		.force("charge", d3.forceManyBody())
		.force("center", d3.forceCenter(width / 2, height / 2))
		.force("y", d3.forceY(0))
		.force("x", d3.forceX(0));

    svg.append("defs").append("marker")
        .attr("id", "arrowHead")
        .attr("viewBox", "0 -5 10 10")
        .attr("refX", 25)
        .attr("refY", 0)
        .attr("markerWidth", 3)
        .attr("markerHeight", 5)
        .attr("orient", "auto")
        .append("svg:path")
        .attr("d", "M0,-5L15,0L0,5")
        .attr("fill", link_color)
        .attr("stroke", link_color);

    link = svg.append("g")
		.attr("class", "links")
		.selectAll("line")
		.data(data.links)
		.enter()
		.append("line")
        .attr("marker-end", "url(#arrowHead)")
		.attr("stroke", link_color)
        .attr("stroke-width", link_width);

    node = svg.append("g")
		.attr("class", "nodes")
		.selectAll("circle")
		.data(data.nodes)
		.enter().append("circle")
		.attr("r", function(d){  return node_radius })
        .attr("stroke", node_outline_color)
        .attr("fill", node_color)
        .attr("id", function(d){ return d.label })
		.call(d3.drag()
				.on("start", dragstarted)
				.on("drag", dragged)
				.on("end", dragended));    

	simulation
		.nodes(data.nodes)
		.on("tick", ticked);

	simulation.force("link")
		.links(data.links);    

    text = svg.append("g").selectAll("text")
        .data(simulation.nodes())
        .enter().append("text")
        .attr("x", node_radius+5)
        .attr("y", node_radius+5)
        .text(function(d) { return d.label; });

	function dragstarted(d) {
		if (!d3.event.active) simulation.alphaTarget(0.3).restart();
		d.fx = d.x;
		d.fy = d.y;
	}

	function dragged(d) {
		d.fx = d3.event.x;
		d.fy = d3.event.y;
	}

	function dragended(d) {
		if (!d3.event.active) simulation.alphaTarget(0);
		d.fx = null;
		d.fy = null;
	} 

}

function ticked(){
    link
        .attr("x1", function(d) { return d.source.x; })
        .attr("y1", function(d) { return d.source.y; })
        .attr("x2", function(d) { return d.target.x; })
        .attr("y2", function(d) { return d.target.y; });

    node
        .attr("fill", function(d) { return d.label == current_state ? current_node_color : node_color })
        .attr("cx", function(d) { return d.x; })
        .attr("cy", function(d) { return d.y; });
    text
        .attr("transform", function(d) {return "translate(" + d.x + "," + d.y + ")"; });
}  

function updateCurrent(string){
    current_state = string;
    ticked();
}

function clearGraph(){
    // remove existing svg elements
    svg.selectAll("*").remove();   
}
