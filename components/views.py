# components/views.py

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
    """
    محاكاة للتطبيق الخارجي: يستقبل الـ 3 أعمدة ويرد ببيانات الـ Datasheet
    """
    incoming_data = request.data
    mock_response_data = []

    for item in incoming_data:
        mpn = item.get('mpn', 'UNKNOWN')
        man = item.get('man', 'UNKNOWN')
        
        # توليد بيانات وهمية للتجربة
        mock_response_data.append({
            "mpn": mpn,
            "man": man,
            "datasheet_url": f"https://datasheet-server.mock/pdf/{man}/{mpn}.pdf",
            "status": "Verified",
            "lifecycle": "Active"
        })

    return Response(mock_response_data, status=status.HTTP_200_OK)


# --- 2. الوظيفة الرئيسية: رفع الملف، الحفظ، استدعاء الـ API، التحديث، والرد الكامل ---
def upload_and_process_file(request):
    if request.method == 'POST' and request.FILES.get('component_file'):
        uploaded_file = request.FILES['component_file']
        batch_id = str(uuid.uuid4())[:8] # كود فريد لتمييز هذه الرفعة
        
        # قراءة ملف الـ Excel أو الـ CSV
        try:
            if uploaded_file.name.endswith('.xlsx') or uploaded_file.name.endswith('.xls'):
                df = pd.read_excel(uploaded_file)
            else:
                df = pd.read_csv(uploaded_file)
        except Exception as e:
            return JsonResponse({"error": f"Failed to read file: {str(e)}"}, status=400)

        db_records = []
        api_payload = []

        # الخطوة 1: استخراج الأعمدة الـ 3 وحفظها مبدئياً
        for _, row in df.iterrows():
            mpn_val = str(row.get('MPN', '')).strip()
            man_val = str(row.get('MAN', '')).strip()
            desc_val = str(row.get('Description', '')).strip()

            db_records.append(ComponentData(
                mpn=mpn_val, 
                man=man_val, 
                description=desc_val, 
                batch_id=batch_id
            ))
            api_payload.append({"mpn": mpn_val, "man": man_val, "description": desc_val})

        # حفظ البيانات الأولية في الـ Master Table
        ComponentData.objects.bulk_create(db_records)

        # الخطوة 2: إرسال الـ 3 أعمدة إلى الـ API الخارجي (الوهمي)
        mock_api_url = "http://127.0.0.1:8000/api/mock-external/" 
        try:
            response = requests.post(mock_api_url, json=api_payload, timeout=10)
            response_data = response.json()
        except requests.exceptions.RequestException as e:
            return JsonResponse({"error": f"API Call Failed: {str(e)}"}, status=500)

        # الخطوة 3: جلب السجلات المخزنة وتحديثها بالأعمدة الجديدة القادمة من الـ API
        saved_records = ComponentData.objects.filter(batch_id=batch_id)
        records_dict = {f"{r.mpn}_{r.man}": r for r in saved_records}
        
        records_to_update = []

        for api_item in response_data:
            key = f"{api_item.get('mpn')}_{api_item.get('man')}"
            
            if key in records_dict:
                record = records_dict[key]
                # إضافة قيم الأعمدة الجديدة للكائن
                record.datasheet_url = api_item.get('datasheet_url')
                record.status = api_item.get('status')
                record.lifecycle = api_item.get('lifecycle')
                
                records_to_update.append(record)

        # حفظ التحديثات الجديدة في الـ Master Table دفعة واحدة (Bulk Update)
        if records_to_update:
            ComponentData.objects.bulk_update(records_to_update, ['datasheet_url', 'status', 'lifecycle'])

        # الخطوة 4: جلب البيانات كاملة (الأصلية + الجديدة) من قاعدة البيانات مباشرة
        final_data_from_db = ComponentData.objects.filter(batch_id=batch_id).values(
            'id', 'mpn', 'man', 'description', 'datasheet_url', 'status', 'lifecycle'
        )

        # إرسال الاستجابة الكاملة للـ HTML أو كـ JSON
        return JsonResponse({
            "message": "Data imported, enhanced by API, and saved to database successfully.",
            "batch_id": batch_id,
            "data": list(final_data_from_db)
        }, safe=False)

    return render(request, 'upload.html')

        