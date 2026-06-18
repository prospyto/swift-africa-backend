from decimal import Decimal

from django.db import transaction
from rest_framework import viewsets, generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (
    Utilisateur, Acheteur, Vendeur, Produit, Livreur, Commande,
    Notification, Mission, Ville, Wallet, Transaction
)
from .serializers import (
    UtilisateurSerializer, AcheteurSerializer, VendeurSerializer,
    ProduitSerializer, LivreurSerializer, CommandeSerializer,
    NotificationSerializer, MissionSerializer, VilleSerializer,
    WalletSerializer, TransactionSerializer
)
from .permissions import IsOwnerOrReadOnly


# =========================================================
# UTILISATEUR / PROFILS
# =========================================================
class UtilisateurViewSet(viewsets.ModelViewSet):
    """
    GET (list/retrieve) -> connecté uniquement
    POST -> ouvert à tous (inscription)
    """
    queryset = Utilisateur.objects.all()
    serializer_class = UtilisateurSerializer

    def get_permissions(self):
        if self.action == 'create':
            return [AllowAny()]
        return [IsAuthenticated()]


class AcheteurViewSet(viewsets.ModelViewSet):
    queryset = Acheteur.objects.all()
    serializer_class = AcheteurSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Un acheteur ne voit que son propre profil
        return Acheteur.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class VendeurViewSet(viewsets.ModelViewSet):
    queryset = Vendeur.objects.all()
    serializer_class = VendeurSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Vendeur.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class LivreurViewSet(viewsets.ModelViewSet):
    queryset = Livreur.objects.all()
    serializer_class = LivreurSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Livreur.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


# =========================================================
# PRODUITS / COMMANDES
# =========================================================
class ProduitViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour les produits :
    - GET public (voir tous les produits)
    - POST/PUT/DELETE : seulement pour le vendeur propriétaire
    """
    queryset = Produit.objects.all()
    serializer_class = ProduitSerializer
    permission_classes = [IsOwnerOrReadOnly]

    def get_permissions(self):
        if self.request.method in ('GET', 'HEAD', 'OPTIONS'):
            return [AllowAny()]
        return [IsAuthenticated(), IsOwnerOrReadOnly()]

    def perform_create(self, serializer):
        # Produit.vendeur est un FK vers le modèle Vendeur (pas Utilisateur directement)
        try:
            vendeur_profil = self.request.user.profil_vendeur
            serializer.save(vendeur=vendeur_profil)
        except Vendeur.DoesNotExist:
            return Response(
                {"error": "Vous n'avez pas de profil vendeur. Créez-en un d'abord."},
                status=status.HTTP_400_BAD_REQUEST
            )


class CommandeViewSet(viewsets.ModelViewSet):
    queryset = Commande.objects.all()
    serializer_class = CommandeSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if hasattr(user, 'profil_acheteur'):
            return Commande.objects.filter(acheteur=user.profil_acheteur)
        return Commande.objects.none()

    def perform_create(self, serializer):
        serializer.save(acheteur=self.request.user.profil_acheteur)


# =========================================================
# VILLES (lecture publique, écriture admin)
# =========================================================
class VilleViewSet(viewsets.ModelViewSet):
    queryset = Ville.objects.all()
    serializer_class = VilleSerializer

    def get_permissions(self):
        if self.request.method in ('GET', 'HEAD', 'OPTIONS'):
            return [AllowAny()]
        return [IsAuthenticated()]


# =========================================================
# MISSIONS
# =========================================================
class MissionCreateView(generics.CreateAPIView):
    """Créer une nouvelle mission de livraison (vendeur connecté)."""
    queryset = Mission.objects.all()
    serializer_class = MissionSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(vendeur=self.request.user)


class MissionListView(generics.ListAPIView):
    """Liste de toutes les missions."""
    queryset = Mission.objects.all()
    serializer_class = MissionSerializer
    permission_classes = [IsAuthenticated]


class MissionDetailUpdateView(generics.RetrieveUpdateAPIView):
    """Voir une mission spécifique et changer son statut (ex: accepter)."""
    queryset = Mission.objects.all()
    serializer_class = MissionSerializer
    permission_classes = [IsAuthenticated]


class MesMissionsListView(generics.ListAPIView):
    """Missions où l'utilisateur connecté est le livreur."""
    serializer_class = MissionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Mission.objects.filter(livreur=self.request.user)


