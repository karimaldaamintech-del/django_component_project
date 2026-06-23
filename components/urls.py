from django.urls import path
from .views import upload_and_process_file, mock_external_api

urlpatterns = [
    path('upload/', upload_and_process_file, name='upload_file'),
    path('api/mock-external/', mock_external_api, name='mock_api'),
]