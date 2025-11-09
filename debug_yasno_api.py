
"""
Debug utility for Yasno API
Утиліта для відлагодження та розуміння структури API Yasno
"""

import requests
import json
from datetime import datetime


def debug_yasno_api():
    """Отримати та вивести повну структуру API відповіді"""

    API_URL = "https://api.yasno.com.ua/api/v1/pages/home/schedule-turn-off-electricity"

    try:
        print("🔍 Отримую дані з API Yasno...")
        response = requests.get(API_URL, timeout=10)
        response.raise_for_status()

        data = response.json()

        print("\n✅ API відповідь отримана!\n")

        # Вивести повну структуру
        print("="*80)
        print("ПОВНА СТРУКТУРА API:")
        print("="*80)
        print(json.dumps(data, indent=2, ensure_ascii=False)[:5000])
        print("... (скорочено)\n")

        # Проаналізувати структуру
        print("="*80)
        print("АНАЛІЗ СТРУКТУРИ:")
        print("="*80)

        if "components" in data:
            print(f"✓ Знайдено {len(data['components'])} компонентів")

            for idx, component in enumerate(data["components"]):
                print(f"\nКомпонент {idx}:")
                print(f"  - template_name: {component.get('template_name')}")
                print(f"  - keys: {list(component.keys())}")

                if "dailySchedule" in component:
                    daily_schedule = component["dailySchedule"]
                    print(f"  - cities in dailySchedule: {list(daily_schedule.keys())}")

                    if "kiev" in daily_schedule:
                        kiev_data = daily_schedule["kiev"]
                        print(f"    - Kiev keys: {list(kiev_data.keys())}")

                        if "today" in kiev_data:
                            today = kiev_data["today"]
                            print(f"    - Today keys: {list(today.keys())}")

                            if "groups" in today:
                                groups = today["groups"]
                                print(f"    - Groups: {list(groups.keys())[:5]}... (total: {len(groups)})")

                                # Показати приклад групи
                                first_group_key = list(groups.keys())[0]
                                first_group_data = groups[first_group_key]
                                print(f"\n    - Приклад групи '{first_group_key}':")
                                print(f"      {json.dumps(first_group_data, indent=6, ensure_ascii=False)[:500]}")

        print("\n" + "="*80)
        print("УСПІШНИЙ ВІДЛАД!")
        print("="*80)

        return data

    except requests.exceptions.RequestException as e:
        print(f"❌ Помилка при запиті до API: {e}")
        return None


if __name__ == "__main__":
    data = debug_yasno_api()
