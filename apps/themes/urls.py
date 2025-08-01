from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ThemeCategoryViewSet, ThemeViewSet, StoreThemeViewSet, ThemeRatingViewSet

router = DefaultRouter()
router.register(r'categories', ThemeCategoryViewSet)
router.register(r'themes', ThemeViewSet)
router.register(r'store-themes', StoreThemeViewSet, basename='storetheme')
router.register(r'ratings', ThemeRatingViewSet, basename='themerating')

urlpatterns = [
    path('', include(router.urls)),
]
