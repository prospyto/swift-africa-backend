from rest_framework import viewsets
from .models import Utilisateur, Acheteur, Vendeur, Produit, Livreur, Commande,Notification # <-- VERIFIE BIEN CETTE LIGNE
from .serializers import (
    UtilisateurSerializer, AcheteurSerializer, VendeurSerializer, 
    ProduitSerializer, LivreurSerializer, CommandeSerializer,NotificationSerializer
)

class UtilisateurViewSet(viewsets.ModelViewSet):
    queryset = Utilisateur.objects.all()
    serializer_class = UtilisateurSerializer

class AcheteurViewSet(viewsets.ModelViewSet):
    queryset = Acheteur.objects.all()
    serializer_class = AcheteurSerializer

class VendeurViewSet(viewsets.ModelViewSet):
    queryset = Vendeur.objects.all()
    serializer_class = VendeurSerializer

from .permissions import IsOwnerOrReadOnly # N'oublie pas l'import !

class ProduitViewSet(viewsets.ModelViewSet):
    queryset = Produit.objects.all()
    serializer_class = ProduitSerializer
    permission_classes = [IsOwnerOrReadOnly] # On applique le blindage ici

    def perform_create(self, serializer):
        # Force l'enregistrement du vendeur comme étant l'utilisateur connecté
        serializer.save(vendeur=self.request.user)


class LivreurViewSet(viewsets.ModelViewSet):
    queryset = Livreur.objects.all()
    serializer_class = LivreurSerializer

class CommandeViewSet(viewsets.ModelViewSet):
    queryset = Commande.objects.all()
    serializer_class = CommandeSerializer

from rest_framework import generics
from .models import Mission
from .serializers import MissionSerializer
from rest_framework.permissions import IsAuthenticated

class MissionCreateView(generics.CreateAPIView):
    """
    Cette classe permet de créer une nouvelle mission.
    Elle hérite de CreateAPIView qui gère automatiquement le POST.
    """
    queryset = Mission.objects.all()
    serializer_class = MissionSerializer
    
    # Seuls les utilisateurs avec un badge (token) peuvent commander
    permission_classes = [IsAuthenticated]    

class MissionListView(generics.ListAPIView):
    """Cette vue permet d'afficher la liste de toutes les missions"""
    queryset = Mission.objects.all()
    serializer_class = MissionSerializer
    permission_classes = [IsAuthenticated]    

from rest_framework import generics

class MissionDetailUpdateView(generics.RetrieveUpdateAPIView):
    """
    Cette vue permet au livreur de voir une mission spécifique 
    et de changer son statut (ex: Accepter la mission).
    """
    queryset = Mission.objects.all()
    serializer_class = MissionSerializer
    permission_classes = [IsAuthenticated] 

# ... tes autres vues (MissionCreateView, etc.) ...

class MesMissionsListView(generics.ListAPIView):
    """
    Cette vue affiche uniquement les missions 
    où l'utilisateur connecté est le livreur.
    """
    serializer_class = MissionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return Mission.objects.filter(livreur=user)

# Assure-toi aussi que MissionsDisponiblesListView est bien là :
class MissionsDisponiblesListView(generics.ListAPIView):
    serializer_class = MissionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Mission.objects.filter(statut='attente')
    
from rest_framework.decorators import api_view
from rest_framework.response import Response

@api_view(['POST'])
def valider_livraison(request, mission_id):
    try:
        mission = Mission.objects.get(id=mission_id, livreur=request.user)
        code_saisi = request.data.get('code')

        if mission.code_validation == code_saisi:
            mission.statut = 'livre'
            mission.save()
            return Response({"message": "Livraison validée ! Félicitations."}, status=200)
        else:
            return Response({"error": "Code incorrect. Vérifiez avec l'acheteur."}, status=400)
    except Mission.DoesNotExist:
        return Response({"error": "Mission non trouvée ou vous n'êtes pas le livreur."}, status=404)

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import Mission

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def valider_livraison(request, mission_id):
    """
    Le livreur saisit le code donné par l'acheteur pour terminer la course.
    """
    try:
        # On vérifie que la mission existe ET que c'est bien CE livreur qui l'a prise
        mission = Mission.objects.get(id=mission_id, livreur=request.user)
        
        # On récupère le code envoyé par l'app mobile (Postman)
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
    
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def mon_profil(request):
    return Response({
        "nom": request.user.username,
        "tel": request.user.telephone,
        "est_livreur": request.user.est_livreur,
        "photo": request.user.photo_profil.url if request.user.photo_profil else None
    }
)    
    

