from django.shortcuts import render
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .brain import process_statement

@api_view(['POST'])
def upload_statement(request):
    if 'file' not in request.FILES:
        return Response({"error": "No file provided"}, status=400)
    
    file_obj = request.FILES['file']
    if not file_obj.name.endswith('.csv'):
        return Response({"error": "Only CSV files are allowed"}, status=400)
    
    try:
        data = process_statement(file_obj)
        return Response({"data": data}, status=200)
    except Exception as e:
        return Response({"error": str(e)}, status=500)
