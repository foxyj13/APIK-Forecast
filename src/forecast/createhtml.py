# Arshan Project
import argparse
import sys
from configparser import ConfigParser
import logging
from logging.handlers import TimedRotatingFileHandler
import os

import openpyxl


def init_logging(config):
    log_folder = config['main']['log-folder']
    if not os.path.isdir(log_folder):
        os.mkdir(log_folder)
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s %(levelname)-7s %(module)s.%(funcName)s - %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S',
                        handlers=[
                            TimedRotatingFileHandler(
                                filename=os.path.join(log_folder, 'meteo.log'),
                                when='midnight'
                            ),
                            logging.StreamHandler(sys.stdout)
                        ])


def read_stations(stations_file: str) -> list:
    wb = openpyxl.open(stations_file)
    ws_stations = wb['Станции']
    ws_parameters = wb['Параметры']

    all_parameters = {}
    for par_row_id in range(2, ws_parameters.max_row + 1):
        par_codes = str(ws_parameters[f'B{par_row_id}'].value).split(';')
        for par_code in par_codes:
            all_parameters[par_code] = {
                'name': ws_parameters[f'D{par_row_id}'].value,
                'code': par_code,
                'full_name': ws_parameters[f'A{par_row_id}'].value,
                'short_name': ws_parameters[f'C{par_row_id}'].value,
                'no_value': ws_parameters[f'E{par_row_id}'].value
        }

    stations = []
    for st_row_id in range(2, ws_stations.max_row + 1):
        parameters = []
        par_codes = str(ws_stations[f'C{st_row_id}'].value).split(';')
        for par_code in par_codes:
            parameters.append(all_parameters[par_code.strip()])
        stations.append({
            'full_name': ws_stations[f'A{st_row_id}'].value,
            'code': str(ws_stations[f'B{st_row_id}'].value),
            'parameters': parameters,
            'description': str(ws_stations[f'D{st_row_id}'].value)
        })

    return stations

