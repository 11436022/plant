import httpx
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

router = APIRouter(tags=["Weather"])

# 台灣縣市列表
TAIWAN_CITIES = [
    "臺北市", "新北市", "桃園市", "臺中市", "臺南市", "高雄市",
    "基隆市", "新竹市", "嘉義市", "新竹縣", "苗栗縣", "彰化縣",
    "南投縣", "雲林縣", "嘉義縣", "屏東縣", "宜蘭縣", "花蓮縣",
    "臺東縣", "澎湖縣", "金門縣", "連江縣"
]

# 氣象局API相關設定
CWB_API_URL = "https://opendata.cwa.gov.tw/api/v1/rest/datastore/F-C0032-001"
# 您需要在.env中設定CWB_API_KEY

class WeatherData(BaseModel):
    location: str
    weather: str
    temperature: str
    rain_probability: str
    update_time: str

class PlantCareAdvice(BaseModel):
    location: str
    current_weather: WeatherData
    watering_advice: str
    disease_prevention_advice: str
    general_care: str

@router.get("/cities", response_model=List[str])
async def get_taiwan_cities():
    """獲取台灣所有縣市列表"""
    return TAIWAN_CITIES

@router.get("/current", response_model=WeatherData)
async def get_current_weather(
    city: str = Query(..., description="台灣縣市名稱，例如：臺北市"),
    api_key: Optional[str] = None
):
    """獲取指定城市的當前天氣數據（使用中央氣象署開放資料）"""
    if city not in TAIWAN_CITIES:
        raise HTTPException(status_code=400, detail=f"不支援的城市：{city}，請選擇台灣的縣市")
    
    # 從環境變量獲取API金鑰（優先級高於參數）
    from app.core.config import settings
    cwb_api_key = settings.CWB_API_KEY if hasattr(settings, 'CWB_API_KEY') else api_key
    
    if not cwb_api_key:
        raise HTTPException(status_code=500, detail="未設定中央氣象署API金鑰，請在.env中設定CWB_API_KEY")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                CWB_API_URL,
                params={"Authorization": cwb_api_key, "locationName": city}
            )
            response.raise_for_status()
            data = response.json()
            
            if "records" not in data or "location" not in data["records"]:
                raise HTTPException(status_code=500, detail="氣象資料格式錯誤")
            
            location_data = data["records"]["location"][0]
            weather_elements = {elem["elementName"]: elem["time"][0]["parameter"] for elem in location_data["weatherElement"]}
            
            return WeatherData(
                location=city,
                weather=weather_elements["Wx"]["parameterName"],
                temperature=f"{weather_elements['MinT']['parameterName']}~{weather_elements['MaxT']['parameterName']}°C",
                rain_probability=f"{weather_elements['PoP']['parameterName']}%",
                update_time=data["records"]["datasetDescription"]
            )
            
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=500, detail=f"無法取得天氣資料：{str(e)}")

@router.get("/plant-care-advice", response_model=PlantCareAdvice)
async def get_plant_care_advice(city: str = Query(..., description="台灣縣市名稱，例如：臺北市")):
    """根據天氣提供植物照護建議"""
    weather_data = await get_current_weather(city)
    
    # 解析天氣數據
    rain_prob = int(weather_data.rain_probability.replace("%", ""))

    # 澆水建議
    if rain_prob > 60:
        watering_advice = "降雨機率高，暫時不需要澆水，請留意土壤濕度"
    elif "晴" in weather_data.weather:
        watering_advice = "天氣晴朗，植物水分蒸散可能較快，請確保充足澆水"
    elif "雨" in weather_data.weather:
        watering_advice = "天氣為雨天，可暫停澆水，並注意盆栽排水"
    else:
        watering_advice = "天氣條件適中，按照一般規律澆水即可"

    # 病害預防建議
    if rain_prob > 70:
        disease_prevention_advice = "高降雨機率可能導致高濕度，容易引發黴菌病害，請保持通風"
    elif "晴" in weather_data.weather:
        disease_prevention_advice = "天氣乾燥，請注意紅蜘蛛等蟲害，可適度對葉片噴霧增加濕度"
    else:
        disease_prevention_advice = "天氣條件適中，維持日常觀察即可"
    
    # 一般照護建議
    if "晴" in weather_data.weather:
        general_care = "陽光充足，適合植物生長，但需注意劇烈日照可能灼傷葉片，適當遮陽"
    elif "雨" in weather_data.weather:
        general_care = "雨天請注意排水，避免積水導致根部腐爛，可暫停戶外植物的澆水"
    else:
        general_care = "多雲或陰天，光線較弱，可適當調整植物位置增加光照"
    
    return PlantCareAdvice(
        location=city,
        current_weather=weather_data,
        watering_advice=watering_advice,
        disease_prevention_advice=disease_prevention_advice,
        general_care=general_care
    )