from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from .models import ThemeCategory, Theme, StoreTheme, ThemeRating
from .serializers import (
    ThemeCategorySerializer, ThemeSerializer, ThemeDetailSerializer,
    StoreThemeSerializer, StoreThemeCreateSerializer,
    ThemeRatingSerializer, ThemeRatingCreateSerializer
)


class ThemeCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """Theme categories - read only"""
    queryset = ThemeCategory.objects.filter(is_active=True)
    serializer_class = ThemeCategorySerializer
    permission_classes = [permissions.AllowAny]
    ordering = ['display_order', 'name_fa']


class ThemeViewSet(viewsets.ReadOnlyModelViewSet):
    """Theme browsing and details"""
    queryset = Theme.objects.filter(is_active=True)
    permission_classes = [permissions.AllowAny]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['category', 'theme_type', 'compatibility', 'is_featured']
    search_fields = ['name', 'name_fa', 'description']
    ordering_fields = ['name_fa', 'price', 'usage_count', 'rating_average']
    ordering = ['-is_featured', '-usage_count']
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ThemeDetailSerializer
        return ThemeSerializer
    
    @action(detail=True, methods=['post'])
    def download(self, request, pk=None):
        """Track theme downloads"""
        theme = self.get_object()
        theme.increment_downloads()
        return Response({'message': 'دانلود ثبت شد'})
    
    @action(detail=False)
    def featured(self, request):
        """Get featured themes"""
        themes = self.queryset.filter(is_featured=True)[:10]
        serializer = self.get_serializer(themes, many=True)
        return Response(serializer.data)
    
    @action(detail=False)
    def popular(self, request):
        """Get popular themes by usage"""
        themes = self.queryset.order_by('-usage_count')[:10]
        serializer = self.get_serializer(themes, many=True)
        return Response(serializer.data)


class StoreThemeViewSet(viewsets.ModelViewSet):
    """Store theme management"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return StoreTheme.objects.filter(store=self.request.user.store)
    
    def get_serializer_class(self):
        if self.action == 'create':
            return StoreThemeCreateSerializer
        return StoreThemeSerializer
    
    @action(detail=False)
    def active(self, request):
        """Get currently active theme"""
        try:
            active_theme = self.get_queryset().get(is_active=True)
            serializer = self.get_serializer(active_theme)
            return Response(serializer.data)
        except StoreTheme.DoesNotExist:
            return Response({
                'message': 'هیچ قالب فعالی یافت نشد'
            }, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """Activate a theme"""
        store_theme = self.get_object()
        
        # Deactivate all other themes
        self.get_queryset().update(is_active=False)
        
        # Activate this theme
        store_theme.is_active = True
        store_theme.save()
        
        return Response({'message': 'قالب فعال شد'})
    
    @action(detail=True, methods=['post'])
    def customize(self, request, pk=None):
        """Update theme customizations"""
        store_theme = self.get_object()
        
        # Update customization fields
        custom_colors = request.data.get('custom_colors', {})
        custom_css = request.data.get('custom_css', '')
        layout_config = request.data.get('layout_config', {})
        font_selections = request.data.get('font_selections', {})
        
        store_theme.custom_colors.update(custom_colors)
        store_theme.custom_css = custom_css
        store_theme.layout_config.update(layout_config)
        store_theme.font_selections.update(font_selections)
        
        store_theme.save()
        
        serializer = self.get_serializer(store_theme)
        return Response(serializer.data)


class ThemeRatingViewSet(viewsets.ModelViewSet):
    """Theme ratings and reviews"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        if self.action == 'list':
            # Show all approved ratings for browsing
            theme_id = self.request.query_params.get('theme')
            if theme_id:
                return ThemeRating.objects.filter(
                    theme_id=theme_id, is_approved=True
                ).order_by('-created_at')
            return ThemeRating.objects.filter(is_approved=True).order_by('-created_at')
        else:
            # Show user's own ratings
            return ThemeRating.objects.filter(store=self.request.user.store)
    
    def get_serializer_class(self):
        if self.action == 'create':
            return ThemeRatingCreateSerializer
        return ThemeRatingSerializer
