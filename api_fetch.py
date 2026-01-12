import requests

url = "https://data.moa.gov.tw/Service/OpenData/TransService.aspx?UnitId=LC7YWlenhLuP"

def fetch_crop_data():
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
        # 印出前 3 筆資料確認格式
        print(f"成功抓取 {len(data)} 筆資料，範例：")
        print(data[:3])
    else:
        print("未抓取到任何資料。")