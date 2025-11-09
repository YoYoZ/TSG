
"""
Schedule analysis module - COMPLETELY FIXED
Модуль для аналізу пересічень графіків відключень
"""

from typing import List, Dict, Tuple


class ScheduleAnalyzer:
    """Analyzer for finding schedule intersections"""

    @staticmethod
    def convert_hour_to_minutes(hour: float) -> int:
        """Convert decimal hour to minutes since midnight"""
        hours = int(hour)
        minutes = int((hour - hours) * 60)
        return hours * 60 + minutes

    @staticmethod
    def minutes_to_hhmm(minutes: int) -> str:
        """Convert minutes to HH:MM format"""
        hours = minutes // 60
        mins = minutes % 60
        return f"{hours:02d}:{mins:02d}"

    @staticmethod
    def minutes_to_hm(minutes: int) -> str:
        """Convert minutes to H:MM or HH format"""
        hours = minutes // 60
        mins = minutes % 60
        if mins == 0:
            return f"{hours}"
        return f"{hours}:{mins:02d}"

    @classmethod
    def get_outage_intervals(cls, outages: List[Dict]) -> List[Tuple[int, int]]:
        """Convert outages to intervals in minutes"""
        intervals = []
        for outage in outages:
            start = cls.convert_hour_to_minutes(outage.get("start_hour", 0))
            end = cls.convert_hour_to_minutes(outage.get("end_hour", 0))
            intervals.append((start, end))
        return sorted(intervals)

    @classmethod
    def get_electricity_periods(cls, outages: List[Dict]) -> List[Tuple[int, int]]:
        """
        Get periods when electricity IS AVAILABLE

        API дает ОТКЛЮЧЕНИЯ (outages), нам нужны ВКЛЮЧЕНИЯ (electricity periods)

        Пример:
        Входные отключения: 00-1.5, 8.5-12, 19-22.5
        Выходной свет:      01:30-08:30, 12:00-19:00, 22:30-24:00
        """
        outage_intervals = cls.get_outage_intervals(outages)

        if not outage_intervals:
            # No outages - electricity available all day
            return [(0, 24 * 60)]

        # Инвертируем: между отключениями - свет!
        electricity_periods = []

        # СВЕТ ДО первого отключения
        if outage_intervals[0][0] > 0:
            electricity_periods.append((0, outage_intervals[0][0]))

        # СВЕТ МЕЖДУ отключениями
        for i in range(len(outage_intervals) - 1):
            gap_start = outage_intervals[i][1]  # Конец первого отключения
            gap_end = outage_intervals[i + 1][0]  # Начало второго отключения
            if gap_start < gap_end:
                electricity_periods.append((gap_start, gap_end))

        # СВЕТ ПОСЛЕ последнего отключения
        if outage_intervals[-1][1] < 24 * 60:
            electricity_periods.append((outage_intervals[-1][1], 24 * 60))

        return electricity_periods

    @classmethod
    def find_common_electricity_periods(
        cls, 
        schedules: List[Dict]
    ) -> Tuple[List[Tuple[int, int]], List[Dict]]:
        """
        Find time periods when electricity is available for ALL users
        """
        if not schedules:
            return [], []

        if len(schedules) == 1:
            periods = cls.get_electricity_periods(schedules[0].get("outages", []))
            return periods, []

        # Собираем ВСЕ временные точки
        all_points = set([0, 24 * 60])

        for schedule in schedules:
            periods = cls.get_electricity_periods(schedule.get("outages", []))
            for start, end in periods:
                all_points.add(start)
                all_points.add(end)

        all_points = sorted(list(all_points))

        # Для каждого интервала проверяем: у ВСЕХ ли есть свет?
        common_periods = []

        for i in range(len(all_points) - 1):
            point = all_points[i]
            next_point = all_points[i + 1]

            # Проверяем каждого пользователя
            all_have_power = True
            for schedule in schedules:
                electricity_periods = cls.get_electricity_periods(schedule.get("outages", []))

                # Есть ли свет в этот момент?
                has_power = False
                for start, end in electricity_periods:
                    if start <= point < end:
                        has_power = True
                        break

                if not has_power:
                    all_have_power = False
                    break

            # Если у ВСЕХ есть свет в этом интервале - добавляем
            if all_have_power:
                if common_periods and common_periods[-1][1] == point:
                    # Расширяем предыдущий период
                    common_periods[-1] = (common_periods[-1][0], next_point)
                else:
                    # Создаем новый период
                    common_periods.append((point, next_point))

        return common_periods, []

    @classmethod
    def find_n_minus_one_periods(
        cls,
        schedules: List[Dict]
    ) -> List[Dict]:
        """
        Find periods when electricity is available for all users EXCEPT ONE
        """
        if len(schedules) < 2:
            return []

        results = []

        for excluded_idx, excluded_schedule in enumerate(schedules):
            excluded_user_id = excluded_schedule["user_id"]
            excluded_username = excluded_schedule["username"]

            # Отключения для исключенного пользователя
            excluded_outages = cls.get_outage_intervals(
                excluded_schedule.get("outages", [])
            )

            # Общий свет для остальных
            other_schedules = schedules[:excluded_idx] + schedules[excluded_idx+1:]
            common_periods, _ = cls.find_common_electricity_periods(other_schedules)

            # Ищем пересечение: у остальных СВЕТ + у исключенного ОТКЛЮЧЕНИЕ
            for other_start, other_end in common_periods:
                for outage_start, outage_end in excluded_outages:
                    overlap_start = max(other_start, outage_start)
                    overlap_end = min(other_end, outage_end)

                    if overlap_start < overlap_end:
                        results.append({
                            "missing_user_id": excluded_user_id,
                            "missing_username": excluded_username,
                            "start": overlap_start,
                            "end": overlap_end,
                            "start_hhmm": cls.minutes_to_hhmm(overlap_start),
                            "end_hhmm": cls.minutes_to_hhmm(overlap_end),
                            "duration_minutes": overlap_end - overlap_start
                        })

        return results

    @classmethod
    def format_report(cls, day_name: str, common_periods: List[Tuple[int, int]]) -> str:
        """Format common periods into readable report"""
        if not common_periods:
            return f"{day_name}: ❌ Нет времени, когда у всех свет одновременно"

        lines = [f"{day_name}: ✅"]
        for start, end in common_periods:
            start_str = cls.minutes_to_hm(start)
            end_str = cls.minutes_to_hm(end)
            lines.append(f"  З {start_str} до {end_str}")

        return "\n".join(lines)
