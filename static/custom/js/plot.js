function Plot(container_name, variable_selection_container_name, variable_selection_class_name, data_route, variable_selection_visible) {
    this.plot_container_name = container_name;
    this.variable_selection_container_name = variable_selection_container_name;
    this.variable_selection_class_name = variable_selection_class_name;
    this.data_route = data_route;
    this.variable_selection_visible = variable_selection_visible;
    this.data = [];
    this.data_labels = [];
    this.update_plot = false;
    this.current_variable = null;
}

Plot.prototype.get_data = function(robot_id, variable_list, start_time, end_time) {
    var parent_obj = this;

    $.ajax({
        url: SCRIPT_ROOT + parent_obj.data_route,
        type: 'get',
        data:
        {
            robot_id: robot_id,
            variables: variable_list.join(),
            start_timestamp: start_time,
            end_timestamp: end_time
        },
        contentType: 'application/json',
        cache: false,
        async: false
    }).done(function(result) {
        parent_obj.display_data(result.variables, result.data);
    }).fail(function(jqXHR, status, error) {
        console.log(error);
        $('#operation_indicator').hide();
    });
};

Plot.prototype.display_data = function(variables, data) {
    if (variables.length == 0) return;

    this.data_labels = variables;
    this.data = data;
    $('#operation_indicator').hide();

    if (!this.update_plot)
    {
        $('#' + this.plot_container_name).html('');
        this.add_variable_selection_checkboxes();
    }
    this.display_selected_data();
}

Plot.prototype.add_variable_selection_checkboxes = function() {
    var html_string = '<div class="form-group">';
    for (var i=0; i<this.data_labels.length; i++)
    {
        html_string += '<div class="checkbox"><label><input class="' + this.variable_selection_class_name + '" type="checkbox" value="' + i + '" checked="true" />' + this.data_labels[i] + '</label></div>';
    }
    html_string += "</div>";
    $('#' + this.variable_selection_container_name).html(html_string);
    if (!this.variable_selection_visible)
    {
        $('#' + this.variable_selection_container_name).hide();
    }
};

Plot.prototype.display_selected_data = function () {
    var checked = $('.' + this.variable_selection_class_name + ':checked');
    var flot_data = [];
    for (var i=0; i<checked.length; i++)
    {
        var id = parseInt($(checked[i]).val());
        flot_data.push({ label: this.data_labels[id], data: this.data[id] });
    }
    $.plot($('#' + this.plot_container_name), flot_data);
};

Plot.prototype.is_empty = function() {
    return $('#' + this.plot_container_name).html() == '';
};

Plot.prototype.reset = function() {
    this.data = [];
    this.data_labels = [];
    this.update_plot = false;
    this.current_variable = null;
    $('#' + this.plot_container_name).html('');
    $('#' + this.variable_selection_container_name).html('');
};


// plotly for occupancy grid plotting
function sendOccupancyGrid(msg, plot_function) {
    plot_function('occupancy_grid', [{}],
     {
      title: msg['name'],
      width: msg['width']*msg['display_scale'],
      height: msg['width']*msg['display_scale'],
      xaxis: {
       range: msg['xrange'],
       showgrid: false,
       zeroline: false,
       showticklabels: false
      },
      yaxis: {
       range: msg['yrange'],
       showgrid: false,
       zeroline: false,
       showticklabels: false
      },
      images: [
          {
            "source": msg['path'],
            "xref": "x",
            "yref": "y",
            "xanchor": "left",
            "yanchor": "top",
            "x": msg['origin_x'],
            "y": msg['origin_y'],
            "sizex": msg['width'],
            "sizey": msg['height'],
            "sizing": "stretch",
            "opacity": 0.2
          }
        ]
    });
}

function plotRobotPoses(msg, resolution) {
    len = msg.length;
    var shapes_dicts = [];
    for (var i = 0; i < len; i++)
    {
        var robot_pose = msg[i];
        var img_x = robot_pose.x / resolution;
        var img_y = robot_pose.y / resolution;
        var robotId = robot_pose.robotId;

        triangle_dict = {};
        var l1x = robot_pose.line1x / resolution;
        var l1y = robot_pose.line1y / resolution;
        var l2x = robot_pose.line2x / resolution;
        var l2y = robot_pose.line2y / resolution;
        triangle_dict['type'] = 'path';
        // svg: move to x,y line to x1,y1, line to x2,y2, stop
        triangle_dict['path'] = 'M ' + img_x + ' ' + img_y +
                                ' L ' + l1x + ' ' + l1y +
                                ' L ' + l2x + ' ' + l2y + ' Z'
        triangle_dict['fillcolor'] = 'rgba(50, 171, 96, 0.5)';
        triangle_dict['line'] = {};
        triangle_dict['line']['color'] = 'rgba(50, 171, 96, 1)';
        triangle_dict['line']['width'] = 1;
        shapes_dicts.push(triangle_dict);

    }
    Plotly.update('occupancy_grid', [{}],
    {
       shapes: shapes_dicts
    })
}
