import django.contrib.auth.password_validation as validators
from app.models import (
    Favorite,
    Ingredient,
    Recipe,
    RecipeIngredient,
    ShoppingCart,
    Tag
)
from django.contrib.auth import authenticate
from django.contrib.auth.hashers import make_password
from django.shortcuts import get_object_or_404
from djoser.serializers import UserSerializer
from drf_base64.fields import Base64ImageField
from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator

from .constants import COOKING_TIME_MAX, COOKING_TIME_MIN, ERROR_MSG
from users.models import Subscription, User


class TokenSerializer(serializers.Serializer):
    email = serializers.CharField(label="Email", write_only=True)
    token = serializers.CharField(label="Токен", read_only=True)
    password = serializers.CharField(
        label="Пароль",
        style={"input_type": "password"},
        trim_whitespace=False,
        write_only=True,
    )

    def validate(self, attrs):
        email = attrs.get("email")
        password = attrs.get("password")
        if email and password:
            user = authenticate(
                request=self.context.get("request"), email=email,
                password=password)
            if not user:
                raise serializers.ValidationError(
                    ERROR_MSG, code="authorization")
        else:
            msg = "Необходимо указать email и password."
            raise serializers.ValidationError(msg, code="authorization")
        attrs["user"] = user
        return attrs


class UserPasswordSerializer(serializers.Serializer):
    new_password = serializers.CharField(label="Новый пароль")
    current_password = serializers.CharField(label="Текущий пароль")

    def validate_current_password(self, current_password):
        user = self.context["request"].user
        if not authenticate(username=user.email, password=current_password):
            raise serializers.ValidationError(ERROR_MSG, code="authorization")
        return current_password

    def create(self, validated_data):
        user = self.context["request"].user
        password = make_password(validated_data.get("new_password"))
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
        fields = (
            "email", "id", "username", "first_name", "last_name",
            "is_subscribed")

    def get_is_subscribed(self, obj):
        request = self.context.get("request")
        return (
            request.user.is_authenticated
            and request.user.subscriptions.filter(author=obj).exists()
        )


class UserSubscribeSerializer(serializers.ModelSerializer):
    """Сериализатор для подписки/отписки от пользователей."""

    class Meta:
        model = Subscription
        fields = "__all__"
        validators = [
            UniqueTogetherValidator(
                queryset=Subscription.objects.all(),
                fields=("user", "author"),
                message="Вы уже подписаны на этого пользователя",
            )
        ]

    def validate(self, data):
        request = self.context.get("request")
        if request.user == data["author"]:
            raise serializers.ValidationError(
                "Нельзя подписываться на самого себя!")
        return data

    def to_representation(self, instance):
        request = self.context.get("request")
        return UserSubscribeSerializer(
            instance.author, context={"request": request}
        ).data


class CustomUserSerializer(UserSerializer):
    is_subscribed = serializers.SerializerMethodField()

    def get_is_subscribed(self, obj):
        user = self.context["request"].user
        return user.is_authenticated and user.subscriptions.filter(
            author=obj).exists()

    class Meta:
        fields = (
            "email", "id", "username", "first_name", "last_name",
            "is_subscribed")
        model = User


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = (
            "id",
            "name",
            "color",
            "slug",
        )


class IngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = "__all__"


class RecipeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recipe
        fields = ("id", "name", "image", "cooking_time")


class RecipeGetSerializer(serializers.ModelSerializer):
    """Сериализатор для получения информации о рецепте."""

    tags = TagSerializer(many=True, read_only=True)
    author = UserGetSerializer(read_only=True)
    ingredients = IngredientSerializer(
        many=True, read_only=True, source="recipeingredients"
    )
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()
    image = Base64ImageField(required=False)

    class Meta:
        model = Recipe
        fields = (
            "id",
            "tags",
            "author",
            "ingredients",
            "is_favorited",
            "is_in_shopping_cart",
            "name",
            "image",
            "text",
            "cooking_time",
        )

    def get_is_favorited(self, obj):
        request = self.context.get("request")
        return (
            request
            and request.user.is_authenticated
            and request.user.favorites.filter(recipe=obj).exists()
        )

    def get_is_in_shopping_cart(self, obj):
        request = self.context.get("request")
        return (
            request
            and request.user.is_authenticated
            and request.user.shopping_cart.filter(recipe=obj).exists()
        )


