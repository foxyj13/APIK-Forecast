import datetime
import logging
import math

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import os
import csv


class Plotter:
    def __init__(self, config: dict, glob_forecast=False, local_forecast=False):
        self._config = config
        self.export_enabled = config.get("export-enable", "false").lower() == "true"
        # self.export_enabled = config.getboolean("export-enable")
        # self.export_folder = config.get('csv-folder')

        self.glob_forecast = glob_forecast
        self.local_forecast = local_forecast

        self.img_bw = config.get("images-bw", "false").lower() == "true"
        if self.img_bw:
            self.obs_plot_kwargs = {
                "scalex": True,
                "scaley": True,
                "marker": "o",
                "markersize": 4,
                "markevery": 4,
                "color": "black",
                "markeredgecolor": "black",
                "markerfacecolor": "white",
                # "linewidth": 5,
                "label": "Наблюдения",
            }
            self.loc_past_plot_kwargs = {
                "scalex": True,
                "scaley": True,
                "color": "gray",
                "label": "Локальный прогноз",
            }
            self.loc_future_plot_kwargs = {
                "scalex": True,
                "scaley": True,
                "linestyle": "--",
                "color": "gray",
            }
            self.glob_past_plot_kwargs = {
                "scalex": True,
                "scaley": True,
                "color": "black",
                "linewidth": 1,
                "label": "Глобальный прогноз",
            }
            self.glob_future_plot_kwargs = {
                "scalex": True,
                "scaley": True,
                "linestyle": "--",
                "color": "black",
                "linewidth": 1,
            }
        else:
            self.obs_plot_kwargs = {
                "scalex": True,
                "scaley": True,
                "marker": "o",
                "markersize": 4,
                "markevery": 4,
                "color": "blue",
                "markeredgecolor": "blue",
                "markerfacecolor": "white",
                "label": "Наблюдения",
            }
            self.loc_past_plot_kwargs = {
                "scalex": True,
                "scaley": True,
                "color": "forestgreen",
                "label": "Локальный прогноз",
            }
            self.loc_future_plot_kwargs = {
                "scalex": True,
                "scaley": True,
                "linestyle": "--",
                "color": "forestgreen",
            }
            self.glob_past_plot_kwargs = {
                "scalex": True,
                "scaley": True,
                "color": "darkred",
                "label": "Глобальный прогноз",
            }
            self.glob_future_plot_kwargs = {
                "scalex": True,
                "scaley": True,
                "linestyle": "--",
                "color": "darkred",
            }

    def export_to_csv(self, station: dict, time_depth: str):

        if not self.export_enabled:
            return

        if not time_depth == "c_yr":
            return

        year = datetime.datetime.now().year
        logging.info(
            "Экспортирую данные в csv для станции %s (%s) за %s год",
            station["code"],
            station["full_name"],
            year,
        )

        filename = f"{station['code']}_{year}.csv"
        filename = os.path.join(self._config["csv-folder"], filename)

        try:
            with open(filename, "w", newline="", encoding="utf-8-sig") as csvfile:
                writer = csv.writer(csvfile, delimiter=";")

                # Заголовки столбцов
                headers = ["time"]
                param_names = []
                for param_name, parameter in station["parameters"].items():
                    headers.append(parameter["name"])
                    param_names.append(param_name)

                writer.writerow(headers)

                # Данные
                for i, timestamp in enumerate(station["db_time_past"]["c_yr"]):
                    row = [timestamp.strftime("%Y-%m-%d %H:%M")]

                    for param_name in param_names:
                        value = station["parameters"][param_name]["data"]["c_yr"][i]
                        row.append(str(value) if value is not None else "")

                    writer.writerow(row)

            logging.info(f"Данные экспортированы в {filename}")
        except Exception as e:
            logging.error(f"Ошибка при экспорте данных: {e}")

    def make_table(self, station: dict):
        logging.info(f"Строю табличку текущих наблюдений для станции {station['code']}")

        plt.ioff()

        title_text = station["full_name"]
        fig_border = "steelblue"
        out_filename = f"{station['code']}_{self._config['recent-table-suffix']}.png"
        out_filename = os.path.join(self._config["images-folder"], out_filename)

        timestamp = station["db_time_past"]["recent"].strftime("%d.%m.%Y %H:%M")
        data = []  # Data to plot as a table
        for name, parameter in station["parameters"].items():
            value = (
                f"{float(parameter['data']['recent']):1.1f}"
                if parameter["data"]["recent"] is not None
                else "-"
            )
            data.append([parameter["full_name"], value])
        # Get row headers from the data array
        row_headers = [x[0] for x in data]
        # Format the data
        cell_text = []
        for row in data:
            cell_text.append([x for x in row[1:]])
        # Get some lists of color specs for row and column headers
        # Create the figure.
        plt.figure(
            linewidth=2,
            edgecolor=fig_border,
            tight_layout={"pad": 0.3},
            figsize=(
                len(data[0]) + 3.5,
                max([(len(data) + 1) * 0.35, 1.1]),
            ),  # Complex formula to get figure size
        )
        # Add a table at the bottom of the axes
        the_table = plt.table(
            cellText=cell_text, rowLabels=row_headers, rowLoc="left", loc="lower center"
        )
        # Make the rows taller (i.e., make cell y scale larger).
        the_table.scale(1, 1.5)
        # Hide axes
        ax = plt.gca()
        ax.get_xaxis().set_visible(False)
        ax.get_yaxis().set_visible(False)
        # Hide axes border
        plt.box(on=None)
        # Add title
        plt.suptitle(
            "$\\bf{" + title_text.replace(" ", "\ ") + "}$\n" + timestamp, va="top"
        )
        # Add footer
        # Without plt.draw() here, the title will center on the axes and not the figure.
        plt.draw()
        # Create image. plt.savefig ignores figure edge and face colors, so map them.
        fig = plt.gcf()
        plt.savefig(
            out_filename,
            edgecolor=fig.get_edgecolor(),
            facecolor=fig.get_facecolor(),
            dpi=150,
        )
        plt.close(fig)

        plt.ion()

    @staticmethod
    def _get_recent_idx(parameters: dict, time_depth: str) -> int:
        def get_recent_value_idx(data: list) -> int:
            return next(
                (
                    i
                    for i, x in reversed(list(enumerate(data)))
                    if isinstance(x, (int, float))
                    and not (isinstance(x, float) and math.isnan(x))
                ),
                -1,
            )

        last_val_idxs = [
            get_recent_value_idx(par_info["data"][time_depth])
            for _, par_info in parameters.items()
        ]

        return max(last_val_idxs)

    def make_table_forecast(self, station: dict, time_depth: str):

        logging.info(
            "Строю табличку текущих наблюдений для станции %s", station["code"]
        )
        if self.local_forecast:
            logging.info("Добавляю значения локального (уточненного) прогноза")

        glob_forecast = self.glob_forecast
        if glob_forecast:
            if "om_time_prepast" in station:
                glob_forecast = False
                logging.info(
                    "Добавление глобального (сырого) прогноза невозможно, т.к. проводился расчет стат. прогноза"
                )
            else:
                logging.info("Добавляю значения глобального (сырого) прогноза")

        plt.ioff()

        title_text = station["full_name"]
        fig_border = "steelblue"
        out_filename = f"{station['code']}_{self._config['recent-table-suffix']}.png"
        out_filename = os.path.join(self._config["images-folder"], out_filename)

        recent_idx = self._get_recent_idx(station["parameters"], time_depth)

        timestamp = station["db_time_past"][time_depth][recent_idx].strftime(
            "%d.%m.%Y %H:%M"
        )

        data = []  # Data to plot as a table
        column_headers = ["Наблюдения"]
        for name, parameter in station["parameters"].items():
            row_val = [parameter["full_name"]]

            value_obs = (
                f"{float(parameter['data'][time_depth][recent_idx]):1.1f}"
                if (recent_idx >= 0)
                and (parameter["data"][time_depth][recent_idx] is not None)
                and not (
                    isinstance(parameter["data"][time_depth][recent_idx], float)
                    and math.isnan(parameter["data"][time_depth][recent_idx])
                )
                else "-"
            )
            row_val.append(value_obs)

            if self.local_forecast:
                value_fc_local = (
                    f"{float(parameter['om_data_local']['past'][time_depth][recent_idx]):1.1f}"
                    if (recent_idx >= 0)
                    and ("om_data_local" in parameter)
                    and (
                        parameter["om_data_local"]["past"][time_depth][recent_idx]
                        is not None
                    )
                    and not (
                        isinstance(
                            parameter["om_data_local"]["past"][time_depth][recent_idx],
                            float,
                        )
                        and math.isnan(
                            parameter["om_data_local"]["past"][time_depth][recent_idx]
                        )
                    )
                    else "-"
                )
                row_val.append(value_fc_local)
                column_headers.append("Лок. прогноз")

            if glob_forecast:
                value_fc_glob = (
                    f"{float(station['om_parameters'][parameter['om_parameter']]['past'][time_depth][recent_idx]):1.1f}"
                    if (recent_idx >= 0)
                    and ("om_parameter" in parameter)
                    and (parameter["om_parameter"] in station["om_parameters"])
                    and (
                        station["om_parameters"][parameter["om_parameter"]]["past"][
                            time_depth
                        ][recent_idx]
                        is not None
                    )
                    and not (
                        isinstance(
                            station["om_parameters"][parameter["om_parameter"]]["past"][
                                time_depth
                            ][recent_idx],
                            float,
                        )
                        and math.isnan(
                            station["om_parameters"][parameter["om_parameter"]]["past"][
                                time_depth
                            ][recent_idx]
                        )
                    )
                    else "-"
                )
                row_val.append(value_fc_glob)
                column_headers.append("Глоб. прогноз")

            data.append(row_val)

        # Get row headers from the data array
        row_headers = [x[0] for x in data]

        # Format the data
        cell_text = []
        for row in data:
            cell_text.append([x for x in row[1:]])
        # Get some lists of color specs for row and column headers
        # Create the figure.
        plt.figure(
            linewidth=2,
            edgecolor=fig_border,
            tight_layout={"pad": 0.3},
            figsize=(
                len(data[0]) + 3.5,
                max([(len(data) + 1) * 0.35, 1.1]),
            ),  # Complex formula to get figure size
        )
        # Add a table at the bottom of the axes
        the_table = plt.table(
            cellText=cell_text,
            rowLabels=row_headers,
            rowLoc="left",
            colLabels=column_headers,
            colLoc="center",
            loc="lower center",
        )
        # Make the rows taller (i.e., make cell y scale larger).
        the_table.scale(1, 1.5)
        # Hide axes
        ax = plt.gca()
        ax.get_xaxis().set_visible(False)
        ax.get_yaxis().set_visible(False)
        # Hide axes border
        plt.box(on=None)
        # Add title
        plt.suptitle(
            "$\\bf{" + title_text.replace(" ", "\ ") + "}$\n" + timestamp, va="top"
        )
        # Add footer
        # Without plt.draw() here, the title will center on the axes and not the figure.
        plt.draw()
        # Create image. plt.savefig ignores figure edge and face colors, so map them.
        fig = plt.gcf()
        plt.savefig(
            out_filename,
            edgecolor=fig.get_edgecolor(),
            facecolor=fig.get_facecolor(),
            dpi=150,
        )
        plt.close(fig)

        plt.ion()

    def _make_plot(self, station: dict, time_scale: str):
        plt.ioff()  # Отключение интерактивного режима (чтобы окна при работе не мелькали)

        footer_text = station["db_time_past"]["recent"].strftime("%d.%m.%Y %H:%M")

        for _, parameter in station["parameters"].items():
            plt.figure(figsize=(6.4, 4.8 - 0.8))
            x = station["db_time_past"][time_scale]
            y = parameter["data"][time_scale]
            plt.plot(x, y)
            ax = plt.gca()
            ax.set_ylabel(parameter["full_name"], size=13)
            ax.tick_params("both", labelsize=12)
            plt.title(station["full_name"], size=14)
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
            if time_scale == "30d":
                ax.xaxis.set_major_locator(mdates.DayLocator(interval=7))
                ax.xaxis.set_minor_locator(mdates.DayLocator())
                ax.xaxis.set_major_formatter(mdates.DateFormatter("%b-%d"))
            if time_scale == "14d":
                ax.xaxis.set_major_locator(mdates.HourLocator(interval=48))
                ax.xaxis.set_minor_locator(mdates.HourLocator(interval=12))
                ax.xaxis.set_major_formatter(mdates.DateFormatter("%b-%d"))
            if time_scale == "7d":
                ax.xaxis.set_major_locator(mdates.HourLocator(interval=24))
                ax.xaxis.set_minor_locator(mdates.HourLocator(interval=6))
                ax.xaxis.set_major_formatter(mdates.DateFormatter("%b-%d"))
            if time_scale == "3d":
                ax.xaxis.set_major_locator(mdates.HourLocator(interval=24))
                ax.xaxis.set_minor_locator(mdates.HourLocator(interval=6))
                ax.xaxis.set_major_formatter(mdates.DateFormatter("%b-%d %H:%M"))
            if time_scale == "1d":
                ax.xaxis.set_major_locator(mdates.HourLocator(interval=4))
                ax.xaxis.set_minor_locator(mdates.HourLocator())
                ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
            ax.grid(True)
            ax.grid(which="minor", linestyle=":")
            plt.xlim(mdates.date2num(station["db_time_range_past"][time_scale]))

            plt.figtext(
                0.95,
                0.025,
                footer_text,
                horizontalalignment="right",
                size=10,
                weight="light",
            )
            out_filename = f"{station['code']}_{parameter['code']}_{self._config[f'{time_scale}-plot-suffix']}.png"
            out_filename = os.path.join(self._config["images-folder"], out_filename)

            fig = plt.gcf()
            plt.savefig(
                out_filename,
                edgecolor=fig.get_edgecolor(),
                facecolor=fig.get_facecolor(),
                dpi=150,
            )
            plt.close(fig)

        plt.ion()

    def make_plots(self, station: dict, time_depth: str):
        time_limit = {
            "c_yr": {"value": 7},  # 5
            "365d": {"value": 6},  # 4
            "30d": {"value": 5},  # 3
            "14d": {"value": 4},
            "7d": {"value": 3},  # 2
            "3d": {"value": 2},
            "1d": {"value": 1},
        }  # 1
        #        if time_limit[time_depth]['value'] == 7: # 5
        #            logging.info(f"Строю текущие годовые графики для станции {station['code']}")
        #            self._make_plot(station, 'c_yr')

        if time_limit[time_depth]["value"] == 6:  # 4
            logging.info(f"Строю годовые графики для станции {station['code']}")
            self._make_plot(station, "365d")

        if time_limit[time_depth]["value"] == 5:  # 3
            logging.info(f"Строю 30-дневные графики для станции {station['code']}")
            self._make_plot(station, "30d")

        if time_limit[time_depth]["value"] == 4:  # 2
            logging.info(f"Строю 14-дневные графики для станции {station['code']}")
            self._make_plot(station, "14d")

        if time_limit[time_depth]["value"] == 3:  # 2
            logging.info(f"Строю 7-дневные графики для станции {station['code']}")
            self._make_plot(station, "7d")

        if time_limit[time_depth]["value"] == 2:  # 2
            logging.info(f"Строю 3-дневные графики для станции {station['code']}")
            self._make_plot(station, "3d")

        if time_limit[time_depth]["value"] == 1:  # 1
            logging.info(f"Строю 1-дневные графики для станции {station['code']}")
            self._make_plot(station, "1d")

    def make_plots_forecast(self, station: dict, time_depth: str, time_forecast: str):
        logging.info(
            "Строю графики наблюдений для станции %s за прошлые %s дней",
            station["code"],
            time_depth[:-1],
        )
        suffix_floc = ""
        suffix_fglob = ""
        if self.local_forecast:
            logging.info(
                "Добавляю график локального (уточненного) прогноза за прошлые %s дней и на будущие %s дней",
                time_depth[:-1],
                time_forecast[:-1],
            )
            suffix_floc = "_floc"

        glob_forecast = self.glob_forecast
        if glob_forecast:
            if "om_time_prepast" in station:
                glob_forecast = False
                logging.info(
                    "Добавление глобального (сырого) прогноза невозможно, т.к. проводился расчет стат. прогноза"
                )
            else:
                logging.info(
                    "Добавляю график глобального (сырого) прогнозаза прошлые %s дней и на будущие %s дней",
                    time_depth[:-1],
                    time_forecast[:-1],
                )
                suffix_fglob = "_fglob"

        plt.ioff()  # Отключение интерактивного режима (чтобы окна при работе не мелькали)

        footer_text = station["db_time_past"]["recent"].strftime("%d.%m.%Y %H:%M")

        time_scale = int(time_depth[:-1]) + int(time_forecast[:-1])

        # Определение значений для оси Х
        x_obs = station["db_time_past"][time_depth]
        x_forecast_past = (
            station["om_time_past"][time_depth] if "om_time_past" in station else []
        )
        x_forecast_future = (
            station["om_time_future"][time_forecast]
            if "om_time_future" in station
            else []
        )

        # Формирование границ для оси Х
        if int(time_forecast[:-1]) > 0:
            x_limits = [
                station["db_time_range_past"][time_depth][0],
                (
                    station["om_time_range_future"][time_forecast][-1]
                    if "om_time_range_future" in station
                    else station["db_time_range_past"][time_depth][-1]
                ),
            ]
        else:
            x_limits = station["db_time_range_past"][time_depth]

        for _, parameter in station["parameters"].items():
            plt.figure(figsize=(6.4, 4.8 - 0.8))
            plt.xlim(mdates.date2num(x_limits))
            ax = plt.gca()

            # Отрисовка наблюдений

            y_obs = parameter["data"][time_depth]
            ax.plot(x_obs, y_obs, **self.obs_plot_kwargs)

            # Добавление локального (скорректированного) прогноза
            if self.local_forecast:
                if "om_data_local" in parameter:
                    # Отрисовка исторического интервала прогноза
                    if "past" in parameter["om_data_local"]:
                        y_local_past = parameter["om_data_local"]["past"][time_depth]
                        ax.plot(
                            x_forecast_past,
                            y_local_past,
                            **self.loc_past_plot_kwargs,
                        )

                    # Отрисовка прогноза вперед
                    if "future" in parameter["om_data_local"]:
                        y_local_future = parameter["om_data_local"]["future"][
                            time_forecast
                        ]
                        ax.plot(
                            x_forecast_future,
                            y_local_future,
                            **self.loc_future_plot_kwargs,
                        )

            # Добавление глобального (сырого) прогноза
            if glob_forecast:
                if (
                    "om_parameter" in parameter
                    and parameter["om_parameter"] in station["om_parameters"]
                ):
                    # Отрисовка исторического интервала прогноза
                    if "past" in station["om_parameters"][parameter["om_parameter"]]:
                        y_glob_past = station["om_parameters"][
                            parameter["om_parameter"]
                        ]["past"][time_depth]
                        ax.plot(
                            x_forecast_past,
                            y_glob_past,
                            **self.glob_past_plot_kwargs,
                        )

                    # Отрисовка прогноза вперед
                    if "future" in station["om_parameters"][parameter["om_parameter"]]:
                        y_glob_future = station["om_parameters"][
                            parameter["om_parameter"]
                        ]["future"][time_forecast]
                        ax.plot(
                            x_forecast_future,
                            y_glob_future,
                            **self.glob_future_plot_kwargs,
                        )

            ax.set_ylabel(parameter["full_name"], size=13)
            ax.tick_params("both", labelsize=12)
            plt.title(station["full_name"], size=14)
            plt.legend()

            if time_scale == 1:
                ax.xaxis.set_major_locator(mdates.HourLocator(interval=4))
                ax.xaxis.set_minor_locator(mdates.HourLocator())
                ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
            elif time_scale <= 3:
                ax.xaxis.set_major_locator(mdates.HourLocator(interval=24))
                ax.xaxis.set_minor_locator(mdates.HourLocator(interval=6))
                ax.xaxis.set_major_formatter(mdates.DateFormatter("%b-%d %H:%M"))
            elif time_scale <= 7:
                ax.xaxis.set_major_locator(mdates.HourLocator(interval=24))
                ax.xaxis.set_minor_locator(mdates.HourLocator(interval=6))
                ax.xaxis.set_major_formatter(mdates.DateFormatter("%b-%d"))
            elif time_scale <= 14:
                ax.xaxis.set_major_locator(mdates.HourLocator(interval=48))
                ax.xaxis.set_minor_locator(mdates.HourLocator(interval=12))
                ax.xaxis.set_major_formatter(mdates.DateFormatter("%b-%d"))
            elif time_scale <= 30:
                ax.xaxis.set_major_locator(mdates.DayLocator(interval=7))
                ax.xaxis.set_minor_locator(mdates.DayLocator())
                ax.xaxis.set_major_formatter(mdates.DateFormatter("%b-%d"))
            else:
                ax.xaxis.set_major_locator(mdates.DayLocator(interval=10))
                ax.xaxis.set_minor_locator(mdates.DayLocator())
                ax.xaxis.set_major_formatter(mdates.DateFormatter("%b-%d"))

            ax.grid(True)
            ax.grid(which="minor", linestyle=":")

            plt.figtext(
                0.95,
                0.025,
                footer_text,
                horizontalalignment="right",
                size=10,
                weight="light",
            )

            # Сохранение в файл .png
            out_filename = f"{station['code']}_{parameter['code']}_{time_depth}-past_{time_forecast}-future{suffix_floc}{suffix_fglob}.png"
            out_filename = os.path.join(self._config["images-folder"], out_filename)

            fig = plt.gcf()
            plt.savefig(
                out_filename,
                edgecolor=fig.get_edgecolor(),
                facecolor=fig.get_facecolor(),
                dpi=150,
            )
            plt.close(fig)

        plt.ion()
