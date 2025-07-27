from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from .models import Store
from .serializers import StoreSerializer

class StoreViewSet(viewsets.ModelViewSet):
    serializer_class = StoreSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Store.objects.filter(owner=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

class MyStoreView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            store = Store.objects.get(owner=request.user)
            serializer = StoreSerializer(store)
            return Response(serializer.data)
        except Store.DoesNotExist:
            return Response({'error': 'فروشگاهی یافت نشد'}, status=status.HTTP_404_NOT_FOUND)