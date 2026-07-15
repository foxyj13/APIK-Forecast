import datetime
import logging
import time

import numpy as np
from scipy import interpolate
from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import NoResultFound


class DBReader:
    def __init__(self, server, port, user, password, database):
        self.server = server
        self.port = port
        self.user = user
        self.password = password
        self.database = database

        self.meta = None
        self.session = None

    def connect(self) -> bool:
        logging.info("Подключаюсь к БД")

        try:
            db_url = f"mysql://{self.user}:{self.password}@{self.server}:{self.port}/{self.database}"
            engine = create_engine(db_url)
            self.meta = MetaData()
            self.meta.reflect(bind=engine)
            self.session = sessionmaker(bind=engine)()
        except Exception as ex:
            logging.error("Ошибка подключения!")
            logging.error("Exception: %s", ex)

            return False
        logging.info("OK!")
        return True

    @staticmethod
    def _fix_value(value, no_value):
        result = value
        if no_value:
            if int(result) == int(no_value):
                result = None
        return result

    def get_station_data(
        self, station: dict, time_depth: str = "7d", now_date=None
    ) -> dict:

        def timeline_to_hourly(
            time_depth: str,
            datetime_ranges: dict,  # result["db_time_range_past"],
            timelines: dict,  # result["db_time_past"],
            parameters: dict,  # station["parameters"],
        ):
            logging.info(
                "Преобразование данных к ежечасным: выбирается ближайшее к полному часу значение"
            )

            tds = ["c_yr", "365d", "30d", "14d", "7d", "3d", "1d"]
            dt_range = [
                datetime_ranges[time_depth][0].replace(
                    minute=0, second=0, microsecond=0
                )
                + datetime.timedelta(hours=1),
                datetime_ranges[time_depth][1].replace(
                    minute=0, second=0, microsecond=0
                ),
            ]

            hours_diff = ((dt_range[1] - dt_range[0]).days + 1) * 24
            timeline_ref = [
                dt_range[0] + datetime.timedelta(hours=dh) for dh in range(hours_diff)
            ]

            for td_val in tds[tds.index(time_depth) :]:
                dt_start = datetime_ranges[td_val][0].replace(
                    minute=0, second=0, microsecond=0
                ) + datetime.timedelta(hours=1)
                td_timeline_ref = timeline_ref[timeline_ref.index(dt_start) :]
                timeline_orig = timelines[td_val]

                td_timeline_timestamp_ref = [
                    time_val.timestamp() for time_val in td_timeline_ref
                ]
                timeline_timestamp_orig = [
                    time_val.timestamp() for time_val in timeline_orig
                ]

                timelines[td_val] = td_timeline_ref

                for par_name, par_info in parameters.items():
                    data_orig = par_info["data"][td_val]

                    to_hourly = interpolate.interp1d(
                        x=timeline_timestamp_orig,
                        y=data_orig,
                        kind="nearest",
                        bounds_error=False,
                        fill_value=np.nan,
                        assume_sorted=True,
                    )
                    par_info["data"][td_val] = to_hourly(td_timeline_timestamp_ref)

            return timelines, parameters

        logging.info(
            "Считываю данные из БД для станции %s (%s)",
            station["code"],
            station["full_name"],
        )

        utc_now = time.time()  # Current time in UTC
        utc_now_date = datetime.datetime.fromtimestamp(
            utc_now, tz=datetime.timezone.utc
        )
        utc_1d_before = utc_now - 24 * 60 * 60  # 1 day before
        utc_1d_before_date = datetime.datetime.fromtimestamp(
            utc_1d_before, tz=datetime.timezone.utc
        )
        utc_3d_before = utc_now - 3 * 24 * 60 * 60  # 3 day before
        utc_3d_before_date = datetime.datetime.fromtimestamp(
            utc_3d_before, tz=datetime.timezone.utc
        )
        utc_7d_before = utc_now - 7 * 24 * 60 * 60  # 7 days before
        utc_7d_before_date = datetime.datetime.fromtimestamp(
            utc_7d_before, tz=datetime.timezone.utc
        )
        utc_14d_before = utc_now - 14 * 24 * 60 * 60  # 14 days before
        utc_14d_before_date = datetime.datetime.fromtimestamp(
            utc_14d_before, tz=datetime.timezone.utc
        )
        utc_30d_before = utc_now - 30 * 24 * 60 * 60  # 30 days before
        utc_30d_before_date = datetime.datetime.fromtimestamp(
            utc_30d_before, tz=datetime.timezone.utc
        )
        utc_365d_before = utc_now - 365 * 24 * 60 * 60  # 365 days before
        utc_365d_before_date = datetime.datetime.fromtimestamp(
            utc_365d_before, tz=datetime.timezone.utc
        )

        year = datetime.datetime.now().year
        utc_1_jan_year = datetime.datetime(year - 1, 12, 31, 23, 0, 0).timestamp()
        utc_1_jan_year_date = datetime.datetime.fromtimestamp(utc_1_jan_year)

        time_limit = {
            "c_yr": {"limit": utc_1_jan_year, "value": 7},  # value: 5
            "365d": {"limit": utc_365d_before, "value": 6},  # value: 4
            "30d": {"limit": utc_30d_before, "value": 5},  # value: 3
            "14d": {"limit": utc_14d_before, "value": 4},
            "7d": {"limit": utc_7d_before, "value": 3},  # value: 2
            "3d": {"limit": utc_3d_before, "value": 2},
            "1d": {"limit": utc_1d_before, "value": 1},  # value: 1
        }
        result = station

        if time_depth not in time_limit:
            logging.error('ERROR! Неверное значение time depth: "%s"', time_depth)
            return {}

        if self.meta and self.session and station["code"] in self.meta.tables:
            data_tbl = self.meta.tables[station["code"]]
            qry = self.session.query(data_tbl.columns["timezone"].label("timezone"))
            qry = qry.add_columns(data_tbl.columns["time"].label("time"))
            for parameter in station["parameters"].values():
                if parameter["code"] in data_tbl.columns.keys():
                    qry = qry.add_columns(
                        data_tbl.columns[parameter["code"]].label(parameter["name"])
                    )
                else:
                    logging.error(
                        'ОШИБКА! Нет кода: %s для параметра "%s"',
                        parameter["code"],
                        parameter["name"],
                    )
                    return result
            qry = qry.select_from(data_tbl)
            qry_f = qry.filter(data_tbl.c.time >= time_limit[time_depth]["limit"])
            try:
                rows = qry_f.all()
            except NoResultFound:
                logging.error("ОШИБКА! В БД не найдено ни одного результата!")
                return {}

            data_present = True
            if not rows:
                logging.warning(
                    "Внимание! За запрошенный диапазон (%s) нет данных для станции %s. "
                    "Использую последние доступные.",
                    time_depth,
                    station["code"],
                )
                data_present = False
                rows = qry.all()

            # Prepare
            station_timeshift = datetime.timedelta(hours=rows[0].timezone)

            result["station_timeshift"] = station_timeshift

            result["db_time_past"] = {}
            result["db_time_past"] = {
                "c_yr": [],
                "365d": [],
                "30d": [],
                "14d": [],
                "7d": [],
                "3d": [],
                "1d": [],
                # "recent": datetime.datetime.fromtimestamp(
                #     rows[-1].time, tz=datetime.timezone.utc
                # )
                # + station_timeshift,
            }
            result["db_time_range_past"] = {
                "c_yr": [
                    utc_1_jan_year_date + station_timeshift,
                    utc_now_date + station_timeshift,
                ],
                "365d": [
                    utc_365d_before_date + station_timeshift,
                    utc_now_date + station_timeshift,
                ],
                "30d": [
                    utc_30d_before_date + station_timeshift,
                    utc_now_date + station_timeshift,
                ],
                "14d": [
                    utc_14d_before_date + station_timeshift,
                    utc_now_date + station_timeshift,
                ],
                "7d": [
                    utc_7d_before_date + station_timeshift,
                    utc_now_date + station_timeshift,
                ],
                "3d": [
                    utc_3d_before_date + station_timeshift,
                    utc_now_date + station_timeshift,
                ],
                "1d": [
                    utc_1d_before_date + station_timeshift,
                    utc_now_date + station_timeshift,
                ],
            }
            for parameter in station["parameters"].values():
                parameter["data"] = {
                    "c_yr": [],
                    "365d": [],
                    "30d": [],
                    "14d": [],
                    "7d": [],
                    "3d": [],
                    "1d": [],
                }

            if data_present:
                # Store date and time.
                for row in rows:
                    # Read time and data. Set missing data values to None
                    row_time = (
                        datetime.datetime.fromtimestamp(
                            row.time, tz=datetime.timezone.utc
                        )
                        + station_timeshift
                    )

                    # Store time in the result
                    if time_limit[time_depth]["value"] == 7:  # 5
                        result["db_time_past"]["c_yr"].append(row_time)
                    if time_limit[time_depth]["value"] == 6:  # 4
                        result["db_time_past"]["365d"].append(row_time)
                    if time_limit[time_depth]["value"] == 5:  # 3
                        result["db_time_past"]["30d"].append(row_time)
                    if (
                        row.time >= utc_14d_before
                        and time_limit[time_depth]["value"] >= 4  # 2
                    ):
                        result["db_time_past"]["14d"].append(row_time)
                    if (
                        row.time >= utc_7d_before
                        and time_limit[time_depth]["value"] >= 3  # 2
                    ):
                        result["db_time_past"]["7d"].append(row_time)
                    if (
                        row.time >= utc_3d_before
                        and time_limit[time_depth]["value"] >= 2  # 2
                    ):
                        result["db_time_past"]["3d"].append(row_time)
                    if (
                        row.time >= utc_1d_before
                        and time_limit[time_depth]["value"] >= 1  # 1
                    ):
                        result["db_time_past"]["1d"].append(row_time)

                    for parameter in station["parameters"].values():
                        row_value = self._fix_value(
                            row._mapping[parameter["name"]], parameter["no_value"]
                        )
                        # Store data in the result
                        if time_limit[time_depth]["value"] == 7:
                            parameter["data"]["c_yr"].append(row_value)
                        if time_limit[time_depth]["value"] == 6:
                            parameter["data"]["365d"].append(row_value)
                        if time_limit[time_depth]["value"] == 5:
                            parameter["data"]["30d"].append(row_value)
                        if (
                            row.time >= utc_14d_before
                            and time_limit[time_depth]["value"] >= 4
                        ):
                            parameter["data"]["14d"].append(row_value)
                        if (
                            row.time >= utc_7d_before
                            and time_limit[time_depth]["value"] >= 3
                        ):
                            parameter["data"]["7d"].append(row_value)
                        if (
                            row.time >= utc_3d_before
                            and time_limit[time_depth]["value"] >= 2
                        ):
                            parameter["data"]["3d"].append(row_value)
                        if (
                            row.time >= utc_1d_before
                            and time_limit[time_depth]["value"] >= 1
                        ):
                            parameter["data"]["1d"].append(row_value)

                db_time_past, parameters = timeline_to_hourly(
                    time_depth,
                    result["db_time_range_past"],
                    result["db_time_past"],
                    station["parameters"],
                )
                result["db_time_past"] = db_time_past
                station["parameters"] = parameters

            result["db_time_past"]["recent"] = result["db_time_past"]["1d"][-1]
            for parameter in station["parameters"].values():
                parameter["data"]["recent"] = parameter["data"]["1d"][-1]
                # parameter["data"]["recent"] = self._fix_value(
                #     rows[-1]._mapping[parameter["name"]], parameter["no_value"]
                # )
        else:
            logging.error(
                "ОШИБКА! Станции с кодом %s в БД не обнаружено!", station["code"]
            )
            return {}
        return result

    def get_station_predictors(
        self, station: dict, time_depth: str, time_forecast: str, now_date=None
    ) -> tuple[bool, dict]:

        def timeline_to_hourly(
            time_depth: str,
            past_type: str,  # "past" | "prerast",
            datetime_ranges: dict,  # station["om_time_range_past"],
            timelines: dict,  # station["om_time_past"],
            parameters: dict,  # station["om_parameters"]
        ):
            logging.info(
                "[%s] Преобразование данных к ежечасным: выбирается ближайшее к полному часу значение",
                past_type,
            )

            dt_range = [
                datetime_ranges[time_depth][0].replace(
                    minute=0, second=0, microsecond=0
                )
                + datetime.timedelta(hours=1),
                datetime_ranges[time_depth][1].replace(
                    minute=0, second=0, microsecond=0
                ),
            ]

            hours_diff = ((dt_range[1] - dt_range[0]).days + 1) * 24
            timeline_ref = [
                dt_range[0] + datetime.timedelta(hours=dh) for dh in range(hours_diff)
            ]
            timeline_orig = timelines[time_depth]

            timeline_timestamp_ref = [time_val.timestamp() for time_val in timeline_ref]
            timeline_timestamp_orig = [
                time_val.timestamp() for time_val in timeline_orig
            ]

            timelines[time_depth] = timeline_ref

            for par_name, par_info in parameters.items():
                data_orig = par_info[past_type][time_depth]

                to_hourly = interpolate.interp1d(
                    x=timeline_timestamp_orig,
                    y=data_orig,
                    kind="nearest",
                    bounds_error=False,
                    fill_value=np.nan,
                    assume_sorted=True,
                )
                par_info[past_type][time_depth] = to_hourly(timeline_timestamp_ref)

            return timelines, parameters

        logging.info(
            "Дополнительное считывание данных из БД для статистического прогноза для станции %s (%s)",
            station["code"],
            station["full_name"],
        )

        # Определение временных пределов для prepast и past
        utc_now = time.time()  # Current time in UTC
        utc_now_date = datetime.datetime.fromtimestamp(
            utc_now, tz=datetime.timezone.utc
        )

        # now - time_depth - time_forecast
        utc_td_tf_before = (
            utc_now - (int(time_depth[:-1]) + int(time_forecast[:-1])) * 24 * 60 * 60
        )
        utc_td_tf_before_date = datetime.datetime.fromtimestamp(
            utc_td_tf_before, tz=datetime.timezone.utc
        )

        # now - time_forecast
        utc_tf_before = utc_now - int(time_forecast[:-1]) * 24 * 60 * 60
        utc_tf_before_date = datetime.datetime.fromtimestamp(
            utc_tf_before, tz=datetime.timezone.utc
        )

        # now - time_depth
        utc_td_before = utc_now - int(time_depth[:-1]) * 24 * 60 * 60
        utc_td_before_date = datetime.datetime.fromtimestamp(
            utc_td_before, tz=datetime.timezone.utc
        )

        # Формирование перечня предикторов и их возможных кодов, необходимых для дальнейшей работы по этой станции
        # predictor_names = set()
        # redictor_codes = {}
        predictors = {}
        for par_name, par_info in station["parameters"].items():
            # predictor_names = predictor_names | set(par_info["db_predictors"])
            # predictor_codes.update(par_info["db_predictors_codes"])
            predictors.update(par_info["db_predictors"])

        # Формирование запроса и выборка данных
        if self.meta and self.session and station["code"] in self.meta.tables:
            data_tbl = self.meta.tables[station["code"]]
            qry = self.session.query(data_tbl.columns["timezone"].label("timezone"))
            qry = qry.add_columns(data_tbl.columns["time"].label("time"))

            for pred_name, pred_info in predictors.items():
                for pred_code in pred_info["codes"]:
                    if pred_code in data_tbl.columns.keys():
                        qry = qry.add_columns(
                            data_tbl.columns[pred_code].label(pred_name)
                        )

            # Выбрать данные для периода prepast: [now - time_depth - time_forecast; now - time_forecast)
            qry = qry.select_from(data_tbl)
            qry_prepast = qry.filter(
                data_tbl.c.time >= utc_td_tf_before, data_tbl.c.time <= utc_tf_before
            )
            try:
                rows_prepast = qry_prepast.all()
            except NoResultFound:
                logging.error(
                    "ОШИБКА! В БД не найдено ни одного результата для периода [now - time_depth - time_forecast; now - time_forecast]!"
                )
                return False, station

            if not rows_prepast:
                logging.error(
                    "Нет данных для периода [now - time_depth - time_forecast; now - time_forecast]!"
                )
                return False, station

            # Выбрать данные для периода past: [now - time_depth; now)
            qry_past = qry.filter(data_tbl.c.time >= utc_td_before)
            try:
                rows_past = qry_past.all()
            except NoResultFound:
                logging.error(
                    "ОШИБКА! В БД не найдено ни одного результата для периода [now - time_depth; now]!"
                )
                return False, station

            if not rows_past:
                logging.error("Нет данных для периода [now - time_depth; now]!")
                return False, station

            station_timeshift = datetime.timedelta(hours=rows_prepast[0].timezone)

            station["om_time_prepast"] = {time_depth: []}
            station["om_time_past"] = {
                time_depth: [],
                # "recent": datetime.datetime.fromtimestamp(
                #     rows_past[-1].time, tz=datetime.timezone.utc
                # )
                # + station_timeshift,
            }

            # station["om_time_future"] = {}
            # station["om_time_future"][time_forecast] = [
            #     station["om_time_past"]["recent"] + datetime.timedelta(hours=hh + 1)
            #     for hh in range(int(time_forecast[:-1]) * 24)
            # ]
            # station["om_time_range_future"] = {}
            # station["om_time_range_future"] = [
            #     station["om_time_future"][time_forecast][0],
            #     station["om_time_future"][time_forecast][-1],
            # ]

            station["om_time_range_prepast"] = {}
            station["om_time_range_past"] = {}
            station["om_time_range_prepast"][time_depth] = [
                utc_td_tf_before_date + station_timeshift,
                utc_tf_before_date + station_timeshift,
            ]
            station["om_time_range_past"][time_depth] = [
                utc_td_before_date + station_timeshift,
                utc_now_date + station_timeshift,
            ]

            # Инициализация ветки в station для хранения метеопараметров взамен ОМ
            # Структура хранения та же, но данные - наблюдений, а не ОМ
            station["om_parameters"] = {}

            # Запись полученных из БД данных в структуру
            for row in rows_prepast:
                row_time = (
                    datetime.datetime.fromtimestamp(row.time, tz=datetime.timezone.utc)
                    + station_timeshift
                )
                station["om_time_prepast"][time_depth].append(row_time)

                for pred_name, pred_info in predictors.items():
                    row_value = self._fix_value(
                        row._mapping[pred_name], pred_info["no_value"]
                    )

                    if pred_name in station["om_parameters"]:
                        station["om_parameters"][pred_name]["prepast"][
                            time_depth
                        ].append(row_value)
                    else:
                        station["om_parameters"][pred_name] = {}
                        station["om_parameters"][pred_name]["prepast"] = {
                            time_depth: [row_value]
                        }

            for row in rows_past:
                row_time = (
                    datetime.datetime.fromtimestamp(row.time, tz=datetime.timezone.utc)
                    + station_timeshift
                )
                station["om_time_past"][time_depth].append(row_time)

                for pred_name, pred_info in predictors.items():
                    row_value = self._fix_value(
                        row._mapping[pred_name], pred_info["no_value"]
                    )

                    if "past" in station["om_parameters"][pred_name]:
                        station["om_parameters"][pred_name]["past"][time_depth].append(
                            row_value
                        )
                    else:
                        station["om_parameters"][pred_name]["past"] = {
                            time_depth: [row_value]
                        }

            # check
            om_time_prepast, om_parameters = timeline_to_hourly(
                time_depth,
                "prepast",
                station["om_time_range_prepast"],
                station["om_time_prepast"],
                station["om_parameters"],
            )
            station["om_time_prepast"] = om_time_prepast
            station["om_parameters"] = om_parameters

            om_time_past, om_parameters = timeline_to_hourly(
                time_depth,
                "past",
                station["om_time_range_past"],
                station["om_time_past"],
                station["om_parameters"],
            )
            station["om_time_past"] = om_time_past
            station["om_parameters"] = om_parameters

            station["om_time_past"]["recent"] = station["om_time_past"][time_depth][-1]

            station["om_time_future"] = {}
            station["om_time_future"][time_forecast] = [
                station["om_time_past"]["recent"] + datetime.timedelta(hours=hh + 1)
                for hh in range(int(time_forecast[:-1]) * 24)
            ]
            station["om_time_range_future"] = {}
            station["om_time_range_future"] = [
                station["om_time_future"][time_forecast][0],
                station["om_time_future"][time_forecast][-1],
            ]

            for pred_name, pred_info in predictors.items():
                station["om_parameters"][pred_name]["past"]["recent"] = station[
                    "om_parameters"
                ][pred_name]["past"][time_depth][-1]
                # station["om_parameters"][pred_name]["past"]["recent"] = self._fix_value(
                #     rows_past[-1]._mapping[pred_name], pred_info["no_value"]
                # )
        else:
            logging.error(
                "ОШИБКА! Станции с кодом %s в БД не обнаружено!", station["code"]
            )
            return False, station

        return True, station
