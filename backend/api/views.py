import io

from django.contrib.auth import get_user_model
from django.db.models.aggregates import Sum
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from djoser.views import UserViewSet as DjoserUserViewSet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from rest_framework import generics, status, viewsets
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.decorators import action
from rest_framework.views import APIView
from rest_framework.status import (
    HTTP_201_CREATED,
    HTTP_204_NO_CONTENT,
    HTTP_400_BAD_REQUEST,
    HTTP_401_UNAUTHORIZED
)
from rest_framework.permissions import (
    SAFE_METHODS,
    AllowAny,
    IsAuthenticated,
    IsAuthenticatedOrReadOnly
)
from rest_framework.response import Response

from .constants import (
    FILENAME_PDF,
    FONT_SIZE_CART,
    FONT_SIZE_DEF,
    INDENT,
    X_POSITION_INGR,
    Y_POSITION_CART,
    Y_POSITION_INGR,
    Y_POSITION_PARAM
)
from .filters import IngredientFilter, RecipeFilter
from .pagination import LimitPageNumberPagination
from .serializers import (
    IngredientSerializer,
    RecipeGetSerializer,
    RecipeSerializer,
    RecipeWriteSerializer,
    UserGetSerializer,
    TagSerializer,
    TokenSerializer,
    UserSubscribeSerializer
)
from recipes.models import Ingredient, Recipe, Tag, Subscribe

User = get_user_model()


class UserViewSet(DjoserUserViewSet):
    queryset = User.objects.all().order_by('-date_joined')
    serializer_class = UserGetSerializer
    pagination_class = LimitPageNumberPagination
    additional_serializer = UserSubscribeSerializer

    @action(methods=('POST', 'DELETE'), detail=True)
    def subscribe(self, request, **kwargs):
        user = self.request.user
        if user.is_anonymous:
            return Response(status=HTTP_401_UNAUTHORIZED)
        obj = get_object_or_404(self.queryset, id=kwargs.get('id'))
        serializer = self.additional_serializer(
            obj, context={'request': self.request}
        )
        if self.request.method == 'POST':
            user.subscribe.add(obj)
            return Response(serializer.data, status=HTTP_201_CREATED)
        if self.request.method == 'DELETE':
            user.subscribe.remove(obj)
            return Response(status=HTTP_204_NO_CONTENT)
        return Response(status=HTTP_400_BAD_REQUEST)

    @action(methods=('GET',), detail=False)
    def subscriptions(self, request):
        user = self.request.user
        if user.is_anonymous:
            return Response(status=HTTP_401_UNAUTHORIZED)
        authors = user.subscribe.all()
        pages = self.paginate_queryset(authors)
        serializer = UserSubscribeSerializer(
            pages, many=True, context={'request': request}
        )
        return self.get_paginated_response(serializer.data)


class AuthToken(ObtainAuthToken):
    """Авторизация пользователя."""

    serializer_class = TokenSerializer
    permission_classes = (AllowAny,)

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        token, created = Token.objects.get_or_create(user=user)
        return Response({"auth_token": token.key},
                        status=status.HTTP_201_CREATED)


class UserSubscribeView(APIView):
    """Создание/удаление подписки на пользователя."""
    def post(self, request, user_id):
        author = get_object_or_404(User, id=user_id)
        serializer = UserSubscribeSerializer(
            data={'user': request.user.id, 'author': author.id},
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def delete(self, request, user_id):
        author = get_object_or_404(User, id=user_id)
        if not Subscribe.objects.filter(
                user=request.user, author=author).exists():
            return Response(
                {'errors': 'Вы не подписаны на этого пользователя'},
                status=status.HTTP_400_BAD_REQUEST
            )
        Subscribe.objects.get(
            user=request.user.id,
            author=user_id).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    """Получение информации о тегах."""

    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = (AllowAny,)
    pagination_class = None


class GetObjectMixin:
    """Удаление/добавление рецептов из избранного или корзины."""

    serializer_class = RecipeSerializer
    permission_classes = (AllowAny,)

    def get_object(self):
        recipe_id = self.kwargs["recipe_id"]
        recipe = get_object_or_404(Recipe, id=recipe_id)
        self.check_object_permissions(self.request, recipe)
        return recipe


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    """Получение информации об ингредиентах."""

    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    permission_classes = (AllowAny,)
    filter_backends = (DjangoFilterBackend,)
    filterset_class = IngredientFilter
    pagination_class = None


class AddDeleteShoppingCart(GetObjectMixin,
                            generics.RetrieveDestroyAPIView,
                            generics.ListCreateAPIView):
    """Добавление и удаление рецепта в/из корзины."""

    def create(self, request, *args, **kwargs):
        instance = self.get_object()
        request.user.shopping_cart.recipe.add(instance)
        serializer = self.get_serializer(instance)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def perform_destroy(self, instance):
        self.request.user.shopping_cart.recipe.remove(instance)


class RecipesViewSet(viewsets.ModelViewSet):
    """Информация о рецептах."""

    queryset = Recipe.objects.all()
    filterset_class = RecipeFilter
    pagination_class = LimitPageNumberPagination
    permission_classes = (IsAuthenticatedOrReadOnly,)

    def get_serializer_class(self):
        if self.request.method in SAFE_METHODS:
            return RecipeGetSerializer
        return RecipeWriteSerializer

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    @action(detail=False, methods=["get"],
            permission_classes=(IsAuthenticated,))
    def download_shopping_cart(self, request):
        """Скачать список с ингредиентами."""

        buffer = io.BytesIO()
        page = canvas.Canvas(buffer)
        pdfmetrics.registerFont(TTFont("Vera", "Vera.ttf"))
        x_position, y_position = X_POSITION_INGR, Y_POSITION_INGR
        shopping_cart = (
            request.user.shopping_cart.recipe.values(
                "ingredients__name", "ingredients__measurement_unit"
            )
            .annotate(amount=Sum("recipe__amount"))
            .order_by()
        )
        page.setFont("Vera", FONT_SIZE_DEF)
        if shopping_cart:
            indent = INDENT
            page.drawString(x_position, y_position, "Cписок покупок:")
            for index, recipe in enumerate(shopping_cart, start=1):
                page.drawString(
                    x_position,
                    y_position - indent,
                    f'{index}. {recipe["ingredients__name"]} - '
                    f'{recipe["amount"]} '
                    f'{recipe["ingredients__measurement_unit"]}.',
                )
                y_position -= Y_POSITION_CART
                if y_position <= Y_POSITION_PARAM:
                    page.showPage()
                    y_position = Y_POSITION_INGR
            page.save()
            buffer.seek(0)
            return FileResponse(
                buffer, as_attachment=True, filename=FILENAME_PDF)
        page.setFont("Vera", FONT_SIZE_CART)
        page.drawString(x_position, y_position, "Cписок покупок пуст!")
        page.save()
        buffer.seek(0)
        return FileResponse(buffer, as_attachment=True, filename=FILENAME_PDF)
