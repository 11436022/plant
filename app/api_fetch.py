import requests

# 農業部開放資料 API 端點。
url = "https://data.moa.gov.tw/Service/OpenData/TransService.aspx?UnitId=LC7YWlenhLuP"


def fetch_crop_data():
    """向開放資料平台抓取作物清單。"""

    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Error fetching data: {e}")
        return None


if __name__ == "__main__":
    data = fetch_crop_data()
    if data:
        # 僅印出前 3 筆資料，方便快速確認內容。
        print(f"總共取得 {len(data)} 筆資料。")
        print(data[:3])
    else:
        print("無法取得作物資料。")
