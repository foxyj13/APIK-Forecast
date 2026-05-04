import logging
import os

htmlfile_template = \
"""
<html>
<meta charset="UTF-8" />
<head>
    <script src='../plotly-2.35.2.min.js'></script>
</head>
<font face='arial'>
<center>
    <h1>
        $$title$$
    </h1>
    <hr size='1' width='80%' color='#3366cc'>
    <br>
</center>

<body>
    $$body$$
</body>
</html>
"""

body_template = \
"""
    <div id='$$plot_div_id$$' style='height:600px;'></div>
    <script src='$$js_filename$$'></script>
"""

jsfile_template = \
"""
$$vars_descripions$$

var data = [$$var_list$$];

var layout = {
    title: '$$parameter_name$$',
    showlegend: true,
    xaxis: {
        autorange: true,
        rangeselector: {buttons: [
            {
            count: 1,
            label: '1m',
            step: 'month',
            stepmode: 'backward'
            },
            {
            count: 7,
            label: '7d',
            step: 'day',
            stepmode: 'backward'
            },
            {
                count: 1,
                label: '1d',
                step: 'day',
                stepmode: 'backward'
            },
            {step: 'all'}
        ]},
        rangeslider : {range: ['$$min_date$$', '$$max_date$$']},
        type: 'date'
    },
    yaxis: {
        autorange: true,
        type: 'linear'
    }
};

Plotly.newPlot($$plot_div_id$$, data, layout);
"""

var_template = \
"""
var $$js_var_name$$ = {
    x: [$$x$$],
    y: [$$y$$],
    name: '$$station_full_name$$',
    type: 'line'
};
"""

class PlotterJS:
    def __init__(self, config: dict, stations, time_depth):
        self._config = config
        self._stations = stations
        self._time_depth = time_depth

    def make_plots(self, variables: list[str]):
        html_filename = self._config['html-plot-basename']+f"_{self._config['name']}"+".html"
        html_filename = os.path.join(self._config['web-folder'], html_filename)
        with open(html_filename, "w", encoding="utf8") as htmlfile:
            bodies = []
            for variable in variables:
                js_filename, plot_div_id = self._make_plot(variable)
                if not js_filename:
                    continue
                js_filename = os.path.basename(js_filename)
                body = body_template.replace("$$plot_div_id$$", plot_div_id)
                body = body.replace("$$js_filename$$", js_filename)
                bodies.append(body)
            htmlfile_text = htmlfile_template.replace("$$title$$", self._config['html-plot-title'])
            htmlfile_text = htmlfile_text.replace("$$body$$", "".join(bodies))
            htmlfile.write(htmlfile_text)

    def _make_plot(self, variable: str) -> tuple[str, str]:
        js_var_names = []
        js_filename = self._config['js-plot-basename']+f"_{variable}"+f"_{self._config['name']}"+".js"
        js_filename = os.path.join(self._config['web-folder'], js_filename)
        plot_div_id = "plot_"+variable
        parameter_name = ""
        with open(js_filename, "w", encoding="utf8") as plotfile:
            vars_descs_list = []
            for idx, station in enumerate(self._stations):
                # Loop by stations.
                if variable in station['parameters']:
                    parameter = station['parameters'][variable]
                    x_data = station['time'][self._time_depth]
                    y_data = parameter['data'][self._time_depth]
                    valid_y_data = [val for val in y_data if val]
                    if not x_data or not valid_y_data:
                        logging.warning("Внимание! Нет значений. Пропускаю станцию %s.", station['full_name'])
                        continue
                    min_date, max_date = min(x_data), max(x_data)
                    parameter_name = parameter["short_name"]
                    js_var_name = f"station{idx}"
                    js_var_names.append(js_var_name)
                    x = [f"'{val}'" for val in x_data]
                    y = [f"'{val}'" if val else "''" for val in y_data]
                    # Add station data variable.
                    var_description = var_template
                    var_description = var_description.replace("$$js_var_name$$", js_var_name)
                    var_description = var_description.replace("$$x$$", ",".join(x))
                    var_description = var_description.replace("$$y$$", ",".join(y))
                    var_description = var_description.replace("$$station_full_name$$", station['full_name'])
                    vars_descs_list.append(var_description)
                else:
                    logging.info("Переменной %s нет у станции %s", variable, station['full_name'])
            if not parameter_name:
                logging.error("Переменная %s не найдена ни в одной станции! График не будет построен!", variable)
                return "", ""
            # Write JS file.
            jsfile_text = jsfile_template
            jsfile_text = jsfile_text.replace("$$vars_descripions$$", ''.join(vars_descs_list))
            jsfile_text = jsfile_text.replace("$$var_list$$", ','.join(js_var_names))
            jsfile_text = jsfile_text.replace("$$parameter_name$$", parameter_name)
            jsfile_text = jsfile_text.replace("$$plot_div_id$$", plot_div_id)
            jsfile_text = jsfile_text.replace("$$min_date$$", str(min_date))
            jsfile_text = jsfile_text.replace("$$max_date$$", str(max_date))
            plotfile.write(jsfile_text)
        return js_filename, plot_div_id
