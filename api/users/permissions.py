from rest_framework import permissions

from .models import User


class AdsPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        user = User.objects.filter(username=request.user.username).first()
        if user:
            return user.can_ads


class AnalyzersPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        user = User.objects.filter(username=request.user.username).first()
        if user:
            return user.can_analyzers


class ChartsPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        user = User.objects.filter(username=request.user.username).first()
        if user:
            return user.can_charts


class GrabbersPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        user = User.objects.filter(username=request.user.username).first()
        if user:
            return user.can_grabbers


class ParsersPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        user = User.objects.filter(username=request.user.username).first()
        if user:
            return user.can_parsers


class RelatedPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        user = User.objects.filter(username=request.user.username).first()
        if user:
            return user.can_related
