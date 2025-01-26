from django.db.models import OuterRef, Exists
from django_filters import rest_framework
from recipe.models import ShoppingCart, Favorite, Recipe


class RecipeFilter(rest_framework.FilterSet):
    is_in_shopping_cart = rest_framework.BooleanFilter(method='filter_is_in_shopping_cart')
    is_favorited = rest_framework.BooleanFilter(method='filter_is_favorited')

    class Meta:
        model = Recipe
        fields = ['name', 'author']

    def filter_is_in_shopping_cart(self, queryset, name, value):
        """Фильтрация по наличию в корзине"""
        if self.request.user.is_authenticated:
            shopping_cart_subquery = ShoppingCart.objects.filter(
                user=self.request.user,
                recipe=OuterRef('pk')
            )
            if value:
                return queryset.filter(Exists(shopping_cart_subquery))
            else:
                return queryset.exclude(Exists(shopping_cart_subquery))
        return queryset  

    def filter_is_favorited(self, queryset, name, value):
        """Фильтрация по наличию в избранном"""
        if self.request.user.is_authenticated:
            favorite_subquery = Favorite.objects.filter(
                user=self.request.user,
                recipe=OuterRef('pk')
            )
            if value:
                return queryset.filter(Exists(favorite_subquery))
            else:
                return queryset.exclude(Exists(favorite_subquery))
        return queryset  
