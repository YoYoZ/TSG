
"""
Yasno API Client - Final Working Version
Парсит API https://app.yasno.ua/api/blackout-service/public/shutdowns/regions/{region}/dsos/{dso}/planned-outages
"""

import requests
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class YasnoAPI:
    """Клієнт для роботи з API Yasno"""

    # Константы для Киева
    REGION_ID = "25"  # Киев
    DSO_ID = "902"    # КИЕВЭНЕРГО

    BASE_URL = "https://app.yasno.ua/api/blackout-service/public/shutdowns/regions/{region}/dsos/{dso}/planned-outages"

    def __init__(self, city: str = "kyiv", region_id: str = REGION_ID, dso_id: str = DSO_ID):
        """
        Ініціалізація клієнта

        Args:
            city: Місто (kyiv, dnipro, итд)
            region_id: ID регіону
            dso_id: ID DSO (розподільна компанія)
        """
        self.city = city
        self.region_id = region_id
        self.dso_id = dso_id
        self.url = self.BASE_URL.format(region=region_id, dso=dso_id)

    def get_schedule(self) -> Dict:
        """
        Отримати повний розклад відключень

        Returns:
            Dict з даними про розклад всіх груп
        """
        try:
            logger.info(f"Загружаю расписание с {self.url}")
            response = requests.get(self.url, timeout=10)
            response.raise_for_status()
            data = response.json()
            logger.info("✅ Успешно загружено расписание")
            return data
        except requests.exceptions.RequestException as e:
            logger.error(f"Помилка при отриманні даних від API: {e}")
            raise Exception(f"Помилка при отриманні даних від API: {e}")

    def get_outages_for_group(self, group: str) -> Dict:
        """
        Отримати розклад відключень для конкретної групи

        Args:
            group: Номер групи (наприклад, "1.1", "2.1", "3.1", та ін.)

        Returns:
            Dict з даними про today та tomorrow для конкретної групи
        """
        data = self.get_schedule()

        if group not in data:
            available_groups = list(data.keys())
            raise Exception(
                f"Група {group} не знайдена! "
                f"Доступні групи: {available_groups}"
            )

        group_data = data[group]

        # Структура API:
        # {
        #   "1.1": {
        #     "today": {
        #       "slots": [{"start": 0, "end": 60, "type": "NotPlanned"}, ...]
        #       "date": "2025-11-09T00:00:00+02:00"
        #     },
        #     "tomorrow": {...}
        #   }
        # }

        result = {
            "city": self.city,
            "group": group,
            "today": {
                "title": "Сьогодні",
                "outages": self._extract_definite_outages(group_data.get("today", {}))
            },
            "tomorrow": {
                "title": "Завтра",
                "outages": self._extract_definite_outages(group_data.get("tomorrow", {}))
            }
        }

        return result

    @staticmethod
    def _extract_definite_outages(day_data: Dict) -> List[Dict]:
        """
        Извлечь ТОЛЬКО тип "Definite" отключения (запланированные)
        Пропустить "NotPlanned"

        Args:
            day_data: Данные дня {"slots": [...]}

        Returns:
            Список отключений только типа "Definite" в часах
        """
        if not day_data:
            return []

        slots = day_data.get("slots", [])
        outages = []

        for slot in slots:
            # Берем ТОЛЬКО "Definite" - запланированные отключения
            if slot.get("type") == "Definite":
                start_minutes = slot.get("start", 0)
                end_minutes = slot.get("end", 0)

                # Конвертируем минуты в часы (decimal format)
                start_hour = start_minutes / 60
                end_hour = end_minutes / 60

                outages.append({
                    "start_hour": start_hour,
                    "end_hour": end_hour,
                    "type": "DEFINITE_OUTAGE"
                })

        return outages

    @staticmethod
    def _format_hour(hour: float) -> str:
        """
        Форматувати годину (наприклад, 12.5 -> 12:30)

        Args:
            hour: Година у десятковому форматі

        Returns:
            Відформатований час
        """
        try:
            hours = int(hour)
            minutes = int((hour - hours) * 60)
            return f"{hours:02d}:{minutes:02d}"
        except (ValueError, TypeError):
            return "??:??"


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    try:
        client = YasnoAPI(city="kyiv")

        # Тестируем группу 1.1
        schedule = client.get_outages_for_group(group="1.1")

        print(f"\n✅ Результаты для группы {schedule['group']}:")
        print(f"\nСегодня ({schedule['today']['title']}):")
        for outage in schedule['today']['outages']:
            start = client._format_hour(outage['start_hour'])
            end = client._format_hour(outage['end_hour'])
            print(f"  Отключение: {start} - {end}")

        print(f"\nЗавтра ({schedule['tomorrow']['title']}):")
        for outage in schedule['tomorrow']['outages']:
            start = client._format_hour(outage['start_hour'])
            end = client._format_hour(outage['end_hour'])
            print(f"  Отключение: {start} - {end}")

    except Exception as e:
        print(f"❌ Помилка: {e}")
        import traceback
        traceback.print_exc()
