import datetime
import logging
import time

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
                "recent": datetime.datetime.fromtimestamp(
                    rows[-1].time, tz=datetime.timezone.utc
                )
                + station_timeshift,
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
            for parameter in station["parameters"].values():
                parameter["data"]["recent"] = self._fix_value(
                    rows[-1]._mapping[parameter["name"]], parameter["no_value"]
                )
        else:
            logging.error(
                "ОШИБКА! Станции с кодом %s в БД не обнаружено!", station["code"]
            )
            return {}
        return result
