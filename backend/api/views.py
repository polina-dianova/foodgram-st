import base64

from rest_framework import viewsets, status, filters, serializers
from rest_framework.decorators import action
from rest_framework.permissions import (IsAuthenticated, IsAuthenticatedOrReadOnly)
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError

from django.core.files.base import ContentFile
from django.contrib.auth import get_user_model
from django.http import FileResponse
from django.db.models import F, Sum
from django.shortcuts import get_object_or_404, redirect
from django_filters.rest_framework import DjangoFilterBackend
from django.urls import reverse
from djoser.views import UserViewSet as DjoserUserViewSet
from rest_framework.authtoken.views import ObtainAuthToken
from recipe.models import (Ingredient, Recipe, Favorite, ShoppingCart, RecipeIngredient)
from .serializers import (
    UsersSerializer, UserWithRecipesSerializer,
    RecipeSerializer, IngredientSerializer, SubscriptionRecipeSerializer
)
from .permissions import IsAuthorOrReadOnly
from .filters import RecipeFilter
from .pagination import PageToOffsetPagination
from .utils import render_shopping_cart

User = get_user_model()


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    pagination_class = None
    filter_backends = (DjangoFilterBackend, filters.SearchFilter,)
    search_fields = ('^name',)

    def get_queryset(self):
        queryset = Ingredient.objects.all().order_by('name')
        name = self.request.query_params.get('name', None)
        if name:
            queryset = queryset.filter(name__icontains=name)
        return queryset


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.all()
    serializer_class = RecipeSerializer
    pagination_class = PageToOffsetPagination
    filter_backends = (DjangoFilterBackend,)
    filterset_class = RecipeFilter
    permission_classes = (IsAuthorOrReadOnly,)

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def get_permissions(self):
        if self.action == 'create':
            return [IsAuthenticated()]
        return [IsAuthorOrReadOnly(), IsAuthenticatedOrReadOnly()]
    
    def get_recipe(self, pk):
        return get_object_or_404(Recipe, pk=pk)

    @staticmethod
    def handle_recipe_action(model, user, recipe, action_type):
        if action_type == 'add':
            obj, created = model.objects.get_or_create(user=user, recipe=recipe)
            if not created:
                raise serializers.ValidationError('Рецепт уже добавлен.')
            return Response(SubscriptionRecipeSerializer(recipe).data, status=status.HTTP_201_CREATED)
        
        elif action_type == 'remove':
            get_object_or_404(
                model,
                user=user,
                recipe=recipe
            ).delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def shopping_cart(self, request, pk=None):
        recipe = self.get_recipe(pk)
        return self.handle_recipe_action(
            ShoppingCart,
            request.user,
            recipe,
            'add')
    
    @shopping_cart.mapping.delete
    def remove_from_shopping_cart(self, request, pk=None):
        recipe = self.get_recipe(pk)
        return self.handle_recipe_action(
            ShoppingCart, 
            request.user, 
            recipe, 
            'remove')

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def favorite(self, request, pk=None):
        recipe = self.get_recipe(pk)
        return self.handle_recipe_action(
            model = Favorite,
            user = request.user,
            recipe = recipe,
            action_type = 'add'
        )
    @favorite.mapping.delete
    def remove_from_favorites(self, request, pk=None):
        recipe = self.get_recipe(pk)
        return self.handle_recipe_action(Favorite, request.user, recipe, 'remove')

    @action(detail=True, methods=['get'], url_path='get-link')
    def get_link(self, request, pk=None):
        recipe = self.get_object()
        short_link = request.build_absolute_uri(reverse('recipe_redirect', args=[recipe.pk]))
        return Response({'short-link': short_link}, status=status.HTTP_200_OK)

    @action(detail=False, permission_classes=[IsAuthenticated])
    def download_shopping_cart(self, request):
        user = request.user
        ingredients = RecipeIngredient.objects.filter(
            recipe__in=user.shopping_carts.values('recipe')
        ).values(
            name=F('ingredient__name'),
            measurement_unit=F('ingredient__measurement_unit'),
            recipe_name=F('recipe__name')
        ).annotate(amount=Sum('amount')).order_by('name')

        return FileResponse(
            render_shopping_cart(ingredients), 
            as_attachment=True,
            filename='Shopping_cart.txt',
            content_type='text/plain'
        )

class UserViewSet(DjoserUserViewSet):
    queryset = User.objects.all()
    serializer_class = UsersSerializer
    permission_classes = (IsAuthenticatedOrReadOnly,)

    @action(detail=False, methods=['get'],
            permission_classes=[IsAuthenticated])
    def me(self, request, *args, **kwargs):
        return super().me(request, *args, **kwargs)

    @action(detail=True, methods=['post', 'delete'],
            permission_classes=[IsAuthenticated])
    def subscribe(self, request, id=None):
        user = request.user
        author = self.get_object()

        if request.method == 'POST':
            if user == author:
                return Response(
                    {'error': 'Нельзя подписаться на самого себя.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            subscription, created = user.followers.get_or_create(
                author=author)

            if not created:
                return Response(
                    {'error': 'Вы уже подписаны на этого пользователя.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            serializer = UserWithRecipesSerializer(
                author, context={'request': request}
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        get_object_or_404(user.followers, author=author).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['get'],
            permission_classes=[IsAuthenticated])
    def subscriptions(self, request):
        queryset = User.objects.filter(authors__user=request.user)
        recipes_limit = request.query_params.get('recipes_limit')
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = UserWithRecipesSerializer(
                page, many=True, context={'request': request,
                                          'recipes_limit': recipes_limit}
            )
            return self.get_paginated_response(serializer.data)
        serializer = UserWithRecipesSerializer(
            queryset, many=True, context={'request': request,
                                          'recipes_limit': recipes_limit})
        return Response(serializer.data)

    @action(detail=False, methods=['put', 'delete'], url_path='me/avatar',
            permission_classes=[IsAuthenticated])
    def avatar(self, request):
        user = request.user
        if request.method == 'PUT':
            avatar_data = request.data.get('avatar')
            if not avatar_data:
                raise ValidationError('Требуются данные для аватара.')
            try:
                format, imgstr = avatar_data.split(';base64,')
            except ValueError:
                raise ValidationError(
                    'Недопустимый формат аватара. Ожидаемое - base64.')
            ext = format.split('/')[-1]
            avatar_file = ContentFile(base64.b64decode(imgstr),
                                      name=f'avatar.{ext}')
            if user.avatar:
                user.avatar.delete(save=False)
            user.avatar = avatar_file
            user.save()
            return Response({'avatar': user.avatar.url})
        if user.avatar:
            user.avatar.delete(save=True)
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    
class CustomAuthToken(ObtainAuthToken):
    def post(self, request, *args, **kwargs):
        if 'logout' in request.path:
            if request.user.is_authenticated:
                request.user.auth_token.delete()
                return Response(
                    {'status': 'Logged out successfully'},
                    status=status.HTTP_204_NO_CONTENT
                )
            return Response(
                {'error': 'User is not authenticated'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        email = request.data.get('email')
        password = request.data.get('password')

        if not email or not password:
            return Response(
                {'error': 'Email and password are required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response(
                {'error': 'No user found with this email address'},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = authenticate(request, username=user.username, password=password)

        if user is None:
            return Response(
                {'error': 'Invalid credentials'},
                status=status.HTTP_400_BAD_REQUEST
            )

        token, created = Token.objects.get_or_create(user=user)
        return Response({
            'auth_token': token.key,
            'user_id': user.id,
            'email': user.email,
        }
        )