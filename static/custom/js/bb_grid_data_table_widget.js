/**
 * A widget for displaying two-dimensional black box data in a table
 * (i.e. the widget displays a set of variables along with their values
 * along two dimensions).
 * @constructor
 * @param {string} container_id - ID of the container in which the widget should be displayed (without a leading #).
 * @param {string} data_table_header - Descriptive table header
 * @param {socket} socket - A socketio object.
 * @param {string} socket_event - Name of a socket data update event.
 */
function BBGridDataTableWidget(container_id, data_table_header, socket, socket_event) {
    this.container_id = container_id;
    this.data_table_header = data_table_header;
    this.variables = null;
    this.socket = socket;
    this.socket_event = socket_event;
    this.id_var_map = {};

    var parent_obj = this;
    this.socket.on(this.socket_event, function(msg) {
        var data_msg = JSON.parse(msg);
        parent_obj.update(data_msg['variables'], data_msg['data']);
    });
}

BBGridDataTableWidget.prototype.init = function() {
    var table_html = '<table class="table table-bordered"><th>' + this.data_table_header + '</th><tbody>';
    table_html += '<tr><td></td>';

    for (var key in this.variables[0])
    {
        table_html += '<td>' + this.variables[0][key] +  '</td>';
    }
    table_html += '</tr>';

    for (var i=0; i<this.variables.length; i++)
    {
        table_html += '<tr><td>' + (i+1).toString() + '</td>';
        this.id_var_map[i] = {};
        for (var key in this.variables[i])
        {
            var var_data_id = this.container_id + '_' + key.replace(/\//g, '_') + '_' + i.toString();
            this.id_var_map[i][this.variables[i][key]] = var_data_id;
            table_html += '<td id="' + var_data_id + '"></td>';
        }
        table_html += '</tr>';
    }
    table_html += '</tbody></table>';
    $('#' + this.container_id).html(table_html);
};

BBGridDataTableWidget.prototype.update = function(variables, timestamped_data) {
    if (variables.length == 0) return;

    if (this.variables == null)
    {
        this.variables = variables;
        this.init();
    }

    for (var i=0; i<variables.length; i++)
    {
        for (var key in variables[i])
        {
            // timestamped_data[0] is the timestamp of the data item
            if (timestamped_data[i][key] != null)
            {
                var var_data_id = this.id_var_map[i][variables[i][key]];
                $('#' + var_data_id).html(timestamped_data[i][key][1].toFixed(2));
            }
        }
    }
};

BBGridDataTableWidget.prototype.reset = function() {
    for (var i=0; i<variables.length; i++)
    {
        $('#' + variables[i]).html('');
    }
};
