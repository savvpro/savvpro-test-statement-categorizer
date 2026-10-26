from django.urls import path
from .views import upload_statement

urlpatterns = [
    path('api/upload/', upload_statement, name='upload_statement'),
]