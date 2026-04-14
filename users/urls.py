from django.urls import path

from . import views


app_name = "users"

urlpatterns = [
    path("login/", views.loginUser, name="login"),
    path("signup/", views.signup, name="signup"),
    path("logout/", views.logoutUser, name="logout"),
    path("profile/", views.profile, name="profile"),
    path("profile/edit/", views.edit_profile, name="edit_profile"),
    path("profile/update/", views.profile_update, name="profile-update"),
    path("profile/<str:username>/", views.profile_view, name="profile_view"),
]