# Modifie l'importation au début du fichier
from rest_framework.generics import ListCreateAPIView 

# Modifie la classe
class NotificationListView(ListCreateAPIView): # Change ListAPIView par ListCreateAPIView
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(utilisateur=self.request.user).order_by('-date_creation')

    def perform_create(self, serializer):
        # Cette méthode permet de lier automatiquement la notification à l'utilisateur connecté
        serializer.save(utilisateur=self.request.user)   
    
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from .models import Wallet, Transaction
from .serializers import WalletSerializer, TransactionSerializer
from decimal import Decimal

class MonPortefeuilleView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Récupère le portefeuille de l'utilisateur connecté avec son solde et ses transactions.
        """
        try:
            wallet = request.user.wallet
        except Wallet.DoesNotExist:
            return Response({"error": "Portefeuille introuvable."}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = WalletSerializer(wallet)
        return Response(serializer.data, status=status.HTTP_200_OK)


class SimulerDepotView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        Simule un dépôt Mobile Money réussi pour tester l'augmentation du solde.
        """
        montant_str = request.data.get('montant')
        if not montant_str:
            return Response({"error": "Le montant est obligatoire."}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            montant = Decimal(str(montant_str))
            if montant <= 0:
                return Response({"error": "Le montant doit être supérieur à 0."}, status=status.HTTP_400_BAD_REQUEST)
        except ValueError:
            return Response({"error": "Montant invalide."}, status=status.HTTP_400_BAD_REQUEST)

        # 1. Récupérer le wallet de l'utilisateur
        wallet = request.user.wallet

        # 2. Créer l'enregistrement de la transaction (directement en SUCCES pour la simulation)
        transaction = Transaction.objects.create(
            wallet=wallet,
            type_transaction='DEPOT',
            montant=montant,
            statut='SUCCES',
            reference_externe="SIMU-MM-" + request.user.username.upper()
        )

        # 3. Mettre à jour le solde du Wallet
        wallet.solde += montant
        wallet.save()

        return Response({
            "message": f"Dépôt de {montant} FCFA effectué avec succès !",
            "nouveau_solde": wallet.solde,
            "transaction": TransactionSerializer(transaction).data
        }, status=status.HTTP_201_CREATED)    
    
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.db import transaction
from .models import Mission, Wallet, Transaction, Notification
class DeclarerIncidentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, mission_id):
        # Utilisation d'une transaction atomique pour sécuriser l'argent (tout passe ou tout s'annule)
        with transaction.atomic():
            try:
                # 1. Récupérer la mission concernée
                mission = Mission.objects.get(id=mission_id)
                
                if mission.statut == "INCIDENT":
                    return Response(
                        {"error": "Un incident est déjà en cours sur cette mission."}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )

                # 2. Passer la mission en statut INCIDENT
                mission.statut = "INCIDENT"
                mission.save()

                # 3. Logique Portefeuille (Wallet) & Sécurité financière
                # On récupère la commande liée pour connaître le montant et l'acheteur
                commande = mission.commande 
                acheteur = commande.acheteur
                livreur = mission.livreur

                # Scénario A : Annulation et remboursement immédiat de l'acheteur
                # On imagine que l'argent avait été bloqué/payé depuis le Wallet de l'acheteur
                wallet_acheteur, created = Wallet.objects.get_or_create(utilisateur=acheteur)
                wallet_acheteur.solde += commande.total_prix  # Remboursement
                wallet_acheteur.save()

                # Enregistrer la transaction de remboursement dans l'historique
                Transaction.objects.create(
                    wallet=wallet_acheteur,
                    montant=commande.total_prix,
                    type_transaction="REMBOURSEMENT",
                    description=f"Remboursement suite incident sur la mission {mission.id}"
                )

                # Scénario B : Sanction ou gel des gains du livreur (si un livreur était assigné)
                if livreur:
                    # Exemple : On peut déduire une pénalité ou simplement ne rien lui verser
                    wallet_livreur, created = Wallet.objects.get_or_create(utilisateur=livreur)
                    
                    # On enregistre un litige dans son historique de transactions
                    Transaction.objects.create(
                        wallet=wallet_livreur,
                        montant=0,
                        type_transaction="LITIGE",
                        description=f"Course bloquée pour incident sur la mission {mission.id}"
                    )

                return Response(
                    {
                        "message": "Incident déclaré avec succès.",
                        "statut_mission": mission.statut,
                        "action_financiere": "Acheteur remboursé, transaction enregistrée."
                    }, 
                    status=status.HTTP_200_OK
                )

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