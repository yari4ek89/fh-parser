# parser.py
import requests
from config import API_TOKEN, BASE_URL

HEADERS = {
    "Authorization": f"Bearer {API_TOKEN}",
    "Accept": "application/json"
}

def get_projects():
    """Получить последние проекты Freelancehunt"""
    url = f"{BASE_URL}/projects?page[number]=1&page[size]=20"
    resp = requests.get(url, headers=HEADERS)

    if resp.status_code != 200:
        print("API error:", resp.text)
        return []

    data = resp.json()
    projects = []

    for item in data.get("data", []):
        attrs = item["attributes"]

        p = {
            "id": int(item["id"]),
            "name": attrs["name"],
            "description": attrs["description"],
            "budget": attrs["budget"],
            "published_at": attrs["published_at"],
            "link": item["links"]["self"],
        }
        projects.append(p)

    return projects