class RecipeWriteSerializer(serializers.ModelSerializer):
    image = Base64ImageField(
        max_length=None,
        use_url=True)
    tags = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Tag.objects.all())
    ingredients = IngredientSerializer(
        many=True)
    cooking_time = serializers.IntegerField(min_value=COOKING_TIME_MIN,
                                            max_value=COOKING_TIME_MAX
                                            )

    class Meta:
        model = Recipe
        fields = '__all__'
        read_only_fields = ('author',)

    def validate(self, data):
        ingredients = data['ingredients']
        ingredient_dict = {}

        for items in ingredients:
            ingredient = get_object_or_404(Ingredient, id=items['id'])
            if ingredient.id in ingredient_dict:
                raise serializers.ValidationError(
                    'Ингредиент должен быть уникальным!')
            ingredient_dict[ingredient.id] = ingredient

        tags = data['tags']
        if not tags:
            raise serializers.ValidationError(
                'Нужен хотя бы один тэг!')
        for tag_name in tags:
            if not Tag.objects.filter(name=tag_name).exists():
                raise serializers.ValidationError(
                    f'Тэг {tag_name} не существует!')
        return data

    def validate_ingredients(self, ingredients):
        if not ingredients:
            raise serializers.ValidationError(
                'Минимум 1 ингредиент в рецепте!')
        return ingredients

    def create_ingredients(self, ingredients, recipe):
        recipe_ingredients_list = [
            RecipeIngredient(
                recipe=recipe,
                ingredient_id=ingredient.get('id'),
                amount=ingredient.get('amount')
            )
            for ingredient in ingredients
        ]
        RecipeIngredient.objects.bulk_create(recipe_ingredients_list)

    def create(self, validated_data):
        ingredients = validated_data.pop('ingredients')
        tags = validated_data.pop('tags')
        recipe = Recipe.objects.create(**validated_data)
        recipe.tags.set(tags)
        self.create_ingredients(ingredients, recipe)
        return recipe

    def update(self, instance, validated_data):
        if 'ingredients' in validated_data:
            ingredients = validated_data.pop('ingredients')
            instance.ingredients.clear()
            self.create_ingredients(ingredients, instance)
        if 'tags' in validated_data:
            instance.tags.set(
                validated_data.pop('tags'))
        return super().update(
            instance, validated_data)

    def to_representation(self, instance):
        return RecipeWriteSerializer(
            instance,
            context={
                'request': self.context.get('request')
            }).data


class FavoriteSerializer(serializers.ModelSerializer):
    """Сериализатор для работы с избранными рецептами."""

    class Meta:
        model = Favorite
        fields = "__all__"
        validators = [
            UniqueTogetherValidator(
                queryset=Favorite.objects.all(),
                fields=("user", "recipe"),
                message="Рецепт уже добавлен в избранное",
            )
        ]

    def to_representation(self, instance):
        request = self.context.get("request")
        return RecipeSerializer(
            instance.recipe, context={"request": request}).data


class ShoppingCartSerializer(serializers.ModelSerializer):
    """Сериализатор для работы со списком покупок."""

    class Meta:
        model = ShoppingCart
        fields = "__all__"
        validators = [
            UniqueTogetherValidator(
                queryset=ShoppingCart.objects.all(),
                fields=("user", "recipe"),
                message="Рецепт уже добавлен в список покупок",
            )
        ]

    def to_representation(self, instance):
        request = self.context.get("request")
        return RecipeSerializer(instance.recipe, context={
            "request": request}).data
