from fastapi import FastAPI
import os
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials

app = FastAPI()

# අදාළ මාසය සහ අවුරුද්ද (දැනට අගෝස්තු 2026 ලෙස ගෙන ඇත, පසුව මෙය Dynamic කළ හැක)
TARGET_YEAR = "2026"
TARGET_MONTH = "August"

def get_gspread_client():
    # Vercel Environment Variables වලින් Google JSON කේතය ලබාගැනීම
    creds_json = os.environ.get("GOOGLE_SHEETS_CREDENTIALS")
    if not creds_json:
        raise ValueError("Google Sheets Credentials not found in Environment Variables")
    
    creds_dict = json.loads(creds_json)
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    return gspread.authorize(creds)

def safe_float(val):
    try:
        if val == "" or val is None or val == "-": return 0.0
        return float(str(val).replace(',', '').strip())
    except:
        return 0.0

@app.get("/api/kpi")
def get_kpi_data():
    try:
        gc = get_gspread_client()
        
        # ඔයාගේ Streamlit ඇප් එකේ පාවිච්චි කළ Sheet Links දෙක
        sh1 = gc.open_by_url("https://docs.google.com/spreadsheets/d/1TWSwwcEElojBnoqY_hPllfb3l9xn1_9ed4Xy4FQdq98/edit") # Sales data
        sh2 = gc.open_by_url("https://docs.google.com/spreadsheets/d/1xO3xNDYkC-97BHksfiq9BRpJ9rDP9_snTzTLP-sJbMg/edit") # Sales data2
        
        # 1. Issued Qty ලබාගැනීම
        issued_qty_records = sh2.worksheet("Issued_Qty").get_all_records(default_blank="")
        total_issued = sum(safe_float(r.get("Issued Qty", 0)) for r in issued_qty_records if str(r.get("Year")) == TARGET_YEAR and str(r.get("Month")) == TARGET_MONTH)
        
        # 2. Sales Return ලබාගැනීම
        sales_return_records = sh2.worksheet("Sales_Return").get_all_records(default_blank="")
        total_sales_return = sum(safe_float(r.get("Return Amount", 0)) for r in sales_return_records if str(r.get("Year")) == TARGET_YEAR and str(r.get("Month")) == TARGET_MONTH)
        
        # 3. Shop Return ලබාගැනීම
        shop_return_records = sh2.worksheet("Shop_Return").get_all_records(default_blank="")
        total_shop_return = sum(safe_float(r.get("Return Amount", 0)) for r in shop_return_records if str(r.get("Year")) == TARGET_YEAR and str(r.get("Month")) == TARGET_MONTH)
        
        # 4. Actual Sales (Sold Qty) ලබාගැනීම
        sales_day_book_records = sh2.worksheet("Sales_day_book").get_all_records(default_blank="")
        total_sold = 0
        for r in sales_day_book_records:
            date_str = str(r.get("new_date", "") or r.get("Date", ""))
            # Date එක 2026-08 වලින් පටන් ගන්නවා නම් එකතු කරන්න
            if date_str.startswith(f"{TARGET_YEAR}-08"): 
                total_sold += safe_float(r.get("Qty", 0))

        # 5. Forecast Sales ලබාගැනීම
        forecast_records = sh1.worksheet("Forecast").get_all_records(default_blank="")
        total_forecast = sum(safe_float(r.get("Forecast Qty", 0)) for r in forecast_records if str(r.get("Year")) == TARGET_YEAR and str(r.get("Month")) == TARGET_MONTH)
        
        # ==========================================
        # 🧮 KPI Calculations (According to Document)
        # ==========================================
        
        # KPI 1: Sales Return Rate (Target < 4%)
        sales_return_rate = (total_sales_return / total_issued * 100) if total_issued > 0 else 0
        
        # KPI 2: Shop Return Rate (Target < 1%)
        shop_return_rate = (total_shop_return / total_sold * 100) if total_sold > 0 else 0
        
        # KPI 3: Forecast Accuracy (Target > 98%)
        if total_sold > 0:
            variance_abs = abs(total_sold - total_forecast)
            forecast_accuracy = (1 - (variance_abs / total_sold)) * 100
        else:
            forecast_accuracy = 0
            
        # ==========================================
        # 📊 Return JSON Data to Frontend
        # ==========================================
        data = {
            "salesReturnRate": round(sales_return_rate, 2),
            "salesReturnKg": round(total_sales_return, 2),
            "issuedKg": round(total_issued, 2),
            
            "shopReturnRate": round(shop_return_rate, 2),
            "shopReturnKg": round(total_shop_return, 2),
            "soldKg": round(total_sold, 2),
            
            "forecastAccuracy": round(forecast_accuracy, 2),
            "actualSales": round(total_sold, 2),
            "forecastSales": round(total_forecast, 2),
            
            # (ප්‍රස්ථාර සඳහා දැනට දත්ත බෙදීම - අවශ්‍ය නම් මෙයද සජීවීව සකස් කළ හැක)
            "weeklyReturnTrend": {
                "labels": ['Week 1', 'Week 2', 'Week 3', 'Week 4'],
                "salesReturn": [total_sales_return * 0.2, total_sales_return * 0.3, total_sales_return * 0.25, total_sales_return * 0.25],
                "shopReturn": [total_shop_return * 0.2, total_shop_return * 0.3, total_shop_return * 0.25, total_shop_return * 0.25]
            },
            "weeklyForecastTrend": {
                "labels": ['Week 1', 'Week 2', 'Week 3', 'Week 4'],
                "actual": [total_sold * 0.2, total_sold * 0.3, total_sold * 0.25, total_sold * 0.25],
                "forecast": [total_forecast * 0.25, total_forecast * 0.25, total_forecast * 0.25, total_forecast * 0.25]
            }
        }
        
        return data

    except Exception as e:
        # දෝෂයක් ආවොත් බලාගන්න
        return {"error": str(e)}