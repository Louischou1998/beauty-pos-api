# 美業 POS — FastAPI Backend

## 啟動步驟

```bash
# 1. 建虛擬環境
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Mac/Linux

# 2. 安裝套件
pip install -r requirements.txt

# 3. 複製環境變數
cp .env.example .env
# 修改 .env 填入你的 DB 密碼

# 4. 建立資料表
alembic upgrade head

# 5. 填入初始資料
python seed.py

# 6. 啟動開發伺服器
uvicorn main:app --reload --port 8000
```

## API 文件
啟動後開啟 http://localhost:8000/docs

## 端點總覽
| Method | Path | 說明 |
|--------|------|------|
| GET | /api/v1/staff | 技師列表 |
| POST | /api/v1/staff | 新增技師 |
| PATCH | /api/v1/staff/{id} | 更新技師 |
| DELETE | /api/v1/staff/{id} | 停用技師 |
| GET | /api/v1/customers | 顧客列表 |
| POST | /api/v1/customers | 新增顧客 |
| PATCH | /api/v1/customers/{id} | 更新顧客 |
| POST | /api/v1/customers/{id}/topup | 儲值/加點 |
| GET | /api/v1/bookings?date=YYYY-MM-DD | 預約列表 |
| POST | /api/v1/bookings | 新增預約（含衝突鎖）|
| PATCH | /api/v1/bookings/{id}/status | 更新預約狀態 |
| GET | /api/v1/services | 服務項目列表 |
| POST | /api/v1/services | 新增服務項目 |

## 錯誤回應格式

API 失敗時，`detail` 會回傳結構化資料，格式如下：

```json
{
  "detail": {
    "code": "BOOKING_CONFLICT",
    "message": "Staff has a booking conflict",
    "meta": {
      "staff_id": 2,
      "start_at": "2026-05-08T10:00:00"
    }
  }
}
```

- `code`: 前後端共用的機器可判斷錯誤碼
- `message`: 可讀訊息（前端可再做在地化對照）
- `meta`: 附加診斷資訊（可選）

## 錯誤碼對照

| Code | 說明 |
|------|------|
| `VALIDATION_ERROR` | 請求參數驗證失敗（422） |
| `SERVICE_NOT_FOUND` | 找不到服務項目 |
| `PRODUCT_NOT_FOUND` | 找不到商品資料 |
| `BOOKING_NOT_FOUND` | 找不到預約 |
| `BOOKING_CONFLICT` | 預約時段衝突 |
| `EMPTY_CHECKOUT` | 結帳項目為空 |
| `PAYMENT_TOTAL_MISMATCH` | 付款總額與訂單總額不一致 |
| `INSUFFICIENT_STOCK` | 庫存不足 |
| `NO_AVAILABLE_STAFF` | 無可用技師 |
| `STAFF_NOT_AVAILABLE` | 指定技師不可預約 |

## 審計日誌（Audit Log）

關鍵流程會以 JSON 一行一筆寫入應用程式 log，方便追蹤營運事件：

- `booking.create`
- `booking.update_status`
- `checkout.submit`
- `portal.book`

每筆事件會包含時間、操作者（或 `public`）、角色、關聯訂單/顧客等欄位。
