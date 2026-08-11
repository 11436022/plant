from update_reference_data import build_reference_data


def test_build_reference_data_filters_and_labels_official_records():
    existing = {
        "crops": [
            {"crop_name": "番茄", "crop_name_en": "Tomato"},
            {"crop_name": "茉莉花_薰芬茶用", "crop_name_en": None},
        ],
        "diseases": [
            {
                "crop_name": None,
                "disease_name": "水分過多",
                "description": "舊資料",
                "treatment": "舊建議",
            }
        ],
        "pests": [],
    }
    pest_rows = [
        {
            "ID": "diag-1",
            "PestName_Ch": "粉蝨",
            "PestName_Scientific": "Aleyrodidae",
            "Crop_Name": "番茄",
            "Harm_leaf": "Y",
            "Image": "https://data.moa.gov.tw/pest/diag-1",
        }
    ]
    tree_rows = [
        {
            "CaseName": "褐根病",
            "TreeType": "榕樹",
            "Injury_Type": "病害",
            "DiagnosisMethod": "樣本檢驗",
            "symptom": "根部腐朽",
            "Injury_Description": "植株萎凋",
            "Advice": "使用10%藥劑稀釋1000倍後噴灑",
        },
        {
            "CaseName": "褐根病",
            "TreeType": "不知名樹",
            "Injury_Type": "病害",
            "DiagnosisMethod": "樣本檢驗",
            "symptom": "不明症狀",
            "Advice": "不明建議",
        },
        {
            "CaseName": "葉斑病",
            "TreeType": "榕樹",
            "Injury_Type": "病害",
            "DiagnosisMethod": "資料判讀",
            "symptom": "葉片斑點",
            "Advice": "修剪病葉",
        },
    ]

    updated, summary = build_reference_data(existing, pest_rows, tree_rows)

    assert {crop["crop_name"] for crop in updated["crops"]} == {
        "番茄",
        "榕樹",
        "茉莉花_薰芬茶用",
    }
    assert summary["official_diseases"] == 1
    assert summary["official_pests"] == 1

    disease = next(row for row in updated["diseases"] if row.get("crop_name") == "榕樹")
    assert disease["disease_name"] == "褐根病"
    assert disease["source_record_id"].startswith("tree-")
    assert "不直接回傳該舊處方" in disease["treatment"]

    pest = updated["pests"][0]
    assert pest["pest_name"] == "粉蝨"
    assert pest["source_record_id"] == "diag-1"
    assert pest["source_url"] == "https://data.moa.gov.tw/pest/diag-1"
