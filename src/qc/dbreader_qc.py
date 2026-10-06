from bisect import bisect_left, bisect_right
import datetime
import logging

from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import NoResultFound
from timezonefinder import TimezoneFinder
from zoneinfo import ZoneInfo


class DBReaderQC:
    def __init__(self, server, port, user, password, database):
        self.server = server
        self.port = port
        self.user = user
        self.password = password
        self.database = database

        self.meta = None
        self.session = None

        self.timezone_obj = TimezoneFinder()

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

    # station_parameters = {
    #     <par_name>: {"code", "full_name", "no_value", "om_parameter",
    #                 "obs": [float, ...],
    #                 "local": {"past": {<now_date>: {"data": [float, ...], "timeline":[datetime, ...]}, ...}
    #                         "future": {<now_date>: {"data": [float, ...], "timeline":[datetime, ...]}, ...}},
    #                 "global": {"past": {<now_date>: {"data": [float, ...], "timeline":[datetime, ...]}, ...}
    #                         "future": {<now_date>: {"data": [float, ...], "timeline":[datetime, ...]}, ...}}
    #     }
    #  obs_timeline = [datetime, ...] # сгенерирован нужный

    @staticmethod
    def _timeline_to_hourly(
        timeline_ref: list, par_name: str, timeline_orig: list, data_orig: list
    ) -> list:

        timeline_timestamp_ref = [time_val.timestamp() for time_val in timeline_ref]
        timeline_timestamp_orig = [time_val.timestamp() for time_val in timeline_orig]

        data_to_hourly = []

        if par_name == "prc":
            # Для осадков используем накопление (сумму) за предыдущий час, а не ближайшее значение
            for t in timeline_ref:
                start_time = t - datetime.timedelta(hours=1)
                end_time = t

                # Используем бинарный поиск для поиска индексов элементов,
                # которые попадают строго в интервал (start_time, end_time]
                idx_start = bisect_right(timeline_orig, start_time)
                idx_end = bisect_right(timeline_orig, end_time)

                # Считаем сумму элементов, попавших в этот диапазон индексов
                # Если в интервале (T - 1 час, T] данных нет (например, в кейсе с редкой записью),
                # то idx_start и idx_end совпадут, срез вернет пустой список, а функция sum() вернет 0.0
                sub_data_orig = [
                    x for x in data_orig[idx_start:idx_end] if x is not None
                ]
                if sub_data_orig:
                    hourly_sum = float(sum(sub_data_orig))
                else:
                    hourly_sum = None

                data_to_hourly.append(hourly_sum)
        else:
            # Для остальных параметров используем ближайшее значение в интервале получаса до и после от отметки времени
            for t in timeline_ref:
                start_time = t - datetime.timedelta(minutes=29)
                end_time = t + datetime.timedelta(minutes=30)

                idx_start = bisect_right(timeline_orig, start_time)
                idx_end = bisect_right(timeline_orig, end_time)

                # sub_data_orig = data_orig[idx_start:idx_end]
                sub_data_orig = [
                    x for x in data_orig[idx_start:idx_end] if x is not None
                ]

                if sub_data_orig:
                    sub_timeline_orig = [
                        timeline_orig[idx] for idx in range(idx_start, idx_end)
                    ]
                    diff_timeline = [abs(x - t) for x in sub_timeline_orig]

                    min_idx = diff_timeline.index(min(diff_timeline))

                    hourly_data = float(sub_data_orig[min_idx])

                    # print(f"{t}: ({start_t}, {end_t}]: {sub_timeline_orig}")
                else:
                    hourly_data = None

                data_to_hourly.append(hourly_data)

        return data_to_hourly

    def get_data(
        self,
        station_code: str,
        station_lat: float,
        station_lon: float,
        station_parameters: dict,
        obs_timeline_ref: list,
    ) -> dict:

        logging.info(
            "Считывание наблюдений из БД (замена уже записанных в словарь) для станции %s",
            station_code,
        )

        # Определяем диапазон дат для запроса данных из БД
        date_range_to_get = [
            obs_timeline_ref[0].date() - datetime.timedelta(days=1),
            obs_timeline_ref[-1].date() + datetime.timedelta(days=2),
        ]

        station_timezone_str = self.timezone_obj.timezone_at(
            lng=station_lon, lat=station_lat
        )

        start_date = datetime.datetime.combine(
            date_range_to_get[0],
            datetime.time.min,
            tzinfo=ZoneInfo(station_timezone_str),
        )
        utc_start_stamp = start_date.timestamp()
        utc_start_date = datetime.datetime.fromtimestamp(
            utc_start_stamp, tz=datetime.timezone.utc
        )

        end_date = datetime.datetime.combine(
            date_range_to_get[-1],
            datetime.time.max,
            tzinfo=ZoneInfo(station_timezone_str),
        )
        utc_end_stamp = end_date.timestamp()
        utc_end_date = datetime.datetime.fromtimestamp(
            utc_end_stamp, tz=datetime.timezone.utc
        )

        # Получаем данные наблюдений из БД для каждой переменной
        st_parameters = station_parameters

        if self.meta and self.session and station_code in self.meta.tables:
            data_tbl = self.meta.tables[station_code]
            qry = self.session.query(data_tbl.columns["timezone"].label("timezone"))
            qry = qry.add_columns(data_tbl.columns["time"].label("time"))

            for par_name, par_info in st_parameters.items():
                if par_info["code"] in data_tbl.columns.keys():
                    qry = qry.add_columns(
                        data_tbl.columns[par_info["code"]].label(par_name)
                    )
                else:
                    logging.info(
                        'Нет кода: %s для параметра "%s"', par_info["code"], par_name
                    )

            qry = qry.select_from(data_tbl)
            qry_f = qry.filter(
                data_tbl.columns["time"] >= utc_start_stamp,
                data_tbl.columns["time"] <= utc_end_stamp,
            )
            try:
                rows = qry_f.all()
            except NoResultFound:
                logging.error("ОШИБКА! В БД не найдено ни одного результата!")
                #!!!!!return {}

            station_timeshift = datetime.timedelta(hours=rows[0].timezone)

            obs_timeline_db = []
            obs_data_db = {par_name: [] for par_name in st_parameters.keys()}

            for row in rows:
                row_time = (
                    datetime.datetime.fromtimestamp(row.time, tz=datetime.timezone.utc)
                    + station_timeshift
                )
                obs_timeline_db.append(row_time)

                for par_name in st_parameters.keys():
                    row_value = self._fix_value(
                        row._mapping[par_name], st_parameters[par_name]["no_value"]
                    )
                    obs_data_db[par_name].append(row_value)

            # Преобразовать данные наблюдений из БД в почасовой формат
            for par_name in st_parameters.keys():
                obs_data_hourly = self._timeline_to_hourly(
                    obs_timeline_ref, par_name, obs_timeline_db, obs_data_db[par_name]
                )
                st_parameters[par_name]["obs"] = obs_data_hourly

        return st_parameters
