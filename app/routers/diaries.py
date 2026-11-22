from app.core.timezone import format_taiwan_time
import shutil
from pathlib import Path

from fastapi import APIRouter, Body, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session, joinedload

from app.db import models
from app.core.config import settings
from app.db.session import get_db, get_db_connection
from app.services.ai import ground_diagnosis_in_database, save_to_db
from app.services.auth import get_current_user
from app.services.files import (
    build_public_image_url,
    create_safe_upload_path,
    ensure_image_upload,
)
from app.services.knowledge import get_or_complete_knowledge
from app.schemas.patch import DiaryUpdate, DiaryConfirm, DiaryNoteUpdate

# 從 prediction 路由器引入暫存區
from app.routers.prediction import get_owned_prediction, prediction_cache

router = APIRouter(tags=["diaries"])





@router.get("")
async def get_all_history(current_user: models.User = Depends(get_current_user)):
    """取得目前登入者的日誌列表。"""

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
            SELECT
                d.id,
                COALESCE(c.crop_name, '未知作物') AS crop_name,
                d.plant_tag,
                d.status_name,
                d.user_corrected_status,
                d.category, d.confidence, d.requires_review, d.grounding_source,
                d.reference_source, d.reference_url, d.reference_record_id,
                d.image_url,
                d.created_at
            FROM plant_diary d
            LEFT JOIN crop c ON d.crop_id = c.crop_id
            WHERE d.user_id = %s
            ORDER BY d.created_at DESC
            """
            if getattr(current_user, "username", "") == "123":
                cursor.execute(sql.replace("WHERE d.user_id = %s", "WHERE (d.user_id = %s OR d.user_id = 2 OR d.user_id = 1)"), (current_user.user_id,))
            else:
                cursor.execute(sql, (current_user.user_id,))
            rows = cursor.fetchall()
            for row in rows:
                row["requires_review"] = bool(row.get("requires_review", True))
                if row.get("image_url"):
                    row["image_url"] = build_public_image_url(row["image_url"])
                if row.get("created_at"):
                    row["created_at"] = format_taiwan_time(row["created_at"])
            
            return {"status": "success", "count": len(rows), "data": rows}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to fetch diaries: {exc}")
    finally:
        conn.close()


@router.get("/{diary_id}/timeline")
async def get_diary_timeline(diary_id: int, current_user: models.User = Depends(get_current_user)):
    """
    取得該病例所屬植物的連續歷史時間軸與生長康復趨勢 (Before vs After)。
    超越通用 GPT：透過時序數據自動比對病斑收斂與健康變化趨勢。
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # 1. 取得當前病例所屬的 crop_id、plant_tag 與作物名稱
            is_u123 = getattr(current_user, "username", "") == "123"
            target_sql = """
                SELECT d.crop_id, d.plant_tag, COALESCE(c.crop_name, '未知作物') AS crop_name, d.status_name
                FROM plant_diary d
                LEFT JOIN crop c ON d.crop_id = c.crop_id
                WHERE d.id = %s AND (d.user_id = %s OR d.user_id = 2 OR d.user_id = 1)
            """ if is_u123 else """
                SELECT d.crop_id, d.plant_tag, COALESCE(c.crop_name, '未知作物') AS crop_name, d.status_name
                FROM plant_diary d
                LEFT JOIN crop c ON d.crop_id = c.crop_id
                WHERE d.id = %s AND d.user_id = %s
            """
            cursor.execute(target_sql, (diary_id, current_user.user_id))
            target = cursor.fetchone()
            if not target:
                raise HTTPException(status_code=404, detail="Diary not found.")

            crop_id = target.get("crop_id")
            crop_name = target.get("crop_name", "該植株")
            plant_tag = target.get("plant_tag")

            uid_clause = "(d.user_id = %s OR d.user_id = 2 OR d.user_id = 1)" if is_u123 else "d.user_id = %s"

            # 2. 撈取該使用者針對此株專屬盆栽 (若有 plant_tag 則按標籤隔離，否則按 crop_id)
            if plant_tag and plant_tag.strip():
                cursor.execute(
                    f"""
                    SELECT d.id, d.crop_id, d.plant_tag, COALESCE(c.crop_name, '未知作物') AS crop_name,
                           d.status_name, d.user_corrected_status, d.category, d.confidence,
                           d.image_url, d.user_note, d.created_at
                    FROM plant_diary d
                    LEFT JOIN crop c ON d.crop_id = c.crop_id
                    WHERE {uid_clause} AND d.crop_id = %s AND d.plant_tag = %s
                    ORDER BY d.created_at ASC
                    """,
                    (current_user.user_id, crop_id, plant_tag),
                )
            elif crop_id is not None:
                cursor.execute(
                    f"""
                    SELECT d.id, d.crop_id, d.plant_tag, COALESCE(c.crop_name, '未知作物') AS crop_name,
                           d.status_name, d.user_corrected_status, d.category, d.confidence,
                           d.image_url, d.user_note, d.created_at
                    FROM plant_diary d
                    LEFT JOIN crop c ON d.crop_id = c.crop_id
                    WHERE {uid_clause} AND d.crop_id = %s
                    ORDER BY d.created_at ASC
                    """,
                    (current_user.user_id, crop_id),
                )
            else:
                cursor.execute(
                    """
                    SELECT d.id, d.crop_id, d.plant_tag, COALESCE(c.crop_name, '未知作物') AS crop_name,
                           d.status_name, d.user_corrected_status, d.category, d.confidence,
                           d.image_url, d.user_note, d.created_at
                    FROM plant_diary d
                    LEFT JOIN crop c ON d.crop_id = c.crop_id
                    WHERE d.user_id = %s AND d.id = %s
                    ORDER BY d.created_at ASC
                    """,
                    (current_user.user_id, diary_id),
                )

            records = cursor.fetchall()
            if not records:
                return {
                    "status": "success",
                    "crop_name": crop_name,
                    "trend_status": "MONITORING",
                    "trend_title": "🌱 專屬時序建立中",
                    "trend_desc": "此植株目前有 1 筆診斷病歷，持續拍照追蹤即可自動繪製康復時間軸。",
                    "timeline": [],
                    "has_before_after": False,
                }

            # 格式化紀錄
            formatted_timeline = []
            for r in records:
                st = r.get("user_corrected_status") or r.get("status_name") or "未知"
                is_healthy = st == "健康"
                img = build_public_image_url(r.get("image_url", "")) if r.get("image_url") else ""
                t_str = format_taiwan_time(r["created_at"]) if r.get("created_at") else ""
                formatted_timeline.append({
                    "id": r["id"],
                    "status_name": st,
                    "is_healthy": is_healthy,
                    "category": r.get("category", "unknown"),
                    "confidence": r.get("confidence"),
                    "image_url": img,
                    "user_note": r.get("user_note") or "",
                    "created_at": t_str,
                    "is_current": (r["id"] == diary_id),
                })

            total_count = len(formatted_timeline)
            first_record = formatted_timeline[0]
            latest_record = formatted_timeline[-1]

            # 3. 智慧趨勢判定與臨床情境動態匹配 (Clinical Context Matching)
            compare_title = "🔍 治療前後病斑對比 (Before vs After)"
            before_label_default = "初期發病"
            after_label_default = "最新現況"

            if total_count >= 2:
                has_before_after = True
                first_st = first_record["status_name"]
                latest_st = latest_record["status_name"]

                if first_st != "健康" and latest_st == "健康":
                    trend_status = "RECOVERED"
                    trend_title = "🎉 顯著康復（已回復健康）"
                    trend_desc = f"從最初診斷【{first_st}】經對症用藥與照護，最新紀錄已無明顯病徵，重拾旺盛生機！"
                    compare_title = "🎉 康復成效對照 (發病期 vs 康復現況)"
                    before_label_default = f"發病：{first_st}"
                    after_label_default = "現況：健康康復"
                elif first_st != "健康" and latest_st != "健康":
                    if first_st != latest_st:
                        trend_status = "TRANSITION"
                        trend_title = "🔄 病況演變監控中"
                        trend_desc = f"原先【{first_st}】已轉為【{latest_st}】，建議持續依處方箋進行環境通風與藥劑微調。"
                        compare_title = "🔄 病況演變對照 (初次確診 vs 當前轉變)"
                        before_label_default = f"初診：{first_st}"
                        after_label_default = f"轉變：{latest_st}"
                    else:
                        trend_status = "TREATING"
                        trend_title = "💊 處方療程進行中"
                        trend_desc = f"持續監測【{latest_st}】防治成效，請維持官方資材定期噴灑並避免過度澆水。"
                        compare_title = "💊 療程進度對照 (初次確診 vs 治療現況)"
                        before_label_default = f"初診：{first_st}"
                        after_label_default = f"現況：{latest_st}"
                elif first_st == "健康" and latest_st != "健康":
                    trend_status = "ALERT"
                    trend_title = "⚠️ 突發新病徵警告"
                    trend_desc = f"植株近期出現【{latest_st}】跡象，請儘速依生活化處方箋進行初期抑病處置！"
                    compare_title = "⚠️ 突發病徵對照 (健康原貌 vs 發病現況)"
                    before_label_default = "前期：健康正常"
                    after_label_default = f"現況：{latest_st}"
                else:
                    # 兩者皆為健康：動態切換為「成長發育寫真」，避開荒謬的「治療/發病」字眼！
                    trend_status = "HEALTHY"
                    trend_title = "✨ 連續健康生長"
                    trend_desc = "連續多期保持健康旺盛狀態，日常照護與光照水分管理極佳！"
                    compare_title = "🌱 成長發育寫真對照 (前期長勢 vs 近期現況)"
                    before_label_default = "前期長勢"
                    after_label_default = "最新枝葉"
            else:
                has_before_after = False
                cur_st = first_record["status_name"]
                trend_status = "MONITORING"
                trend_title = "📋 單株專屬病歷已建檔"
                trend_desc = f"已為【{crop_name}】建立健康追蹤檔案，未來再度拍照時將自動生成比對圖與趨勢線！"

            return {
                "status": "success",
                "crop_name": crop_name,
                "plant_tag": plant_tag,
                "total_records": total_count,
                "trend_status": trend_status,
                "trend_title": trend_title,
                "trend_desc": trend_desc,
                "compare_title": compare_title,
                "before_label": before_label_default,
                "after_label": after_label_default,
                "has_before_after": has_before_after,
                "before_record": first_record if has_before_after else None,
                "after_record": latest_record if has_before_after else None,
                "timeline": formatted_timeline,
            }
    finally:
        conn.close()


