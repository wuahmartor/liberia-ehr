from django.urls import path

from . import views

app_name = "care_management"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("board/", views.board_partial, name="board"),
    path("shifts/new/", views.create_shift, name="shift-create"),
    path("teams/new/", views.create_team, name="team-create"),
    path("assign/", views.assign, name="assign"),
    path("assignments/<uuid:assignment_id>/release/", views.release, name="release"),
    path("teams/<uuid:team_id>/staff/", views.team_add_staff, name="team-add-staff"),
    path("teams/<uuid:team_id>/patients/", views.team_add_patient, name="team-add-patient"),
]