def main():
    config = ConfigParser()
    config.read(os.path.join(str(os.path.dirname(__file__)), 'config.ini'))
    db_config = config['DB']
    main_config = config['main']

    if not os.path.exists(main_config['log-folder']):
        os.mkdir(main_config['log-folder'])

    if not os.path.exists(main_config['images-folder']):
        os.mkdir(main_config['images-folder'])

    init_logging(config)

    logging.info('Начинаем работу!')

    stations = read_stations(main_config['stations-file'])

    for station in stations:
        if station:
             logging.info(f"Cтанция {station['code']}")
             f = open(f"stn_{station['code']}.html", "w")
             f.write("<html>\n")
             f.write(f"<title>{station['full_name']}</title>\n")
             f.write("<head>\n")
             f.write("</head>\n")
             f.write("<body>\n")
             f.write("<center>\n")
             f.write("<font face='arial'>\n")
             #f.write(f"<h1>{station['full_name']}</h1>\n")
             f.write(f"<h1>{station['description']}</h1>\n")
             f.write("<p>\n")
             f.write(f"<a rel='noopener noreferrer' href='index.html'>\n")
             f.write(f"<-- apik.imces.ru ...\n")
             f.write("</a>\n")
             f.write("<p>\n")
             f.write(f"<a rel='noopener noreferrer' href='stn_{station['code']}_info.html'>\n")
             f.write(f"<-- Инфо о станции {station['full_name']}...\n")
             f.write("</a>\n")
             f.write("</p>\n")
             f.write(f"<img src='meteo/images/{station['code']}_recent.png' alt='Recent'>\n")
             f.write("</p>\n")
             for parameter in station['parameters']:
                 if parameter['code'] != "0":
                     f.write(f"<h3>{parameter['short_name']}</h3>\n")
                     f.write("<p>\n")
                     f.write(f"<a rel='noopener noreferrer' href='meteo/images/{station['code']}_{parameter['code']}_day.png'>\n")
                     f.write(f"<img src='meteo/images/{station['code']}_{parameter['code']}_day.png' width=300>\n")
                     f.write("</a>\n")
                     f.write(f"<a rel='noopener noreferrer' href='meteo/images/{station['code']}_{parameter['code']}_week.png'>\n")
                     f.write(f"<img src='meteo/images/{station['code']}_{parameter['code']}_week.png' width=300>\n")
                     f.write("</a>\n")
                     f.write(f"<a rel='noopener noreferrer' href='meteo/images/{station['code']}_{parameter['code']}_mon.png'>\n")
                     f.write(f"<img src='meteo/images/{station['code']}_{parameter['code']}_mon.png' width=300>\n")
                     f.write("</a>\n")
                     f.write("</p>\n")
                 else:
                     logging.error(f"ОШИБКА! Нет кода: {parameter['code']} для параметра \"{parameter['name']}\"")
             f.write("<hr size='2' width='80%' color='#3366cc'>\n")
             f.write("<p>\n")
             f.write("<a target=_blank href='http://imces.ru/index.php?rm=news&action=view&id=861'> (c) АПИК, 2025 <br> </a>\n")
             f.write("<a href='mailto:apik-imces@mail.ru'> apik-imces@mail.ru </a>\n")
             f.write("</p>\n")

             f.write("</center>\n")
             f.write("</body>\n")
             f.write("</html>\n")
             f.close()
        else:
            logging.warning('Внимание! Какие-то проблемы. Пропускаю станцию.')

    logging.info('Годовые данные') 

    f = open("stn_annual.html", "w") 
    f.write("<html>\n") 
    f.write(f"<title>APIK anual data</title>\n")
    f.write("<head>\n")
    f.write("</head>\n")
    f.write("<body>\n")
    f.write("<center>\n")
    f.write("<font face='arial'>\n")
    f.write("<h1>Сеть гидрометеорологических наблюдений АПИК</h1>\n")
    f.write("<p>\n")
    for station in stations:
         f.write(f"<h2>{station['full_name']}</h2>\n")
         f.write("<p>\n")
         f.write(f"<a rel='noopener noreferrer' href='stn_{station['code']}.html'>\n")
         f.write(f"<-- Данные станции {station['full_name']}...\n")
         f.write("</a>\n")
         f.write("</p>\n")
         for parameter in station['parameters']:
             if parameter['code'] != "0":
                     f.write(f"<h3>{parameter['short_name']}</h3>\n")
                     f.write("<p>\n")
                     f.write(f"<a rel='noopener noreferrer' href='meteo/images/{station['code']}_{parameter['code']}_day.png'>\n")
                     f.write(f"<img src='meteo/images/{station['code']}_{parameter['code']}_day.png' width=300>\n")
                     f.write("</a>\n")
                     f.write(f"<a rel='noopener noreferrer' href='meteo/images/{station['code']}_{parameter['code']}_week.png'>\n")
                     f.write(f"<img src='meteo/images/{station['code']}_{parameter['code']}_week.png' width=300>\n")
                     f.write("</a>\n")
                     f.write(f"<a rel='noopener noreferrer' href='meteo/images/{station['code']}_{parameter['code']}_mon.png'>\n")
                     f.write(f"<img src='meteo/images/{station['code']}_{parameter['code']}_mon.png' width=300>\n")
                     f.write("</a>\n")
                     f.write(f"<a rel='noopener noreferrer' href='meteo/images/{station['code']}_{parameter['code']}_mon.ann'>\n")
                     f.write(f"<img src='meteo/images/{station['code']}_{parameter['code']}_ann.png' width=300>\n")
                     f.write("</a>\n")
                     f.write("</p>\n")
             else:
                 logging.error(f"ОШИБКА! Нет кода: {parameter['code']} для параметра \"{parameter['name']}\"")
         f.write("<hr size='2' width='80%' color='#3366cc'>\n")
    f.write("</center>\n")
    f.write("</font>\n")
    f.write("</body>\n")
    f.write("</html>\n")
    f.close()


    logging.info('Заканчиваем работу')


if __name__ == '__main__':
    main()
