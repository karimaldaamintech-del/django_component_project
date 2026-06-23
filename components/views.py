import pandas as pd
import requests
import uuid
from django.shortcuts import render
from django.http import JsonResponse
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .models import ComponentData

# --- 1. الـ API الوهمي (Mock API) لتجربة الـ Datasheet ---
@api_view(['POST'])
def mock_external_api(request):
    incoming_data = request.data
    mock_response_data = []

    for item in incoming_data:
        mpn = item.get('mpn', 'UNKNOWN')
        man = item.get('man', 'UNKNOWN')
        
        # بنرجع بيانات وهمية للتجربة
        mock_response_data.append({
            "mpn": mpn,
            "man": man,
            "datasheet_url": f"https://datasheet-server.mock/pdf/{man}/{mpn}.pdf",
            "status": "Verified",
            "lifecycle": "Active"
        })

    return Response(mock_response_data, status=status.HTTP_200_OK)


# --- 2. صفحة الرفع والـ Process والدمج (Join) ---
def upload_and_process_file(request):
    if request.method == 'POST' and request.FILES.get('component_file'):
        uploaded_file = request.FILES['component_file']
        batch_id = str(uuid.uuid4())[:8] # كود مميز لكل عملية رفع
        
        # قراءة الملف (سواء Excel أو CSV)
        try:
            if uploaded_file.name.endswith('.xlsx') or uploaded_file.name.endswith('.xls'):
                df = pd.read_excel(uploaded_file)
            else:
                df = pd.read_csv(uploaded_file)
        except Exception as e:
            return JsonResponse({"error": f"Failed to read file: {str(e)}"}, status=400)

        db_records = []
        api_payload = []

        # قراءة البيانات وتجهيزها
        for _, row in df.iterrows():
            mpn_val = str(row.get('MPN', '')).strip()
            man_val = str(row.get('MAN', '')).strip()
            desc_val = str(row.get('Description', '')).strip()

            db_records.append(ComponentData(
                mpn=mpn_val, man=man_val, description=desc_val, batch_id=batch_id
            ))

            api_payload.append({"mpn": mpn_val, "man": man_val, "description": desc_val})

        # حفظ البيانات دفعة واحدة في الداتا البيز
        ComponentData.objects.bulk_create(db_records)

        # إرسال البيانات للـ API الوهمي
        mock_api_url = "http://127.0.0.1:8000/api/mock-external/" 
        try:
            response = requests.post(mock_api_url, json=api_payload, timeout=10)
            response_data = response.json()
        except requests.exceptions.RequestException as e:
            return JsonResponse({"error": f"API Call Failed: {str(e)}"}, status=500)

        # دمج النتيجة (Join) مع البيانات الأصلية من الداتا بيز
        final_joined_result = []
        saved_records = ComponentData.objects.filter(batch_id=batch_id).values('id', 'mpn', 'man', 'description')
        records_dict = {f"{r['mpn']}_{r['man']}": r for r in saved_records}

        for api_item in response_data:
            key = f"{api_item.get('mpn')}_{api_item.get('man')}"
            if key in records_dict:
                original_row = records_dict[key]
                final_joined_result.append({
                    "database_id": original_row['id'],
                    "mpn": original_row['mpn'],
                    "man": original_row['man'],
                    "description": original_row['description'],
                    "datasheet_url": api_item.get('datasheet_url'),
                    "status": api_item.get('status'),
                    "lifecycle": api_item.get('lifecycle')
                })

        return JsonResponse({
            "message": "Success",
            "batch_id": batch_id,
            "data": final_joined_result
        }, safe=False)

    return render(request, 'upload.html')

# Create your views here.