class MissionsDisponiblesListView(generics.ListAPIView):
    """Missions en attente, non encore prises par un livreur."""
    serializer_class = MissionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Mission.objects.filter(statut='attente')


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def accepter_mission(request, mission_id):
    """Un livreur accepte une mission disponible et se l'assigne."""
    try:
        mission = Mission.objects.get(id=mission_id)
    except Mission.DoesNotExist:
        return Response({"error": "Mission introuvable."}, status=status.HTTP_404_NOT_FOUND)

    if mission.statut != 'attente':
        return Response({"error": "Cette mission n'est plus disponible."}, status=status.HTTP_400_BAD_REQUEST)

    if mission.livreur is not None:
        return Response({"error": "Cette mission a déjà été prise par un autre livreur."}, status=status.HTTP_400_BAD_REQUEST)

    mission.livreur = request.user
    mission.statut = 'en_cours'
    mission.save()

    if mission.vendeur:
        Notification.objects.create(
            utilisateur=mission.vendeur,
            titre="Mission prise en charge",
            message=f"{request.user.username} a accepté la livraison vers {mission.adresse_precise}.",
            lu=False
        )

    return Response(MissionSerializer(mission).data, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def valider_livraison(request, mission_id):
    """Le livreur saisit le code donné par l'acheteur pour terminer la course."""
    try:
        mission = Mission.objects.get(id=mission_id, livreur=request.user)
    except Mission.DoesNotExist:
        return Response({
            "status": "error",
            "message": "Mission introuvable ou vous n'êtes pas assigné à cette course."
        }, status=status.HTTP_404_NOT_FOUND)

    code_saisi = request.data.get('code')

    if mission.code_validation == str(code_saisi):
        mission.statut = 'livre'
        mission.save()
        return Response({
            "status": "success",
            "message": "Code correct. Livraison validée !"
        }, status=status.HTTP_200_OK)

    return Response({
        "status": "error",
        "message": "Code incorrect. Demandez le code à 4 chiffres au client."
    }, status=status.HTTP_400_BAD_REQUEST)


class DeclarerIncidentView(APIView):
    """
    Signale un incident sur une mission :
    - passe la mission en statut INCIDENT (déclenche la notification au vendeur via signals.py)
    - enregistre un litige dans le portefeuille du livreur (gains gelés / non versés)
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, mission_id):
        try:
            mission = Mission.objects.get(id=mission_id)
        except Mission.DoesNotExist:
            return Response({"error": "Mission introuvable."}, status=status.HTTP_404_NOT_FOUND)

        if mission.statut == "INCIDENT":
            return Response(
                {"error": "Un incident est déjà en cours sur cette mission."},
                status=status.HTTP_400_BAD_REQUEST
            )

        with transaction.atomic():
            mission.statut = "INCIDENT"
            mission.save()  # déclenche la notification au vendeur (voir signals.py)

            if mission.livreur:
                wallet_livreur, _ = Wallet.objects.get_or_create(utilisateur=mission.livreur)
                Transaction.objects.create(
                    wallet=wallet_livreur,
                    type_transaction="LITIGE",
                    montant=Decimal('0.00'),
                    statut="ECHEC",
                    reference_externe=f"INCIDENT-MISSION-{mission.id}"
                )

        return Response({
            "message": "Incident déclaré avec succès.",
            "statut_mission": mission.statut,
        }, status=status.HTTP_200_OK)


# =========================================================
# PROFIL / NOTIFICATIONS / PORTEFEUILLE
# =========================================================
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def mon_profil(request):
    user = request.user
    return Response({
        "id": str(user.id),
        "username": user.username,
        "email": user.email,
        "telephone": user.telephone,
        "est_acheteur": user.est_acheteur,
        "est_vendeur": user.est_vendeur,
        "est_livreur": user.est_livreur,
        "solde": user.solde,
    })


class NotificationListView(generics.ListCreateAPIView):
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(utilisateur=self.request.user).order_by('-date_creation')

    def perform_create(self, serializer):
        serializer.save(utilisateur=self.request.user)


class MonPortefeuilleView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            wallet = request.user.wallet
        except Wallet.DoesNotExist:
            return Response({"error": "Portefeuille introuvable."}, status=status.HTTP_404_NOT_FOUND)

        serializer = WalletSerializer(wallet)
        return Response(serializer.data, status=status.HTTP_200_OK)


class SimulerDepotView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        montant_str = request.data.get('montant')
        if not montant_str:
            return Response({"error": "Le montant est obligatoire."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            montant = Decimal(str(montant_str))
            if montant <= 0:
                return Response({"error": "Le montant doit être supérieur à 0."}, status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            return Response({"error": "Montant invalide."}, status=status.HTTP_400_BAD_REQUEST)

        wallet = request.user.wallet

        transaction_obj = Transaction.objects.create(
            wallet=wallet,
            type_transaction='DEPOT',
            montant=montant,
            statut='SUCCES',
            reference_externe="SIMU-MM-" + request.user.username.upper()
        )

        wallet.solde += montant
        wallet.save()

        return Response({
            "message": f"Dépôt de {montant} FCFA effectué avec succès !",
            "nouveau_solde": wallet.solde,
            "transaction": TransactionSerializer(transaction_obj).data
        }, status=status.HTTP_201_CREATED)
