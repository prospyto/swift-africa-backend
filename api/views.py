from rest_framework import viewsets, generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import ListCreateAPIView
from rest_framework import status
from django.db import transaction
from decimal import Decimal

from .models import (
    Utilisateur, Acheteur, Vendeur, Produit, Livreur,
    Commande, Mission, Notification, Wallet, Transaction
)
from .serializers import (
    UtilisateurSerializer, AcheteurSerializer, VendeurSerializer,
    ProduitSerializer, LivreurSerializer, CommandeSerializer,
    MissionSerializer, NotificationSerializer, WalletSerializer, TransactionSerializer
)
from .permissions import IsOwnerOrReadOnly


# --- VIEWSETS CRUD ---

class UtilisateurViewSet(viewsets.ModelViewSet):
    queryset = Utilisateur.objects.all()
    serializer_class = UtilisateurSerializer


class AcheteurViewSet(viewsets.ModelViewSet):
    queryset = Acheteur.objects.all()
    serializer_class = AcheteurSerializer


class VendeurViewSet(viewsets.ModelViewSet):
    queryset = Vendeur.objects.all()
    serializer_class = VendeurSerializer


class ProduitViewSet(viewsets.ModelViewSet):
    queryset = Produit.objects.all()
    serializer_class = ProduitSerializer
    permission_classes = [IsOwnerOrReadOnly]

    def perform_create(self, serializer):
        serializer.save(vendeur=self.request.user)


class LivreurViewSet(viewsets.ModelViewSet):
    queryset = Livreur.objects.all()
    serializer_class = LivreurSerializer


class CommandeViewSet(viewsets.ModelViewSet):
    queryset = Commande.objects.all()
    serializer_class = CommandeSerializer


# --- VUES MISSIONS ---

class MissionCreateView(generics.CreateAPIView):
    queryset = Mission.objects.all()
    serializer_class = MissionSerializer
    permission_classes = [IsAuthenticated]


class MissionListView(generics.ListAPIView):
    queryset = Mission.objects.all()
    serializer_class = MissionSerializer
    permission_classes = [IsAuthenticated]


class MissionDetailUpdateView(generics.RetrieveUpdateAPIView):
    queryset = Mission.objects.all()
    serializer_class = MissionSerializer
    permission_classes = [IsAuthenticated]


class MesMissionsListView(generics.ListAPIView):
    serializer_class = MissionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Mission.objects.filter(livreur=self.request.user)


class MissionsDisponiblesListView(generics.ListAPIView):
    serializer_class = MissionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Mission.objects.filter(statut='attente')


# --- VALIDATION LIVRAISON ---

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def valider_livraison(request, mission_id):
    try:
        mission = Mission.objects.get(id=mission_id, livreur=request.user)
        code_saisi = request.data.get('code')

        if mission.code_validation == str(code_saisi):
            mission.statut = 'livre'
            mission.save()
            return Response({
                "status": "success",
                "message": "Code correct. Livraison validée !"
            }, status=200)
        else:
            return Response({
                "status": "error",
                "message": "Code incorrect. Demandez le code à 4 chiffres au client."
            }, status=400)

    except Mission.DoesNotExist:
        return Response({
            "status": "error",
            "message": "Mission introuvable ou vous n'êtes pas assigné à cette course."
        }, status=404)


# --- PROFIL ---

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def mon_profil(request):
    return Response({
        "nom": request.user.username,
        "tel": request.user.telephone,
        "est_livreur": request.user.est_livreur,
        "photo": None  # champ photo_profil non défini dans le modèle
    })


# --- NOTIFICATIONS ---

class NotificationListView(ListCreateAPIView):
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(utilisateur=self.request.user).order_by('-date_creation')

    def perform_create(self, serializer):
        serializer.save(utilisateur=self.request.user)


# --- PORTEFEUILLE ---

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


# --- INCIDENT ---

class DeclarerIncidentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, mission_id):
        with transaction.atomic():
            try:
                mission = Mission.objects.get(id=mission_id)

                if mission.statut == "INCIDENT":
                    return Response(
                        {"error": "Un incident est déjà en cours sur cette mission."},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                mission.statut = "INCIDENT"
                mission.save()

                return Response({
                    "message": "Incident déclaré avec succès.",
                    "statut_mission": mission.statut,
                }, status=status.HTTP_200_OK)

            except Mission.DoesNotExist:
                return Response(
                    {"error": "Mission introuvable."},
                    status=status.HTTP_404_NOT_FOUND
                )
            except Exception as e:
                return Response(
                    {"error": f"Une erreur est survenue : {str(e)}"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
