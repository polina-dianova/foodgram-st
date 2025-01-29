from django.shortcuts import get_object_or_404, redirect
from .models import Recipe


def recipe_redirect(request, short_id):
    get_object_or_404(Recipe, id=short_id)
    return redirect(f'/recipes/{short_id}')
