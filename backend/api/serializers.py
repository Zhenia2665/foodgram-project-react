import django.contrib.auth.password_validation as validators
from django.contrib.auth import authenticate
from django.contrib.auth.hashers import make_password
from djoser.serializers import UserSerializer
from drf_base64.fields import Base64ImageField
from rest_framework import serializers
from rest_framework.validators import (
    UniqueTogetherValidator, MinValueValidator, MaxValueValidator)

from users.models import User, Subscription
from app.models import (Favorite, RecipeIngredient, Ingredient,
                        Recipe, ShoppingCart, Tag)
from .constants import AMOUNT_INGREDIENT_MIN, AMOUNT_INGREDIENT_MAX, ERROR_MSG


class TokenSerializer(serializers.Serializer):
    email = serializers.CharField(
        label='Email',
        write_only=True)
    token = serializers.CharField(
        label='Токен',
        read_only=True)
    password = serializers.CharField(
        label='Пароль',
        style={'input_type': 'password'},
        trim_whitespace=False,
        write_only=True)

    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')
        if email and password:
            user = authenticate(
                request=self.context.get('request'),
                email=email,
                password=password)
            if not user:
                raise serializers.ValidationError(
                    ERROR_MSG,
                    code='authorization')
        else:
            msg = 'Необходимо указать email и password.'
            raise serializers.ValidationError(
                msg,
                code='authorization')
        attrs['user'] = user
        return attrs


class UserPasswordSerializer(serializers.Serializer):
    new_password = serializers.CharField(
        label='Новый пароль')
    current_password = serializers.CharField(
        label='Текущий пароль')

    def validate_current_password(self, current_password):
        user = self.context['request'].user
        if not authenticate(
                username=user.email,
                password=current_password):
            raise serializers.ValidationError(
                ERROR_MSG, code='authorization')
        return current_password

    def create(self, validated_data):
        user = self.context['request'].user
        password = make_password(
            validated_data.get('new_password'))
        user.password = password
        user.save()
        return validated_data

    def validate_new_password(self, new_password):
        validators.validate_password(new_password)
        return new_password


class UserGetSerializer(UserSerializer):
    """Сериализатор для работы с информацией о пользователях."""
    is_subscribed = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('email', 'id', 'username', 'first_name',
                  'last_name', 'is_subscribed')

    def get_is_subscribed(self, obj):
        request = self.context.get('request')
        return (request.user.is_authenticated
                and request.user.subscriptions.filter(
                    author=obj).exists())


class UserSubscribeSerializer(serializers.ModelSerializer):
    """Сериализатор для подписки/отписки от пользователей."""

    class Meta:
        model = Subscription
        fields = '__all__'
        validators = [
            UniqueTogetherValidator(
                queryset=Subscription.objects.all(),
                fields=('user', 'author'),
                message='Вы уже подписаны на этого пользователя'
            )
        ]

    def validate(self, data):
        request = self.context.get('request')
        if request.user == data['author']:
            raise serializers.ValidationError(
                'Нельзя подписываться на самого себя!'
            )
        return data

    def to_representation(self, instance):
        request = self.context.get('request')
        return UserSubscribeSerializer(
            instance.author, context={'request': request}
        ).data


class CustomUserSerializer(UserSerializer):
    is_subscribed = serializers.SerializerMethodField()

    def get_is_subscribed(self, obj):
        user = self.context['request'].user
        return user.is_authenticated and user.subscriptions.filter(
                    author=obj).exists()

    class Meta:
        fields = ('email', 'id', 'username',
                  'first_name', 'last_name', 'is_subscribed')
        model = User


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = (
            'id', 'name', 'color', 'slug',)


class IngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = '__all__'


class IngredientsEditSerializer(serializers.ModelSerializer):
    """Сериализатор для получения информации об ингредиентах.
    Используется при работе с рецептами."""
    id = serializers.IntegerField(source='ingredient.id', read_only=True)
    name = serializers.CharField(source='ingredient.name', read_only=True)
    measurement_unit = serializers.CharField(
        source='ingredient.measurement_unit',
        read_only=True
    )

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'name', 'measurement_unit', 'amount')

    id = serializers.IntegerField()
    amount = serializers.IntegerField(
        MinValueValidator(AMOUNT_INGREDIENT_MIN),
        MaxValueValidator(AMOUNT_INGREDIENT_MAX)
    )

    class Meta:
        model = Ingredient
        fields = ('id', 'amount')


class RecipeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')


class RecipeGetSerializer(serializers.ModelSerializer):
    """Сериализатор для получения информации о рецепте."""
    tags = TagSerializer(many=True, read_only=True)
    author = UserGetSerializer(read_only=True)
    ingredients = IngredientSerializer(
                                        many=True, read_only=True,
                                        source='recipeingredients')
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()
    image = Base64ImageField(required=False)

    class Meta:
        model = Recipe
        fields = ('id', 'tags', 'author', 'ingredients',
                  'is_favorited', 'is_in_shopping_cart', 'name',
                  'image', 'text', 'cooking_time')

    def get_is_favorited(self, obj):
        request = self.context.get('request')
        return (request and request.user.is_authenticated
                and request.user.favorites.filter(
                    recipe=obj).exists())

    def get_is_in_shopping_cart(self, obj):
        request = self.context.get('request')
        return (request and request.user.is_authenticated
                and request.user.shopping_cart.filter(
                    recipe=obj).exists())


class FavoriteSerializer(serializers.ModelSerializer):
    """Сериализатор для работы с избранными рецептами."""
    class Meta:
        model = Favorite
        fields = '__all__'
        validators = [
            UniqueTogetherValidator(
                queryset=Favorite.objects.all(),
                fields=('user', 'recipe'),
                message='Рецепт уже добавлен в избранное'
            )
        ]

    def to_representation(self, instance):
        request = self.context.get('request')
        return RecipeSerializer(
            instance.recipe,
            context={'request': request}
        ).data


class ShoppingCartSerializer(serializers.ModelSerializer):
    """Сериализатор для работы со списком покупок."""
    class Meta:
        model = ShoppingCart
        fields = '__all__'
        validators = [
            UniqueTogetherValidator(
                queryset=ShoppingCart.objects.all(),
                fields=('user', 'recipe'),
                message='Рецепт уже добавлен в список покупок'
            )
        ]

    def to_representation(self, instance):
        request = self.context.get('request')
        return RecipeSerializer(
            instance.recipe,
            context={'request': request}
        ).data
