from django.urls import include, path
from rest_framework.routers import DefaultRouter

from api.views import (
    AuthToken,
    RecipesViewSet,
    IngredientViewSet,
    TagViewSet,
    UserViewSet,
    AddDeleteShoppingCart,
    UserSubscribeView
)

app_name = "api"

router = DefaultRouter()
router.register("tags", TagViewSet)
router.register("users", UserViewSet)
router.register("ingredients", IngredientViewSet)
router.register("recipes", RecipesViewSet)


urlpatterns = [
    path("auth/token/login/", AuthToken.as_view(), name="login"),
    path(
        "users/<int:user_id>/subscribe/",
        UserSubscribeView.as_view(),
        name='subscribe',
    ),
    path(
        'recipes/<int:recipe_id>/shopping_cart/',
        AddDeleteShoppingCart.as_view(),
        name='shopping_cart',
    ),
    path('', include(router.urls)),
    path('', include('djoser.urls')),
    path('auth/', include('djoser.urls.authtoken')),
]
