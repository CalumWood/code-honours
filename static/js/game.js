var players = []

// create an array with nodes
var nodes = new vis.DataSet([]);
// create an array with edges
var edges = new vis.DataSet([]);

// create a network
var container = document.getElementById("mynetwork");

var data = {
    nodes: nodes,
    edges: edges,
};

var options = {
    interaction:{
    dragNodes:true,
    dragView: true,
    hideEdgesOnDrag: false,
    hideEdgesOnZoom: false,
    hideNodesOnDrag: false,
    hover: false,
    hoverConnectedEdges: true,
    keyboard: {
        enabled: false,
        speed: {x: 10, y: 10, zoom: 0.02},
        bindToWindow: true,
        autoFocus: true,
    },
    multiselect: false,
    navigationButtons: false,
    selectable: true,
    selectConnectedEdges: true,
    tooltipDelay: 300,
    zoomSpeed: 1,
    zoomView: true
    }
}

function context(data = {}) {
    return {'data': data, 'lobby': lobby}
}

var network = new vis.Network(container, data, options);
highlighted = []
network.on("click", function (params) {
    params.event = "[original event]";
    selection = params.nodes.filter(value => highlighted.includes(value));
    console.log(selection)
    network.setSelection({'nodes': selection, 'edges':null}, {highlightEdges: false})
    document.getElementById("eventSpanHeading").innerText = "Click event:";
    document.getElementById("eventSpanContent").innerText = params.nodes

    console.log("click event, getNodeAt returns: " +
                this.getNodeAt(params.pointer.DOM)
    );
})

var socket = io();
socket.on('connect', function() {
    console.log("connected")
    console.log(context())
    socket.emit('join', context());
});

socket.on('players', function(arg) {
    console.log("players updated")
    $("#Players").html("Players: " + arg.join(', '))
});

socket.on('update_map', function(arg) {
    console.log(arg)
    edges.update(arg.connections)
    update_nodes(arg.nodes)
    network.body.emitter.emit('_dataChanged')
    network.redraw()
    console.log("map updated")
});

// phase_depth = 1
// socket.on('highlight_choices', function(arg) {
//     console.log(arg)
//     options = []

//     highlight(arg.data)
//     $("#Phase").html("Phase: " + arg.phase)

//     console.log("Choices Highlighted")
// });

function highlight(arr) {
    highlighted = arr
    obj = []
    if (arr && !Array.isArray(arr[0])){
        for (const node of arr) {
            obj.push({'id': node, 'group': -1})
        }
    }
    update_nodes(obj)
}

request_choice = {}

socket.on('get_choices', function(arg) {
    // arg = {phase, data = [[], []], number}
    console.log("new options")
    console.log(arg)
    options = []
    request_choice = arg

    $("#Phase").html("Phase: " + arg.phase)
    highlight(arg.data[0])
});

depth = 0
number = 0
selected = []
stored = []


function get_choice() {
    node = network.getSelectedNodes()[0]
    if (node == null){return}
    if (node in stored){return}

    stored.push(node)

    if (depth+1<request_choice.data.length) {
        depth++
        highlight(request_choice.data[depth])
    } else {
        const found = selected.some(r=> JSON.stringify(r) === JSON.stringify(stored))
        depth = 0
        highlight(request_choice.data[depth])
        stored = []
        if (found){return}
        selected.push(stored)
        // number++
    }
    if (number >= request_choice.number) {
        send_selected()
    }
    console.log(selected)
}

function clear_selected(){
    depth = 0
    number = 0
    stored = []
}

function send_selected(){
    console.log(selected)
    socket.emit('select', context(selected));
    clear_selected()
    console.log("choices sent")
}

socket.on('update_lobby', function(arg) {
    console.log("update_lobby")
    socket.emit('update_map', lobby);
    $("#Turn").html("Turn: " + arg['turn'])
});

function update_nodes(new_nodes) {
    // console.log(new_nodes)
    nodes.update(new_nodes)
    network.body.emitter.emit('_dataChanged')
    network.redraw()
}

// function select() {
//     socket.emit('select', context(network.getSelectedNodes()));
// }

// function get_requests() {
//     socket.emit('select', network.getSelectedNodes());
// }
