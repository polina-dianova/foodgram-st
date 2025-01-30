from django.urls import  path
from .views import recipe_redirect


urlpatterns = [
    path('s/int:short_id>/', recipe_redirect, name='recipe_redirect')
]