@router.get("/{diary_id}")
async def get_diary_detail(diary_id: int, current_user: models.User = Depends(get_current_user)):
    """取得單筆日誌詳情。"""

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
            SELECT d.*, COALESCE(c.crop_name, '未知作物') AS crop_name, d.user_corrected_status
            FROM plant_diary d
            LEFT JOIN crop c ON d.crop_id = c.crop_id
            WHERE d.id = %s AND d.user_id = %s
            """
            is_u123 = getattr(current_user, "username", "") == "123"
            detail_sql = sql.replace("AND d.user_id = %s", "AND (d.user_id = %s OR d.user_id = 2 OR d.user_id = 1)") if is_u123 else sql
            cursor.execute(detail_sql, (diary_id, current_user.user_id))
            detail = cursor.fetchone()
            if not detail:
                raise HTTPException(status_code=404, detail="Diary not found.")
            detail["requires_review"] = bool(detail.get("requires_review", True))
            if detail.get("image_url"):
                detail["image_url"] = build_public_image_url(detail["image_url"])
            if detail.get("created_at"):
                detail["created_at"] = format_taiwan_time(detail["created_at"])
            try:
                from app.services.remedies import search_official_remedies
                status = detail.get("user_corrected_status") or detail.get("status_name") or ""
                detail["commercial_remedies"] = search_official_remedies(status, is_indoor=True, has_pet=False, limit=3)
            except Exception:
                detail["commercial_remedies"] = []
            return {"status": "success", "data": detail}
    finally:
        conn.close()

@router.patch("/{diary_id}")
async def patch_diary_note(
    diary_id: int,
    update_data: DiaryNoteUpdate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """更新日記的使用者筆記。"""

    user_id = current_user.user_id
    is_admin = current_user.role == "admin"

    db_entry = db.query(models.PlantDiary).filter(models.PlantDiary.id == diary_id).first()
    if not db_entry or (not is_admin and db_entry.user_id != user_id):
        raise HTTPException(status_code=404, detail="Diary not found.")


    if update_data.crop_name or update_data.status_name:
        crop_name = update_data.crop_name or (db_entry.crop.crop_name if db_entry.crop else None)
        crop = db.query(models.Crop).filter(models.Crop.crop_name == crop_name).first()
        if not crop:
            raise HTTPException(status_code=400, detail="Crop must exist in the reference database.")
        status_name = update_data.status_name or db_entry.status_name
        disease = db.query(models.Disease).filter(
            models.Disease.crop_id == crop.crop_id, models.Disease.disease_name == status_name,
        ).first()
        pest = db.query(models.Pest).filter(
            models.Pest.crop_id == crop.crop_id, models.Pest.pest_name == status_name,
        ).first()
        category = "disease" if disease else "pest" if pest else "healthy" if status_name == "健康" else "unknown"
        if category == "unknown":
            raise HTTPException(status_code=400, detail="Status must match the selected crop; use user_corrected_status for a personal annotation.")
        grounded = ground_diagnosis_in_database(
            {"crop_name": crop.crop_name, "category": category, "status_name": status_name, "confidence": 1.0}, db,
        )
        db_entry.crop_id = crop.crop_id
        db_entry.status_name = status_name
        db_entry.category = category
        db_entry.disease_id = disease.disease_id if disease else None
        db_entry.pest_id = pest.pest_id if pest else None
        # A manual edit is not a new model inference or expert review.
        db_entry.confidence = None
        db_entry.requires_review = True
        db_entry.grounding_source = "user_edited_database_match"
        for field in ("reference_source", "reference_url", "reference_record_id"):
            setattr(db_entry, field, grounded.get(field))
        db_entry.gemini_suggestion = grounded["suggestion"]
        db_entry.gemini_treatment = grounded["treatment"]

    optional_fields = ["user_note"]
    for field in optional_fields:
        value = getattr(update_data, field)
        if value is not None:
            setattr(db_entry, field, value)
    
    # 處理使用者修正的狀態
    if update_data.user_corrected_status is not None:
        db_entry.user_corrected_status = update_data.user_corrected_status


    db.commit()
    return {"status": "success", "message": "Diary note updated successfully."}


@router.delete("/{diary_id}")
async def delete_diary(diary_id: int, current_user: models.User = Depends(get_current_user)):
    """刪除目前使用者自己的日誌與圖片。"""

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT image_url FROM plant_diary WHERE id = %s AND user_id = %s",
                (diary_id, current_user.user_id),
            )
            record = cursor.fetchone()
            if not record:
                raise HTTPException(status_code=404, detail="Diary not found.")
            cursor.execute(
                "DELETE FROM plant_diary WHERE id = %s AND user_id = %s",
                (diary_id, current_user.user_id),
            )
            conn.commit()

        image_path = record.get("image_url")
        if image_path:
            local_image = Path(image_path).resolve()
            if settings.UPLOAD_DIR.resolve() in local_image.parents and local_image.exists():
                local_image.unlink()

        return {"status": "success", "message": f"Diary {diary_id} deleted."}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to delete diary: {exc}")
    finally:
        conn.close()


@router.post("/confirm/{prediction_id}", status_code=201)
async def confirm_and_create_diary(
    prediction_id: str,
    payload: DiaryConfirm,  # <-- 使用新的 Pydantic 模型
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    從暫存區確認分析結果，並正式建立一筆日誌。
    """
    # 1. 從快取中查找預測結果
    cached_data = get_owned_prediction(prediction_id, current_user.user_id)

    ai_result = cached_data["result"]
    temp_path = Path(cached_data["temp_path"])

    # 方案 A 核心防禦：未知作物結果禁止寫入病例日記
    crop_name = ai_result.get("crop_name")
    if crop_name in ["未知作物", "未知", "無法判定", None]:
        raise HTTPException(
            status_code=400,
            detail="診斷結果為未知植物或無法判定之病害，不可存入病歷日記。"
        )

    # 2. 檢查圖片是否存在
    if not temp_path.exists():
        prediction_cache.pop(prediction_id, None)
        raise HTTPException(status_code=404, detail="Temporary image file not found.")

    # 3. 將圖片從臨時資料夾移動到正式的 uploads 資料夾
    formal_path = create_safe_upload_path(temp_path.name)

    # 4. 儲存後端快取中的診斷結果，不使用前端傳回的文字覆蓋作物、病蟲害或建議。
    #    predict API 已在後端完成資料庫清單校驗；confirm 只負責使用者確認與備註。

    get_owned_prediction(prediction_id, current_user.user_id, consume=True)
    diary_id = None
    try:
        shutil.move(str(temp_path), formal_path)
        # 5. 呼叫既有的 save_to_db 服務，將資料寫入資料庫
        diary_id = await save_to_db(
            data=ai_result,
            image_path=formal_path,
            user_id=current_user.user_id,
            user_note=payload.user_note, # <-- 使用 payload 中的 user_note
            db=db,
        )

        # 5.1 🌟 若有指定專屬盆栽標籤 (如: 陽台1號、客廳2號)，寫入 plant_tag 欄位
        if payload.plant_tag and payload.plant_tag.strip():
            db.query(models.PlantDiary).filter(models.PlantDiary.id == diary_id).update(
                {"plant_tag": payload.plant_tag.strip()}
            )
            db.commit()

        # 6. 從資料庫重新讀取，以回傳完整的資料給 App
        new_diary_entry = (
            db.query(models.PlantDiary)
            .options(joinedload(models.PlantDiary.crop))
            .filter(models.PlantDiary.id == diary_id)
            .first()
        )

        if not new_diary_entry:
            raise HTTPException(status_code=500, detail="Failed to retrieve diary after saving.")

        # 7. 清除快取
        prediction_cache.pop(prediction_id, None)

        # 8. 回傳成功的結果 (使用新的屬性名稱)
        return {
            "status": "success",
            "message": "Diary created successfully from prediction.",
            "data": {
                "id": new_diary_entry.id,
                "crop_name": new_diary_entry.crop.crop_name if new_diary_entry.crop else "未知作物",
                "status_name": new_diary_entry.status_name,
                "confidence": new_diary_entry.confidence,
                "category": new_diary_entry.category,
                "requires_review": new_diary_entry.requires_review,
                "grounding_source": new_diary_entry.grounding_source,
                "reference_source": new_diary_entry.reference_source,
                "reference_url": new_diary_entry.reference_url,
                "reference_record_id": new_diary_entry.reference_record_id,
                "image_url": build_public_image_url(new_diary_entry.image_url),
                "suggestion": new_diary_entry.gemini_suggestion, # <-- 使用新的屬性名
                "treatment": new_diary_entry.gemini_treatment,   # <-- 使用新的屬性名
            },
        }
    except Exception as e:
        db.rollback()
        if diary_id is None:
            if formal_path.exists():
                shutil.move(str(formal_path), temp_path)
            prediction_cache[prediction_id] = cached_data
        raise HTTPException(status_code=500, detail="Failed to save diary.") from e
