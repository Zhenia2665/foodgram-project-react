from django.contrib import admin

from .models import (FavoriteRecipe, Ingredient, Recipe, RecipeIngredient,
                     ShoppingCart, Subscribe, Tag)
from .constants import EMPTY_MSG_ADMIN


class RecipeIngredientAdmin(admin.StackedInline):
    model = RecipeIngredient
    autocomplete_fields = ('ingredient',)
    min_num = 1

@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'get_author', 'name', 'text',
        'cooking_time', 'get_tags', 'get_ingredients',
        'pub_date', 'get_favorite_count')
    search_fields = (
        'name', 'cooking_time',
        'author__email', 'ingredients__name')
    list_filter = ('pub_date', 'tags',)
    inlines = (RecipeIngredientAdmin,)
    empty_value_display = EMPTY_MSG_ADMIN

    @admin.display(
        description='Электронная почта')
    def get_author(self, obj):
        return obj.author.email

    @admin.display(description='Тэги')
    def get_tags(self, obj):
        list_ = [_.name for _ in obj.tags.all()]
        return ', '.join(list_)

    @admin.display(description=' Ингредиенты ')
    def get_ingredients(self, obj):
        return '\n '.join([
            f'{item["ingredient__name"]} - {item["amount"]}'
            f' {item["ingredient__measurement_unit"]}.'
            for item in obj.recipe.values(
                'ingredient__name',
                'amount', 'ingredient__measurement_unit')])

    @admin.display(description='В избранном')
    def get_favorite_count(self, obj):
        return obj.favorite_recipe.count()


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'name', 'color', 'slug',)
    search_fields = ('name', 'slug',)
    ordering = ('color',)
    empty_value_display = EMPTY_MSG_ADMIN


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ('name', 'measurement_unit',)
    list_filter = ('name',)
    search_fields = ('name',)
    ordering = ('measurement_unit',)
    empty_value_display = EMPTY_MSG_ADMIN


@admin.register(ShoppingCart)
class SoppingCartAdmin(admin.ModelAdmin):
    list_display = ('user', 'recipe',)
    empty_value_display = EMPTY_MSG_ADMIN


@admin.register(FavoriteRecipe)
class FavoriteRecipeAdmin(admin.ModelAdmin):
    list_display = ('user', 'recipe',)
    list_filter = ('user', 'recipe',)
    empty_value_display = EMPTY_MSG_ADMIN


@admin.register(Subscribe)
class SubscribeAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'user', 'author', 'created',)
    search_fields = (
        'user__email', 'author__email',)
    empty_value_display = EMPTY_MSG_ADMIN
