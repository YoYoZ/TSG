
"""
Yasno Web Parser - парсит информацию со статического сайта Yasno
"""

import requests
from typing import Dict, List, Optional
import logging
import json
import re
from datetime import datetime

logger = logging.getLogger(__name__)


class YasnoWebParser:
    """Парсер сайта Yasno для получения запланованных отключений"""

    BASE_URL = "https://static.yasno.ua/{city}/outages"

    def __init__(self, city: str = "kyiv"):
        """
        Ініціалізація парсера

        Args:
            city: Місто (kyiv, dnipro, kharkiv, итд)
        """
        self.city = city.lower()
        self.url = self.BASE_URL.format(city=city)

    def get_schedule_json(self) -> Optional[Dict]:
        """
        Получить JSON с расписанием со статического сайта

        Returns:
            Dict с данными расписания или None если ошибка
        """
        try:
            logger.info(f"Загружаю расписание с {self.url}")
            response = requests.get(self.url, timeout=15)
            response.raise_for_status()

            # Попытаемся распарить как JSON
            data = response.json()
            logger.info("✅ Успешно загружено расписание")
            return data

        except requests.exceptions.JSONDecodeError:
            logger.warning("Ответ не JSON, пробуем HTML парсинг")
            return self._parse_html(response.text)

        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка при загрузке: {e}")
            return None

    def _parse_html(self, html: str) -> Optional[Dict]:
        """
        Парсить HTML если это не JSON

        Args:
            html: HTML контент

        Returns:
            Dict с извлеченными данными
        """
        try:
            # Ищем JSON в скриптах
            json_matches = re.findall(r'<script[^>]*>(.*?)</script>', html, re.DOTALL)

            for script_content in json_matches:
                # Ищем объекты с данными о расписании
                if 'schedule' in script_content.lower() or 'outages' in script_content.lower():
                    try:
                        # Очищаем от комментариев
                        cleaned = re.sub(r'//.*?$', '', script_content, flags=re.MULTILINE)
                        data = json.loads(cleaned)
                        logger.info("✅ Найдены данные в HTML")
                        return data
                    except json.JSONDecodeError:
                        continue

            logger.warning("Не удалось найти JSON в HTML")
            return None

        except Exception as e:
            logger.error(f"Ошибка при парсинге HTML: {e}")
            return None

    def get_outages_for_group(self, group: str) -> Dict:
        """
        Получить отключения для конкретной группы

        Args:
            group: Номер группы (например, "1.1")

        Returns:
            Dict с расписанием на сегодня и завтра
        """
        data = self.get_schedule_json()

        if not data:
            raise Exception(f"Не удалось загрузить расписание для {self.city}")

        # Предполагаем структуру: {"groups": {"1.1": [...]}}
        # или {"schedule": {"group_1.1": [...]}}
        # или другая структура

        # Ищем данные группы
        group_data = self._find_group_data(data, group)

        if not group_data:
            available = self._get_available_groups(data)
            raise Exception(
                f"Группа {group} не найдена. "
                f"Доступные группы: {available}"
            )

        # Определяем текущий день
        today_idx = datetime.now().weekday()
        tomorrow_idx = (today_idx + 1) % 7

        result = {
            "city": self.city,
            "group": group,
            "today": {
                "title": "Сьогодні",
                "outages": self._extract_outages(group_data, today_idx)
            },
            "tomorrow": {
                "title": "Завтра",
                "outages": self._extract_outages(group_data, tomorrow_idx)
            }
        }

        return result

    @staticmethod
    def _find_group_data(data: Dict, group: str) -> Optional[List]:
        """
        Найти данные группы в структуре данных

        Args:
            data: Полные данные со статического сайта
            group: Номер группы

        Returns:
            Данные группы или None
        """
        # Вариант 1: {"group_1.1": [...]}
        if f"group_{group}" in data:
            return data[f"group_{group}"]

        # Вариант 2: {"groups": {"1.1": [...]}}
        if "groups" in data and group in data["groups"]:
            return data["groups"][group]

        # Вариант 3: {"schedule": {"group_1.1": [...]}}
        if "schedule" in data and f"group_{group}" in data["schedule"]:
            return data["schedule"][f"group_{group}"]

        # Вариант 4: {"schedule": {"groups": {"1.1": [...]}}}
        if "schedule" in data and "groups" in data["schedule"] and group in data["schedule"]["groups"]:
            return data["schedule"]["groups"][group]

        return None

    @staticmethod
    def _get_available_groups(data: Dict) -> List[str]:
        """
        Получить список доступных групп

        Args:
            data: Полные данные

        Returns:
            Список групп
        """
        groups = []

        # Вариант 1
        for key in data.keys():
            if key.startswith("group_"):
                groups.append(key.replace("group_", ""))

        # Вариант 2
        if "groups" in data:
            groups.extend(list(data["groups"].keys()))

        # Вариант 3 и 4
        if "schedule" in data:
            for key in data["schedule"].keys():
                if key.startswith("group_"):
                    groups.append(key.replace("group_", ""))
            if "groups" in data["schedule"]:
                groups.extend(list(data["schedule"]["groups"].keys()))

        return list(set(groups))  # Remove duplicates

    @staticmethod
    def _extract_outages(group_data: List, day_idx: int) -> List[Dict]:
        """
        Извлечь отключения для конкретного дня

        Args:
            group_data: Данные группы (массив по дням)
            day_idx: Индекс дня (0-6)

        Returns:
            Список отключений
        """
        if not isinstance(group_data, list) or day_idx >= len(group_data):
            return []

        day_data = group_data[day_idx]

        if not isinstance(day_data, list):
            return []

        # Парсим отключения
        outages = []
        for item in day_data:
            if isinstance(item, dict):
                outages.append({
                    "start_hour": item.get("start", 0),
                    "end_hour": item.get("end", 0),
                    "type": item.get("type", "POSSIBLE_OUTAGE")
                })
            elif isinstance(item, (list, tuple)) and len(item) >= 2:
                outages.append({
                    "start_hour": float(item[0]),
                    "end_hour": float(item[1]),
                    "type": "POSSIBLE_OUTAGE"
                })

        return outages

    def format_outages(self, outages_data: Dict) -> str:
        """Форматировать отключения"""
        result = []
        result.append(f"Місто: {outages_data['city'].upper()}")
        result.append(f"Група: {outages_data['group']}")
        result.append("")

        for period_name in ["today", "tomorrow"]:
            period = outages_data[period_name]
            result.append(f"{period['title']}: {len(period['outages'])} відключень")
            for outage in period["outages"]:
                start = self._format_hour(outage["start_hour"])
                end = self._format_hour(outage["end_hour"])
                result.append(f"  {start} - {end}")

        return "\n".join(result)

    @staticmethod
    def _format_hour(hour: float) -> str:
        """Форматировать час"""
        try:
            hours = int(hour)
            minutes = int((hour - hours) * 60)
            return f"{hours:02d}:{minutes:02d}"
        except:
            return "??:??"


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    try:
        parser = YasnoWebParser(city="kyiv")
        schedule = parser.get_outages_for_group(group="1.1")
        print(parser.format_outages(schedule))
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
