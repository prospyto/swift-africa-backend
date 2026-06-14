from django.urls import path
from .views import (
    MissionCreateView,
    MissionsDisponiblesListView,
    MesMissionsListView,
    MissionDetailUpdateView,
    mon_profil,
    valider_livraison,
    NotificationListView,
    MonPortefeuilleView,
    SimulerDepotView,
    DeclarerIncidentView,
)

urlpatterns = [
    # Missions
    path('missions/creer/', MissionCreateView.as_view(), name='mission-creer'),
    path('missions/disponibles/', MissionsDisponiblesListView.as_view(), name='missions-disponibles'),
    path('missions/mes-courses/', MesMissionsListView.as_view(), name='mes-missions'),
    path('missions/<int:pk>/', MissionDetailUpdateView.as_view(), name='mission-detail'),
    path('missions/<int:mission_id>/valider/', valider_livraison, name='valider-livraison'),
    path('missions/<int:mission_id>/incident/', DeclarerIncidentView.as_view(), name='declarer-incident'),

    # Profil
    path('me/', mon_profil, name='mon-profil'),

    # Notifications
    path('notifications/', NotificationListView.as_view(), name='notifications'),

    # Portefeuille
    path('portefeuille/', MonPortefeuilleView.as_view(), name='mon-portefeuille'),
    path('portefeuille/depot-simulation/', SimulerDepotView.as_view(), name='simuler-depot'),
]
