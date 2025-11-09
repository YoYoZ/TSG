
"""
Debug version to understand the intersection logic
"""

from typing import List, Dict, Tuple


class ScheduleAnalyzerDebug:
    """Debug version for understanding intersections"""

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

    @classmethod
    def get_outage_intervals(cls, outages: List[Dict]) -> List[Tuple[int, int]]:
        """Get outage intervals in minutes"""
        intervals = []
        for outage in outages:
            start = cls.convert_hour_to_minutes(outage.get("start_hour", 0))
            end = cls.convert_hour_to_minutes(outage.get("end_hour", 0))
            intervals.append((start, end))
        return sorted(intervals)

    @classmethod
    def get_electricity_periods(cls, outages: List[Dict]) -> List[Tuple[int, int]]:
        """Get periods when electricity IS AVAILABLE"""
        outage_intervals = cls.get_outage_intervals(outages)

        if not outage_intervals:
            return [(0, 24 * 60)]

        periods = []

        # Before first outage
        if outage_intervals[0][0] > 0:
            periods.append((0, outage_intervals[0][0]))

        # Gaps between outages
        for i in range(len(outage_intervals) - 1):
            gap_start = outage_intervals[i][1]
            gap_end = outage_intervals[i + 1][0]
            if gap_start < gap_end:
                periods.append((gap_start, gap_end))

        # After last outage
        if outage_intervals[-1][1] < 24 * 60:
            periods.append((outage_intervals[-1][1], 24 * 60))

        return periods

    @classmethod
    def debug_schedules(cls, schedules: List[Dict]):
        """Print debug info about all schedules"""
        print("\n" + "="*80)
        print("DEBUG: ELECTRICITY PERIODS FOR EACH USER")
        print("="*80)

        all_user_periods = []

        for schedule in schedules:
            username = schedule["username"]
            group = schedule["group"]
            outages = schedule.get("outages", [])

            print(f"\n{username} (группа {group}):")
            print(f"  Отключения (outages):")

            outage_intervals = cls.get_outage_intervals(outages)
            for start, end in outage_intervals:
                print(f"    {cls.minutes_to_hhmm(start)} - {cls.minutes_to_hhmm(end)}")

            electricity_periods = cls.get_electricity_periods(outages)
            print(f"  Когда есть свет (ЗЕЛЕНЫЕ ЗОНЫ):")
            for start, end in electricity_periods:
                print(f"    ✅ {cls.minutes_to_hhmm(start)} - {cls.minutes_to_hhmm(end)}")

            all_user_periods.append({
                "username": username,
                "periods": electricity_periods
            })

        # Now find intersections
        print("\n" + "="*80)
        print("DEBUG: FINDING INTERSECTIONS")
        print("="*80)

        if len(all_user_periods) < 2:
            print("Недостаточно пользователей для пересечения")
            return

        # Start with first user
        common = set()
        first_user = all_user_periods[0]
        print(f"\nНачинаем с {first_user['username']}:")
        for start, end in first_user['periods']:
            print(f"  {cls.minutes_to_hhmm(start)} - {cls.minutes_to_hhmm(end)}")
            common.add((start, end))

        # Intersect with others
        for user_data in all_user_periods[1:]:
            username = user_data["username"]
            print(f"\nПересекаем с {username}:")

            new_common = set()

            for common_start, common_end in common:
                print(f"  Проверяем диапазон {cls.minutes_to_hhmm(common_start)} - {cls.minutes_to_hhmm(common_end)}:")

                for user_start, user_end in user_data["periods"]:
                    overlap_start = max(common_start, user_start)
                    overlap_end = min(common_end, user_end)

                    if overlap_start < overlap_end:
                        print(f"    ✅ Пересечение: {cls.minutes_to_hhmm(overlap_start)} - {cls.minutes_to_hhmm(overlap_end)}")
                        new_common.add((overlap_start, overlap_end))
                    else:
                        print(f"    ❌ Нет пересечения с {cls.minutes_to_hhmm(user_start)} - {cls.minutes_to_hhmm(user_end)}")

            common = new_common
            print(f"  Результат: {len(common)} периодов")

        print("\n" + "="*80)
        print(f"ФИНАЛЬНЫЙ РЕЗУЛЬТАТ: {len(common)} периодов")
        print("="*80)
        if common:
            for start, end in sorted(common):
                print(f"  ✅ {ScheduleAnalyzerDebug.minutes_to_hhmm(start)} - {ScheduleAnalyzerDebug.minutes_to_hhmm(end)}")
        else:
            print("  ❌ Нет пересечений")

        return common


# Test with example data
if __name__ == "__main__":
    # Example: Anton and Danilo from the chat
    schedules = [
        {
            "username": "Anton",
            "group": "3.1",
            "outages": [
                {"start_hour": 1.5, "end_hour": 5},      # 01:30 - 05:00
                {"start_hour": 12, "end_hour": 15.5},    # 12:00 - 15:30
                {"start_hour": 22.5, "end_hour": 24}     # 22:30 - 24:00
            ]
        },
        {
            "username": "Данія",
            "group": "6.1",
            "outages": [
                {"start_hour": 0, "end_hour": 1.5},      # 00:00 - 01:30
                {"start_hour": 8.5, "end_hour": 12},     # 08:30 - 12:00
                {"start_hour": 19, "end_hour": 22.5}     # 19:00 - 22:30
            ]
        }
    ]

    ScheduleAnalyzerDebug.debug_schedules(schedules)
