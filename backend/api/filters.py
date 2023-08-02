from django.core.exceptions import ValidationError
import django_filters as filters

from users.models import User
from recipes.models import Ingredient, Recipe


class TagsChoiceField(
        filters.fields.MultipleChoiceField):
    def validate(self, value):
        if self.required and not value:
            raise ValidationError(
                self.error_messages['required'],
                code='required')
        for val in value:
            if val in self.choices and not self.valid_value(val):
                raise ValidationError(
                    self.error_messages['invalid_choice'],
                    code='invalid_choice',
                    params={'value': val},)


class TagsFilter(filters.AllValuesMultipleFilter):
    field_class = TagsChoiceField


class IngredientFilter(filters.FilterSet):
    name = filters.CharFilter(lookup_expr='istartswith')

    class Meta:
        model = Ingredient
        fields = ('name',)


class RecipeFilter(filters.FilterSet):
    is_in_shopping_cart = filters.BooleanFilter(
        widget=filters.widgets.BooleanWidget(),
        label='В корзине.')
    author = filters.ModelChoiceFilter(
        queryset=User.objects.all())
    is_favorited = filters.BooleanFilter(
        widget=filters.widgets.BooleanWidget(),
        label='В избранных.')
    tags = filters.AllValuesMultipleFilter(
        field_name='tags__slug',
        label='Тэг')

    class Meta:
        model = Recipe
        fields = ['is_favorited', 'is_in_shopping_cart', 'author', 'tags']
