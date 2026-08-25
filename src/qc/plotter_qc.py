import logging


class PlotterQC:
    def __init__(
        self,
        args: dict,
        # now_dates_forec_obs: dict[str, str],
        data: dict,
        # in_data: dict,
        # timelines: dict,
    ):

        self.args = args
        # self.now_dates_forec_obs = now_dates_forec_obs
        self.data = data
        # self.in_data = in_data
        # self.timelines = timelines

        self.start_date_str = args["main-args"]["start-date"]
        self.end_date_str = args["main-args"]["end-date"]
        self.step_date_str = args["main-args"]["step-date"]
        self.output_folder = args["main-args"]["output-folder"]

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
            "loc_future",
            "loc_past-future",
            "loc-glob_future",
            "loc-glob_past-future",
        ]

    def _plot_par(
        self,
        par_name: str,
        par_info: dict,
        station_info: dict,
        past: bool = False,
        glob: bool = False,
    ) -> None: ...

    def make_plots(self):
        logging.info("Отрисовка сводных графиков прогнозов и наблюдений")

        for station_code, station_data in self.data.items():
            station_info = {
                "code": station_code,
                "full_name": station_data["full_name"],
                "lat": station_data["lat"],
                "lon": station_data["lon"],
            }

            for par_name, par_info in station_data["parameters"]:
                # (1) Отрисовка только local и только future
                self._plot_par(par_name, par_info, station_info, past=False, glob=False)

                # (2) Отрисовка только local, но past + future
                self._plot_par(par_name, par_info, station_info, past=True, glob=False)

                # (3)  Отрисовка local + global (если есть), но только future
                self._plot_par(par_name, par_info, station_info, past=False, glob=True)

                # (4) Отрисовка local + global (если есть) для past + future
                self._plot_par(par_name, par_info, station_info, past=True, glob=True)

        #       Сборка наблюдений на одну ось и сборка оси времени
        #       (1) Отрисовка ["data_local"]["future"]
        #       (2) Отрисовка ["data_local"]["future"] + ["data_local"]["past"]
        #       Если получено по OM (т.е. есть ["timeline"]["prepast"][self.time_depth]):
        #           Если для параметра есть прямое соответствие с OM (есть <om_par_name>):
        #               (3) Отрисовка ["data_local"]["future"] + ["predictors_data"][<om_par_name>]["future"]
        #               (4) Отрисовка ["data_local"]["future"] + ["data_local"]["past"] + ["predictors_data"][<om_par_name>]["future"] + ["predictors_data"][<om_par_name>]["past"]
