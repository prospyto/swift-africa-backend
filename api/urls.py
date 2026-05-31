from django.urls import path
from .views import (
    MissionCreateView,
    MissionsDisponiblesListView,
    MesMissionsListView,
    MissionDetailUpdateView,  # La virgule ici est obligatoire
    mon_profil,               # Ajoute une virgule ici aussi par sécurité
    valider_livraison
)
urlpatterns = [
    # 1. Créer une mission (Postman : POST)
    path('missions/creer/', MissionCreateView.as_view(), name='mission-creer'),
    
    # 2. Voir les missions libres (Postman : GET)
    path('missions/disponibles/', MissionsDisponiblesListView.as_view(), name='missions-disponibles'),
    
    # 3. Voir mes courses (Postman : GET)
    path('missions/mes-courses/', MesMissionsListView.as_view(), name='mes-missions'),
    
    # 4. Détails et Acceptation (Postman : GET ou PATCH)
    path('missions/<int:pk>/', MissionDetailUpdateView.as_view(), name='mission-detail'),
    
    # 5. Validation finale par code (Postman : POST)
    path('missions/<int:mission_id>/valider/', valider_livraison, name='valider-livraison'),
    # Assure-toi que le nom correspond à ta fonction dans views.py
    path('me/', mon_profil, name='mon-profil'),
]

from django.urls import path
from .views import NotificationListView # Assure-toi que cette vue existe

urlpatterns = [
    # ... tes autres routes ...
    path('notifications/', NotificationListView.as_view(), name='notifications'),
]

from django.urls import path
from .views import MonPortefeuilleView, SimulerDepotView # Assure-toi de les importer au début du fichier

urlpatterns = [
    # ... tes autres urls existantes ...
    path('portefeuille/', MonPortefeuilleView.as_view(), name='mon-portefeuille'),
    path('portefeuille/depot-simulation/', SimulerDepotView.as_view(), name='simuler-depot'),
]

from django.urls import path
from .views import DeclarerIncidentView

urlpatterns = [
    # ... tes autres routes (auth, produits...)
    path('missions/<int:mission_id>/incident/', DeclarerIncidentView.as_view(), name='declarer-incident'),
]