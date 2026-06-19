from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    UtilisateurViewSet, AcheteurViewSet, VendeurViewSet, ProduitViewSet,
    LivreurViewSet, CommandeViewSet, VilleViewSet,
    MissionCreateView, MissionListView, MissionsDisponiblesListView,
    MesMissionsListView, MissionDetailUpdateView, accepter_mission,
    valider_livraison, DeclarerIncidentView,
    mon_profil, NotificationListView,
    MonPortefeuilleView, SimulerDepotView,
    RegisterView, LoginView, AuthMeView,
)

router = DefaultRouter()
router.register(r'utilisateurs', UtilisateurViewSet, basename='utilisateur')
router.register(r'acheteurs', AcheteurViewSet, basename='acheteur')
router.register(r'vendeurs', VendeurViewSet, basename='vendeur')
router.register(r'livreurs', LivreurViewSet, basename='livreur')
router.register(r'produits', ProduitViewSet, basename='produit')
router.register(r'commandes', CommandeViewSet, basename='commande')
router.register(r'villes', VilleViewSet, basename='ville')

urlpatterns = [
    # --- Authentification ---
    path('auth/register/', RegisterView.as_view(), name='auth-register'),
    path('auth/login/', LoginView.as_view(), name='auth-login'),
    path('auth/me/', AuthMeView.as_view(), name='auth-me'),

    # --- Ressources CRUD standard (router) ---
    path('', include(router.urls)),

    # --- Missions (livraison) ---
    path('missions/creer/', MissionCreateView.as_view(), name='mission-creer'),
    path('missions/liste/', MissionListView.as_view(), name='missions-liste'),
    path('missions/disponibles/', MissionsDisponiblesListView.as_view(), name='missions-disponibles'),
    path('missions/mes-courses/', MesMissionsListView.as_view(), name='mes-missions'),
    path('missions/<int:pk>/', MissionDetailUpdateView.as_view(), name='mission-detail'),
    path('missions/<int:mission_id>/accepter/', accepter_mission, name='mission-accepter'),
    path('missions/<int:mission_id>/valider/', valider_livraison, name='valider-livraison'),
    path('missions/<int:mission_id>/incident/', DeclarerIncidentView.as_view(), name='declarer-incident'),

    # --- Profil utilisateur ---
    path('me/', mon_profil, name='mon-profil'),

    # --- Notifications ---
    path('notifications/', NotificationListView.as_view(), name='notifications'),

    # --- Portefeuille ---
    path('portefeuille/', MonPortefeuilleView.as_view(), name='mon-portefeuille'),
    path('portefeuille/depot-simulation/', SimulerDepotView.as_view(), name='simuler-depot'),
]
