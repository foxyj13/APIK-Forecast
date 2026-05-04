import datetime
import logging

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import os
import csv


class Plotter:
    def __init__(self, config: dict):
        self._config = config
        self.export_enabled = config.get('export-enable', 'false').lower() == 'true'
        #self.export_folder = config.get('csv-folder')

    def export_to_csv(self, station: dict, time_depth: str):

        if not self.export_enabled:
            return
        
        if not time_depth == 'c_yr':
            return
            
        year = datetime.datetime.now().year
        logging.info("Экспортирую данные в csv для станции %s (%s) за %s год", station['code'], station['full_name'], year)

        filename = f"{station['code']}_{year}.csv"
        filename = os.path.join(self._config['csv-folder'], filename)
        
        try:
            with open(filename, 'w', newline='', encoding='utf-8-sig') as csvfile:
                writer = csv.writer(csvfile, delimiter=';')
                
                # Заголовки столбцов
                headers = ['time']
                param_names = []
                for param_name, parameter in station['parameters'].items():
                    headers.append(parameter['name'])
                    param_names.append(param_name)
                
                writer.writerow(headers)
                
                # Данные
                for i, timestamp in enumerate(station['time']['c_yr']):
                    row = [timestamp.strftime('%Y-%m-%d %H:%M')]
                    
                    for param_name in param_names:
                        value = station['parameters'][param_name]['data']['c_yr'][i]
                        row.append(str(value) if value is not None else '')
                    
                    writer.writerow(row)
            
            logging.info(f"Данные экспортированы в {filename}")
        except Exception as e:
            logging.error(f"Ошибка при экспорте данных: {e}")


    def make_table(self, station: dict):
        logging.info(f"Строю табличку текущих наблюдений для станции {station['code']}")
        title_text = station['full_name']
        fig_border = 'steelblue'
        out_filename = f"{station['code']}_{self._config['recent-table-suffix']}.png"
        out_filename = os.path.join(self._config['images-folder'], out_filename)

        timestamp = station['time']['recent'].strftime('%d.%m.%Y %H:%M')
        data = []  # Data to plot as a table
        for name, parameter in station['parameters'].items():
            value = f"{float(parameter['data']['recent']):1.1f}" if parameter['data']['recent'] is not None else '-'
            data.append([parameter['full_name'], value])
        # Get row headers from the data array
        row_headers = [x[0] for x in data]
        # Format the data
        cell_text = []
        for row in data:
            cell_text.append([x for x in row[1:]])
        # Get some lists of color specs for row and column headers
        # Create the figure.
        plt.figure(linewidth=2,
                   edgecolor=fig_border,
                   tight_layout={'pad': 0.3},
                   figsize=(len(data[0])+3.5, max([(len(data)+1)*0.35, 1.1]))  # Complex formula to get figure size
                   )
        # Add a table at the bottom of the axes
        the_table = plt.table(cellText=cell_text,
                              rowLabels=row_headers,
                              rowLoc='left',
                              loc='lower center')
        # Make the rows taller (i.e., make cell y scale larger).
        the_table.scale(1, 1.5)
        # Hide axes
        ax = plt.gca()
        ax.get_xaxis().set_visible(False)
        ax.get_yaxis().set_visible(False)
        # Hide axes border
        plt.box(on=None)
        # Add title
        plt.suptitle('$\\bf{' + title_text.replace(' ', '\ ') + '}$\n' + timestamp, va='top')
        # Add footer
        # Without plt.draw() here, the title will center on the axes and not the figure.
        plt.draw()
        # Create image. plt.savefig ignores figure edge and face colors, so map them.
        fig = plt.gcf()
        plt.savefig(out_filename,
                    edgecolor=fig.get_edgecolor(),
                    facecolor=fig.get_facecolor(),
                    dpi=150)
        plt.close(fig)

    def _make_plot(self, station: dict, time_scale: str):
        footer_text = station['time']['recent'].strftime('%d.%m.%Y %H:%M')

        for _, parameter in station['parameters'].items():
            plt.figure(figsize=(6.4, 4.8-0.8))
            x = station['time'][time_scale]
            y = parameter['data'][time_scale]
            plt.plot(x, y)
            ax = plt.gca()
            ax.set_ylabel(parameter['full_name'], size=13)
            ax.tick_params('both', labelsize=12)
            plt.title(station['full_name'], size=14)
#            if time_scale == 'c_yr':
#                ax.xaxis.set_major_locator(mdates.MonthLocator())
#                ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
#                ax.xaxis.set_minor_locator(mdates.DayLocator())
#                ax.yaxis.set_tick_params(which='minor', left=False)
#            if time_scale == '365d':
#                ax.xaxis.set_major_locator(mdates.MonthLocator())
#                ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
#                ax.xaxis.set_minor_locator(mdates.DayLocator())
#                ax.yaxis.set_tick_params(which='minor', left=False)                
            if time_scale == '30d':
                ax.xaxis.set_major_locator(mdates.DayLocator(interval=7))
                ax.xaxis.set_minor_locator(mdates.DayLocator())
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%b-%d'))
            if time_scale == '7d':
                ax.xaxis.set_major_locator(mdates.HourLocator(interval=24))
                ax.xaxis.set_minor_locator(mdates.HourLocator(interval=6))
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%b-%d'))
            if time_scale == '1d':
                ax.xaxis.set_major_locator(mdates.HourLocator(interval=4))
                ax.xaxis.set_minor_locator(mdates.HourLocator())
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
            ax.grid(True)
            ax.grid(which='minor', linestyle=':')
            plt.xlim(mdates.date2num(station['time_range'][time_scale]))

            plt.figtext(0.95, 0.025, footer_text, horizontalalignment='right', size=10, weight='light')
            out_filename = f"{station['code']}_{parameter['code']}_{self._config[f'{time_scale}-plot-suffix']}.png"
            out_filename = os.path.join(self._config['images-folder'], out_filename)
            fig = plt.gcf()
            plt.savefig(out_filename,
                        edgecolor=fig.get_edgecolor(),
                        facecolor=fig.get_facecolor(),
                        dpi=150)
            plt.close(fig)

    def make_plots(self, station: dict, time_depth: str):
        time_limit = {'c_yr': {'value': 5},
                      '365d': {'value': 4},
				   	  '30d': {'value': 3},
                      '7d': {'value': 2},
                      '1d': {'value': 1}}
#        if time_limit[time_depth]['value'] == 5:
#            logging.info(f"Строю текущие годовые графики для станции {station['code']}")
#            self._make_plot(station, 'c_yr')
            
        if time_limit[time_depth]['value'] == 4:
            logging.info(f"Строю годовые графики для станции {station['code']}")
            self._make_plot(station, '365d')
			
        if time_limit[time_depth]['value'] == 3:
            logging.info(f"Строю 30-дневные графики для станции {station['code']}")
            self._make_plot(station, '30d')

        if time_limit[time_depth]['value'] == 2:
            logging.info(f"Строю 7-дневные графики для станции {station['code']}")
            self._make_plot(station, '7d')
			
        if time_limit[time_depth]['value'] == 1:
            logging.info(f"Строю 1-дневные графики для станции {station['code']}")
            self._make_plot(station, '1d')
