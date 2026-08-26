import datetime
import logging
import os

import matplotlib.cm as cm
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np


class PlotterQC:
    def __init__(
        self,
        args: dict,
        now_dates_forec_obs: dict[str, str],
        data: dict,
        # in_data: dict,
        # timelines: dict,
    ):

        self.args = args
        self.now_dates_forec_obs = now_dates_forec_obs
        self.now_dates = sorted(list(now_dates_forec_obs.keys()))
        self.data = data
        # self.in_data = in_data
        # self.timelines = timelines

        self.start_date_str = args["main-args"]["start-date"]
        self.end_date_str = args["main-args"]["end-date"]
        self.step_date_str = args["main-args"]["step-date"]
        self.output_folder = args["main-args"]["output-folder"]
        self.plot_mode = args["main-args"]["plot-mode"]
        self.color_map = args["main-args"]["color-map"]

        self.time_depth = args["forecast-args"]["time-depth"]
        self.time_forecast = args["forecast-args"]["time-forecast"]
        self.forecast_type = args["forecast-args"]["forecast-type"]

        self.exp_name = args["data-args"]["experiment-name"]

        self.filename_prefix = (
            "apik-forecast_"
            + self.exp_name
            + "_"
            + self.start_date_str
            + "_"
            + self.end_date_str
            + "_step"
            + self.step_date_str
            + "_"
            + self.forecast_type
            + "_td"
            + self.time_depth
            + "_tf"
            + self.time_forecast
        )
        self.filename_suffix = [
            "_loc_future",
            "_loc_past-future",
            "_loc-glob_future",
            "_loc-glob_past-future",
        ]
        if self.plot_mode == "color":
            self.obs_plot_kwargs = {
                "scalex": True,
                "scaley": True,
                "marker": "o",
                "markersize": 4,
                "markevery": 4,
                "color": "black",  # "blue",
                "markeredgecolor": "black",  # "blue",
                "markerfacecolor": "white",
                "label": "Наблюдения",
            }
            self.loc_past_plot_kwargs = {
                "scalex": True,
                "scaley": True,
                "linestyle": "--",
                "color": "forestgreen",
            }
            self.loc_future_plot_kwargs = {
                "scalex": True,
                "scaley": True,
                "color": "forestgreen",
            }
            self.glob_past_plot_kwargs = {
                "scalex": True,
                "scaley": True,
                "linestyle": "--",
                "color": "darkred",
            }
            self.glob_future_plot_kwargs = {
                "scalex": True,
                "scaley": True,
                "color": "darkred",
            }
        elif self.plot_mode == "bw":
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
                "linestyle": "--",
                "color": "gray",
            }
            self.loc_future_plot_kwargs = {
                "scalex": True,
                "scaley": True,
                "color": "gray",
            }
            self.glob_past_plot_kwargs = {
                "scalex": True,
                "scaley": True,
                "linestyle": "--",
                "color": "black",
                "linewidth": 1,
            }
            self.glob_future_plot_kwargs = {
                "scalex": True,
                "scaley": True,
                "color": "black",
                "linewidth": 1,
            }
        else:  # self.plot_mode == "grad"
            n_colors = len(self.now_dates)
            self.colormap = cm.get_cmap(self.color_map)
            self.colors = [self.colormap(i / (n_colors - 1)) for i in range(n_colors)]

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
                "linestyle": "--",
            }
            self.loc_future_plot_kwargs = {
                "scalex": True,
                "scaley": True,
            }
            self.glob_past_plot_kwargs = {
                "scalex": True,
                "scaley": True,
                "linestyle": "--",
                "color": "gray",
                "linewidth": 2,
            }
            self.glob_future_plot_kwargs = {
                "scalex": True,
                "scaley": True,
                "color": "gray",
                "linewidth": 2,
            }

    def _plot_par(
        self,
        par_name: str,
        par_info: dict,
        station_info: dict,
        past: bool = False,
        glob: bool = False,
    ) -> None:
        logging.info(
            "Отрисовка сводного графика для станции %s для параметра %s",
            station_info["code"],
            par_name,
        )

        if past and glob:
            logging.info("Прогнозы past + future локальные и глобальные")
            suffix = self.filename_suffix[3]
            start_date = self.data["obs_timeline"][0]
            idx_start = 0
        elif past and not glob:
            logging.info("Прогнозы past + future только локальные")
            suffix = self.filename_suffix[1]
            start_date = self.data["obs_timeline"][0]
            idx_start = 0
        elif not past and glob:
            logging.info("Прогнозы только future локальные и глобальные")
            suffix = self.filename_suffix[2]
            start_date = datetime.datetime.strptime(
                self.start_date_str, "%Y-%m-%d"
            ).replace(tzinfo=datetime.timezone.utc)
            idx_start = self.data["obs_timeline"].index(start_date)
        else:
            logging.info("Прогнозы только future и только локальные")
            suffix = self.filename_suffix[0]
            start_date = datetime.datetime.strptime(
                self.start_date_str, "%Y-%m-%d"
            ).replace(tzinfo=datetime.timezone.utc)
            idx_start = self.data["obs_timeline"].index(start_date)

        plt.ioff()  # Отключение интерактивного режима (чтобы окна при работе не мелькали)

        # Формирование границ для оси Х
        x_limits = [
            start_date,
            self.data["obs_timeline"][-1],
        ]
        time_scale = (x_limits[1] - x_limits[0]).days

        # Определение значений для оси Х
        x_obs = self.data["obs_timeline"][idx_start:]

        plt.figure(figsize=(9.6, 4.8 - 0.8))
        plt.xlim(mdates.date2num(x_limits))
        ax = plt.gca()

        # Отрисовка наблюдений
        y_obs = par_info["obs"][idx_start:]
        ax.plot(x_obs, y_obs, **self.obs_plot_kwargs)

        # отрисовка прогнозов локальных и глобальных
        if past and glob:
            for now_idx, now_date in enumerate(self.now_dates):
                for forec_type, forec_label in zip(
                    ["local", "global"], ["Локальный", "Глобальный"]
                ):
                    now_date_data = par_info[forec_type]["future"][now_date]
                    x_forec = now_date_data["timeline"]
                    y_forec = now_date_data["data"]
                    if (self.plot_mode == "grad") and (forec_type == "local"):
                        ax.plot(
                            x_forec,
                            y_forec,
                            **(
                                self.loc_future_plot_kwargs
                                if forec_type == "local"
                                else self.glob_future_plot_kwargs
                            ),
                            color=self.colors[now_idx],
                            label=(f"{forec_label} прогноз" if now_idx == 0 else None),
                        )
                    else:
                        ax.plot(
                            x_forec,
                            y_forec,
                            **(
                                self.loc_future_plot_kwargs
                                if forec_type == "local"
                                else self.glob_future_plot_kwargs
                            ),
                            label=(f"{forec_label} прогноз" if now_idx == 0 else None),
                        )

                    now_date_data = par_info[forec_type]["past"][now_date]
                    x_past = now_date_data["timeline"]
                    y_past = now_date_data["data"]
                    if (self.plot_mode == "grad") and (forec_type == "local"):
                        ax.plot(
                            x_past,
                            y_past,
                            **(
                                self.loc_past_plot_kwargs
                                if forec_type == "local"
                                else self.glob_past_plot_kwargs
                            ),
                            color=self.colors[now_idx],
                            label=(
                                f"{forec_label} прогноз (обучение)"
                                if now_idx == 0
                                else None
                            ),
                        )
                    else:
                        ax.plot(
                            x_past,
                            y_past,
                            **(
                                self.loc_past_plot_kwargs
                                if forec_type == "local"
                                else self.glob_past_plot_kwargs
                            ),
                            label=(
                                f"{forec_label} прогноз (обучение)"
                                if now_idx == 0
                                else None
                            ),
                        )
        elif past and not glob:
            for now_idx, now_date in enumerate(self.now_dates):
                now_date_data = par_info["local"]["future"][now_date]
                x_forec = now_date_data["timeline"]
                y_forec = now_date_data["data"]
                if self.plot_mode == "grad":
                    ax.plot(
                        x_forec,
                        y_forec,
                        **self.loc_future_plot_kwargs,
                        color=self.colors[now_idx],
                        label=("Локальный прогноз" if now_idx == 0 else None),
                    )
                else:
                    ax.plot(
                        x_forec,
                        y_forec,
                        **self.loc_future_plot_kwargs,
                        label=("Локальный прогноз" if now_idx == 0 else None),
                    )

                now_date_data = par_info["local"]["past"][now_date]
                x_past = now_date_data["timeline"]
                y_past = now_date_data["data"]
                if self.plot_mode == "grad":
                    ax.plot(
                        x_past,
                        y_past,
                        **self.loc_past_plot_kwargs,
                        color=self.colors[now_idx],
                        label=(
                            "Локальный прогноз (обучение)" if now_idx == 0 else None
                        ),
                    )
                else:
                    ax.plot(
                        x_past,
                        y_past,
                        **self.loc_past_plot_kwargs,
                        label=(
                            "Локальный прогноз (обучение)" if now_idx == 0 else None
                        ),
                    )
        elif not past and glob:
            for now_idx, now_date in enumerate(self.now_dates):
                for forec_type, forec_label in zip(
                    ["local", "global"],
                    ["Локальный", "Глобальный"],
                ):
                    now_date_data = par_info[forec_type]["future"][now_date]
                    x_forec = now_date_data["timeline"]
                    y_forec = now_date_data["data"]
                    if (self.plot_mode == "grad") and (forec_type == "local"):
                        ax.plot(
                            x_forec,
                            y_forec,
                            **(
                                self.loc_future_plot_kwargs
                                if forec_type == "local"
                                else self.glob_future_plot_kwargs
                            ),
                            color=self.colors[now_idx],
                            label=(f"{forec_label} прогноз" if now_idx == 0 else None),
                        )
                    else:
                        ax.plot(
                            x_forec,
                            y_forec,
                            **(
                                self.loc_future_plot_kwargs
                                if forec_type == "local"
                                else self.glob_future_plot_kwargs
                            ),
                            label=(f"{forec_label} прогноз" if now_idx == 0 else None),
                        )
        else:  # not past and not glob
            for now_idx, now_date in enumerate(self.now_dates):
                now_date_data = par_info["local"]["future"][now_date]
                x_forec = now_date_data["timeline"]
                y_forec = now_date_data["data"]
                if self.plot_mode == "grad":
                    ax.plot(
                        x_forec,
                        y_forec,
                        **self.loc_future_plot_kwargs,
                        color=self.colors[now_idx],
                        label=(f"Локальный прогноз" if now_idx == 0 else None),
                    )
                else:
                    ax.plot(
                        x_forec,
                        y_forec,
                        **self.loc_future_plot_kwargs,
                        label=(f"Локальный прогноз" if now_idx == 0 else None),
                    )

        ax.set_ylabel(par_info["full_name"], size=13)
        ax.tick_params("both", labelsize=12)
        plt.title(f"{station_info['code']} - {station_info['full_name']}", size=14)
        plt.legend()

        if time_scale <= 7:
            ax.xaxis.set_major_locator(mdates.HourLocator(interval=24))
            ax.xaxis.set_minor_locator(mdates.HourLocator(interval=6))
            ax.xaxis.set_major_formatter(mdates.DateFormatter("%b-%d"))
        elif time_scale <= 14:
            ax.xaxis.set_major_locator(mdates.HourLocator(interval=48))
            ax.xaxis.set_minor_locator(mdates.HourLocator(interval=12))
            ax.xaxis.set_major_formatter(mdates.DateFormatter("%b-%d"))
        elif time_scale <= 30:
            # ax.xaxis.set_major_locator(mdates.DayLocator(interval=7))
            # ax.xaxis.set_minor_locator(mdates.DayLocator())
            ax.xaxis.set_major_locator(mdates.HourLocator(interval=48))
            ax.xaxis.set_minor_locator(mdates.HourLocator(interval=12))
            ax.xaxis.set_major_formatter(mdates.DateFormatter("%b-%d"))
        else:
            ax.xaxis.set_major_locator(mdates.DayLocator(interval=10))
            ax.xaxis.set_minor_locator(mdates.DayLocator())
            ax.xaxis.set_major_formatter(mdates.DateFormatter("%b-%d"))

        ax.grid(True)
        ax.grid(which="minor", linestyle=":")

        # ------------------------------
        # Сохранение в файл .png
        fname = (
            self.filename_prefix
            + "_"
            + station_info["code"]
            + "-"
            + par_name
            + suffix
            + "_"
            + self.plot_mode
            + ".png"
        )
        out_filename = os.path.join(self.output_folder, fname)

        fig = plt.gcf()
        plt.savefig(
            out_filename,
            edgecolor=fig.get_edgecolor(),
            facecolor=fig.get_facecolor(),
            dpi=150,
        )
        plt.close(fig)

        plt.ion()

    def make_plots(self):
        logging.info("Отрисовка сводных графиков прогнозов и наблюдений")

        for station_code, station_data in self.data["stations"].items():
            station_info = {
                "code": station_code,
                "full_name": station_data["full_name"],
                "lat": station_data["lat"],
                "lon": station_data["lon"],
            }

            for par_name, par_info in station_data["parameters"].items():
                # (1) Отрисовка только local и только future
                self._plot_par(par_name, par_info, station_info, past=False, glob=False)

                # (2) Отрисовка только local, но past + future
                # self._plot_par(par_name, par_info, station_info, past=True, glob=False)

                # (3)  Отрисовка local + global (если есть), но только future
                self._plot_par(par_name, par_info, station_info, past=False, glob=True)

                # (4) Отрисовка local + global (если есть) для past + future
                # self._plot_par(par_name, par_info, station_info, past=True, glob=True)

        #       Сборка наблюдений на одну ось и сборка оси времени
        #       (1) Отрисовка ["data_local"]["future"]
        #       (2) Отрисовка ["data_local"]["future"] + ["data_local"]["past"]
        #       Если получено по OM (т.е. есть ["timeline"]["prepast"][self.time_depth]):
        #           Если для параметра есть прямое соответствие с OM (есть <om_par_name>):
        #               (3) Отрисовка ["data_local"]["future"] + ["predictors_data"][<om_par_name>]["future"]
        #               (4) Отрисовка ["data_local"]["future"] + ["data_local"]["past"] + ["predictors_data"][<om_par_name>]["future"] + ["predictors_data"][<om_par_name>]["past"]
