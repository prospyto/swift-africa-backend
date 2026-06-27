# CORS Force Redeploy v3
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    UtilisateurViewSet, AcheteurViewSet, VendeurViewSet, ProduitViewSet,
    LivreurViewSet, CommandeViewSet, VilleViewSet,
    FinancerCommandeView, DecaisserCommandeView, MarquerPretCommandeView,
    MissionCreateView, MissionListView, MissionsDisponiblesListView,
    MesMissionsListView, MissionDetailUpdateView, accepter_mission,
    valider_livraison, DeclarerIncidentView,
    MissionDestinationView, MissionPositionView,
    mon_profil, NotificationListView,
    MonPortefeuilleView, SimulerDepotView, NoterView,
    RegisterView, LoginView, AuthMeView,
    ConversationCommandeView, MessagesNonLusView,
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
    # Authentification
    path('auth/register/', RegisterView.as_view(), name='auth-register'),
    path('auth/login/', LoginView.as_view(), name='auth-login'),
    path('auth/me/', AuthMeView.as_view(), name='auth-me'),

    # CRUD standard
    path('', include(router.urls)),

    # Missions
    path('missions/creer/', MissionCreateView.as_view(), name='mission-creer'),
    path('missions/liste/', MissionListView.as_view(), name='missions-liste'),
    path('missions/disponibles/', MissionsDisponiblesListView.as_view(), name='missions-disponibles'),
    path('missions/mes-courses/', MesMissionsListView.as_view(), name='mes-missions'),
    path('missions/<int:pk>/', MissionDetailUpdateView.as_view(), name='mission-detail'),
    path('missions/<int:mission_id>/accepter/', accepter_mission, name='mission-accepter'),
    path('missions/<int:mission_id>/valider/', valider_livraison, name='valider-livraison'),
    path('missions/<int:mission_id>/incident/', DeclarerIncidentView.as_view(), name='declarer-incident'),
    path('missions/<int:mission_id>/destination/', MissionDestinationView.as_view(), name='mission-destination'),
    path('missions/<int:mission_id>/position/', MissionPositionView.as_view(), name='mission-position'),
    
    # Commandes — Vendeur
    path('commandes/<int:commande_id>/financer/', FinancerCommandeView.as_view(), name='commande-financer'),
    path('commandes/<int:commande_id>/marquer-pret/', MarquerPretCommandeView.as_view(), name='commande-marquer-pret'),
    path('commandes/<int:commande_id>/decaisser/', DecaisserCommandeView.as_view(), name='commande-decaisser'),

    # Chat
    path('chat/commande/<int:commande_id>/avec/<str:autre_role>/', ConversationCommandeView.as_view(), name='chat-commande'),
    path('chat/non-lus/', MessagesNonLusView.as_view(), name='chat-non-lus'),

    # Profil / Notifs / Wallet
    path('me/', mon_profil, name='mon-profil'),
    path('notifications/', NotificationListView.as_view(), name='notifications'),
    path('portefeuille/', MonPortefeuilleView.as_view(), name='mon-portefeuille'),
    path('portefeuille/depot-simulation/', SimulerDepotView.as_view(), name='simuler-depot'),
    path('commandes/<int:commande_id>/noter/', NoterView.as_view(), name='noter-commande'),
]

