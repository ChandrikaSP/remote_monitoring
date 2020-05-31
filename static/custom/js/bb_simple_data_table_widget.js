/**
 * A widget for displaying one-dimensional black box data in a table
 * (i.e. the widget displays a set of variables along with their values).
 * @constructor
 * @param {string} container_id - ID of the container in which the widget should be displayed (without a leading #).
 * @param {string} data_table_header - Descriptive table header
 * @param {socket} socket - A socketio object.
 * @param {string} socket_event - Name of a socket data update event.
 * @param {string} var_display_direction - String denoting the direction of variable display ('vertical' or 'horizontal') (default 'vertical')
 */
function BBSimpleDataTableWidget(container_id, data_table_header, socket, socket_event, var_display_direction='vertical') {
    this.container_id = container_id;
    this.data_table_header = data_table_header;
    this.variables = null;
    this.socket = socket;
    this.socket_event = socket_event;
    this.var_display_direction = var_display_direction;
    this.id_var_map = {};

    var parent_obj = this;
    this.socket.on(this.socket_event, function(msg) {
        var data_msg = JSON.parse(msg);
        parent_obj.update(data_msg['variables'], data_msg['data']);
    });
}

BBSimpleDataTableWidget.prototype.init = function() {
    var table_html = '<table class="table table-bordered"><th>' + this.data_table_header + '</th><tbody>';
    for (var i=0; i<this.variables.length; i++)
    {
        var var_data_id = this.container_id + '_' + i.toString();
        this.id_var_map[this.variables[i]] = var_data_id;
        table_html += '<tr><td>' + this.variables[i] +  '</td><td id="' + var_data_id + '"></td></tr>';
    }
    table_html += '</tbody></table>';
    $('#' + this.container_id).html(table_html);
};

BBSimpleDataTableWidget.prototype.update = function(variables, timestamped_data) {
    if (variables.length == 0) return;

    if (this.variables == null)
    {
        this.variables = variables;
        this.init();
    }

    for (var i=0; i<variables.length; i++)
    {
        // timestamped_data[0] is the timestamp of the data item
        var var_data_id = this.id_var_map[variables[i]];
        $('#' + var_data_id).html(timestamped_data[i][1].toFixed(2));
    }
};

BBSimpleDataTableWidget.prototype.reset = function() {
    for (var i=0; i<variables.length; i++)
    {
        $('#' + variables[i]).html('');
    }
};
