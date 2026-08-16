from django.urls import path

from . import views

app_name = "care_management"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("board/", views.board_partial, name="board"),
    path("shifts/new/", views.create_shift, name="shift-create"),
    path("teams/commit/", views.commit_assignment_batch, name="team-commit"),
    path("teams/<uuid:team_id>/update/", views.update_assignment_team, name="team-update"),
    path("team-patients/<uuid:assignment_id>/release/", views.release_team_patient, name="team-patient-release"),
    path("assign/", views.assign, name="assign"),
    path("assignments/<uuid:assignment_id>/release/", views.release, name="release"),
]
